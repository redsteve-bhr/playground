# -*- coding: utf-8 -*-
#
# Copyright 2013 Grosvenor Technology
#

import log
from applib.db import tblTransactions
import commsHelper
from contextlib import closing
from applib.db.tblSettings import getAppSetting
from applib.db import database
from applib.utils import jobs
import uuid
import xml.etree.cElementTree as ET

_trans = None

def getAppTransactions():
    """ Return application web client transaction class. """
    global _trans
    if (_trans == None):
        _trans = _createAppTrans()
        _trans.open()
    return _trans

def _createAppTrans():
    transactions = Transaction(database.getAppDB(),
            getAppSetting('webclient_trans_warn_level'),
            getAppSetting('webclient_trans_max_level'),
            getAppSetting('webclient_trans_keep_time'),
            getAppSetting('webclient_retry_time'),
            )
    return transactions

def createTransactionData(deviceID, dataTag, emp=None, dataType=None):
    """ Create transaction XML with employee info. """
    topTag = ET.Element('transaction')
    ET.SubElement(topTag, 'transID').text = str(uuid.uuid1())
    ET.SubElement(topTag, 'deviceID').text = deviceID
    if (emp):
        empTag = ET.SubElement(topTag, 'employee')
        ET.SubElement(empTag, 'empID').text = emp.getEmpID()
        # add information about identification
        identifiedByTag = ET.SubElement(empTag, 'identifiedBy')
        if (emp.isIdentifiedByReader()):
            ET.SubElement(identifiedByTag, 'badgeCode').text = emp.getBadgeCode()
        elif (emp.isIdentifiedByKeypad()):           
            ET.SubElement(identifiedByTag, 'keypadID').text = emp.getKeypadID()
        else:
            ET.SubElement(identifiedByTag, emp.getUsedIdentificationMethod())
        # add information about verification
        # e.g. add verify by photo 
        verifiedByTag = ET.SubElement(empTag, 'verifiedBy')
        vMethod = emp.getUsedVerificationMethod()
        ET.SubElement(verifiedByTag, vMethod)
    
    if dataType is not None:
        dataTag.tag = 'data'
        dataTag.attrib['type'] = dataType
        topTag.append(dataTag)
    else:
        ET.SubElement(topTag, 'data').append(dataTag)
    return ET.tostring(topTag)


class Transaction(tblTransactions.TblTransactions):

    columnDefs = {'TransID' : 'INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL', 
                  'Sent'    : 'INTEGER DEFAULT "0" NOT NULL',
                  'Time'    : 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL',
                  'Data'    : 'TEXT NOT NULL'}

    #-----------------------------------------------------------------------
    def __init__(self, db, warnLevel=1000, maxLevel=20000, keepTime = 60*60*24, retryTime = 60):
        super(Transaction, self).__init__(db, "tblWebClientTrans", warnLevel, maxLevel, keepTime, retryTime)
        self.__sender = None
        self.__deviceID = getAppSetting('clksrv_id')

    def startThread(self):
        super(Transaction, self).startThread(_TransactionSender())

    def create(self):
        super(Transaction, self).create()
        log.dbg("Creating index for %s" % self.tableName)
        self.runQuery('CREATE INDEX %sIndex ON %s(Time);' % (self.tableName, self.tableName))        

    def addTransaction(self, dataTag, emp=None, dataType=None):
        """Add clocking to transaction table and send when possible. """
        self.insert({'Data': createTransactionData(self.__deviceID, dataTag, emp, dataType)})

    def createTransaction(self, dataTag, emp=None, dataType=None):
        return createTransactionData(self.__deviceID, dataTag, emp, dataType)
        
    def markAsSentToDate(self, sqlTime):
        """Mark unsent transactions up to and including *sqlTime* as sent.

        *sqlTime* is a UTC date-time string in the format "%Y-%m-%d %H:%M:%S"
        """
        sql = "UPDATE %s SET Sent = '1' WHERE Time <= (?)" % self.tableName
        self.runQuery(sql, (sqlTime,))
        self.unsentTransactions = self.getNumberUnsent()

    def getNumberOfUnsentTransactions(self, sqlTime):
        """Returns the number of unsent transactions up to and including *sqlTime*.

        *sqlTime* is a UTC date-time string in the format "%Y-%m-%d %H:%M:%S"
        """
        sql = 'SELECT COUNT(*) FROM %s WHERE Sent = "0" AND Time <= (?)' % self.tableName
        count = self.runSelectOne(sql, (sqlTime,))
        if (count == None):
            return 0
        return count[0]

class _TransactionSender(object):

    def prepare(self):
        self.__conn = None
    
    def send(self, transData):
        # Reuse connection of possible
        if (self.__conn is None):
            self.__conn = commsHelper.openHttpConnection()
        try:
            commsHelper.httpPost(self.__conn, getAppSetting('webclient_trans_offline_tail'), transData['data'])
        except:
            # Close connection on error
            self.__conn.close()
            raise
        log.dbg('Transaction sent OK')        
        
    def postSend(self, ignore=None):
        # Close connection once all pending transactions were sent
        if (self.__conn != None):
            self.__conn.close()
        

class OnlineTransactionJob(jobs.Job):
    """This is used for the on-demand employee info requests""" 

    def __init__(self, dataTag, emp=None, dataType=None, responseText=None):
        super(OnlineTransactionJob, self).__init__()
        self.__transData = createTransactionData(getAppSetting('clksrv_id'), dataTag, emp, dataType)
        self.__responseText = responseText
        self.__failIndicator = False
     
    def getName(self):
        return 'clocking.online'
     
    def execute(self):
        with closing(commsHelper.openHttpConnection()) as conn:
            response = commsHelper.httpPost(conn, getAppSetting('webclient_trans_online_tail'), self.__transData) 
        #self.__infoRequestResponse = self.__parseResponse(data)
        root = ET.fromstring(response)
        if (root.tag != 'response'):
            log.err('Unexpected root element in online transaction response: %s' % root.tag)
            raise Exception('Invalid response!')
        msgTag = root.find('message')
        if (msgTag == None) or (msgTag.text.strip() == ""):
            # No message in response. Can we fall back on a default?
            if self.__responseText == None:
                log.err('No message element in online transaction response and no default response available!')
                raise Exception('Invalid response!!')
        else:
            self.__responseText = msgTag.text
        self.__failIndicator = (root.get('failed') == 'true')
    
    def commitTransaction(self):
        """ Send transaction as offline transaction. """
        getAppTransactions().insert({'Data': self.__transData})        
    
    def getResponseText(self):
        return self.__responseText

    def hasFailIndicator(self):
        return (self.__failIndicator)
    

  

            

