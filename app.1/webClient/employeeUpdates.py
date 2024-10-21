# -*- coding: utf-8 -*-

import xml.etree.cElementTree as ET
from contextlib import closing
import commsHelper
import employees
import log
import base64
import time
import threading
from applib.db import tblTransactions, database, tblSettings
from applib.bio.bioEncryption import BioEncryption
from applib.utils import crashReport, timeUtils
import json
from plugins.consent.consentManager import ConsentManager, ConsentReason, ConsentStatus, consentReasonForStatus

_empUpdatesQueue = None


def getAppEmpUpdatesQueue():
    """ Return application employee update queue. """
    global _empUpdatesQueue
    if (_empUpdatesQueue == None):
        _empUpdatesQueue = EmployeeUpdatesQueue(
                                database.getAppDB(), 
                                retryTime = tblSettings.getAppSetting('webclient_retry_time'))
        _empUpdatesQueue.open()
    return _empUpdatesQueue


class EmployeeUpdatesQueue(tblTransactions.TblTransactions):

    columnDefs = { 'TransID' : 'INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL',
                   'Sent'    : 'INTEGER DEFAULT "0" NOT NULL',
                   'Time'    : 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL',
                   'EmpID'   : 'TEXT NOT NULL',
                   'Field'   : 'TEXT NOT NULL',
                   'Data'    : 'TEXT NOT NULL' }
                        
    def __init__(self, db, warnLevel=10, maxLevel=100, keepTime=0, retryTime=60):
        super(EmployeeUpdatesQueue, self).__init__(db, "tblEmployeeUpdates", warnLevel, maxLevel, keepTime, retryTime)
        self.__completedCond = threading.Condition()
    
    def getHealthName(self):
        return _('Employee Updates Status')

    def startThread(self):
        log.dbg('Starting employee updates thread')
        super(EmployeeUpdatesQueue, self).startThread(_EmployeeUpdatesSender())

    def add(self, empID, field, data):
        self.insert({'EmpID':empID, 'Field': field, 'Data': data})

    def addConsent(self, empID, consentData):
        """Send consent message"""
        self.add(empID, "consent", consentData)
        
    def addTemplates(self, empID, tmplData):
        """ Request change of templates, *templates* is a String (could be JSON). """
        self.add(empID, 'templates', tmplData)
        
    def addPhoto(self, empID, photo):
        """ Request change of photo, *photo* is raw data of a JPEG encoded photo. """
        self.add(empID, 'photo', base64.b64encode(photo) if photo else '')
        
    def addLanguage(self, empID, language):
        """ Request change of language. *language* is a **String**. """
        self.add(empID, 'language', language)
        
    def addPin(self, empID, pin):
        """ Request change of pin. *pin* is a **String**. """
        self.add(empID, 'pin', pin)

    def addBadgeCode(self, empID, badgeCode):
        """ Request change of BadgeCode. *badgeCode* is a **String**. """
        self.add(empID, 'badgeCode', badgeCode)

    def addVerificationbMethods(self, empID, vMethods):
        """ Request change of verification methods. *vMethods* is a **String**. """
        self.add(empID, 'verifyBy', vMethods)
    
    def waitUntilDone(self, timeout):
        """ Blocks until all transactions are sent and a re-sync of
            employees has happened or the timeout.
        """
        # do not wait if there are more than 5 changes queued
        if (self.unsentTransactions > 5):
            return self.unsentTransactions
        with self.__completedCond:
            endTime = time.time() + timeout
            while (time.time() < endTime):
                if (self.unsentTransactions == 0):
                    break
                self.__completedCond.wait(endTime - time.time())
        return self.unsentTransactions
    
    def markAsDone(self):
        """ Notify everyone waiting that the queue has been emptied. """
        with self.__completedCond:
            self.__completedCond.notifyAll()



class _EmployeeUpdatesSender(object):
    
    def prepare(self):
        pass

    def send(self, trans):
        """ Send employee update request. 
        
        `trans` is a dict with four entries: `EmpID`, `TransID`, `Field`, 
        and `Data`, taken from the equivalent fields in tblEmployeeUpdates.
        
        The `Field` entry is the identifying name for the type of data, and is 
        used as the tag-name for the XML element that is created for the data.
        
        The `Data` entry contains the actual data as a string.
        
        The resulting XML that is sent to the server has this format for templates:
        
        <employee>
          <empID>1-1</empID>
          <templates>Base64Encoded: {"Templates": ["RR0SGZMAVUYgw8Gqh...\n"], "Info": {"fingerInfo": [...], "numTemplates": 2}, "Consents": [{"templateHashes": "", "expiry": "2024-03-13T10:44:54+0000", "source": "0001CE01D61F", "time": "2023-03-14T10:44:54+0000", "action": "accepted", "id": "b209a0d4-3280-4166-a022-e928f3afeb90"}]}</templates>
        </employee>

        """
        log.dbg("Sending employee change #%s (%s)" % (trans['TransID'], trans['Field']))
        reason = ""
        if trans['Field'] == 'consent':
            body = trans['Data']
        else:
            employeeTag = ET.Element('employee')
            if trans['Field'] == "templates":
                try:
                    # If BioEncryption is in use, replace the templates with the decrypted version
                    if trans['Data'].strip() != "":
                        tmplData = json.loads(trans['Data'])
                        templates = BioEncryption.getInstance().decryptTemplates(tmplData['Templates'])
                    else:
                        tmplData = {}
                        templates = []
                except Exception as e:
                    log.err("Failed to decrypt template {0}".format(e))
                    crashReport.createCrashReportFromException()
                    return
                tmplData["Templates"] = templates
                try:
                    dataStr = json.dumps(tmplData)
                    # Set the correct reason for the XML element
                    consents = ConsentManager()
                    consents.loadFromJSONString(dataStr)
                    status = consents.getActiveStatus()
                    if status in [ConsentStatus.ENROLLED, ConsentStatus.RENEWED]:
                        reason = consentReasonForStatus(status)
                    else:
                        log.err('Invalid consent status "%s" found for employee "%s".' % (status, trans['EmpID']))
                        reason = ConsentReason.ConsentEnrolled
                    dataStr = base64.b64encode(dataStr)
                except Exception as e:
                    log.err("Failed to parse template data: {0}".format(e))
                    crashReport.createCrashReportFromException()
                    return
            else:
                dataStr = trans['Data']
    
            ET.SubElement(employeeTag, 'empID').text = trans['EmpID']
            element = ET.SubElement(employeeTag, trans['Field'])
            if trans['Field'] == "templates" and reason != "":
                element.set('reason', reason)
            element.text = dataStr
            
            ET.SubElement(employeeTag, 'time').text = timeUtils.getXMLTimestampNow() 

            body = ET.tostring(employeeTag, 'utf-8')
        
        with closing(commsHelper.openHttpConnection()) as conn:
            commsHelper.httpPatch(conn, '/employees/%s' % (trans['EmpID']), body)
            
    def postSend(self, tblTrans):
        if (tblTrans.unsentTransactions==0):
            employees.syncEmployees()
            tblTrans.markAsDone()

