# -*- coding: utf-8 -*-
#
# Copyright 2023 Grosvenor Technology
#
"""Handling for Consent data in Employee records"""
import uuid
import base64
import datetime
import os
from HTMLParser import HTMLParser, HTMLParseError
from htmlentitydefs import name2codepoint
import re
import xml.etree.cElementTree

import log
from applib.utils import timeUtils
import json

from webClient.webConfig import getAppWebClientSetup
import webClient
from applib.db import sqlTime

class ConsentStatus(object):
    """Pseudo-enumeration of ConsentRecord Status values"""
    
    PENDING = "PENDING"    # Only used internally, never sent to server
    ENROLLED = "ACCEPTED"
    DECLINED = "DECLINED"
    DELETED = "DELETED"
    RENEWED = "RENEWED"
    DEFERRED = "DEFERRED"
    TIMEDOUT = "TIMEDOUT"
    CANCELLED = "CANCELLED"
    EXPIRING = "EXPIRING"  # Only used internally, never sent to server
    EXPIRED = "EXPIRED"    # Only used internally, never sent to server
    
    ACTIVE = [ENROLLED, RENEWED]

class ConsentReason(object):
    """Pseudo-enumeration of consent reasons, to be sent as attributes in 
    Employee Update transactions"""
    
    UserDeleted = "userDeleted"
    ConsentEnrolled = "consentEnrolled"
    ConsentDeclined = "consentDeclined"
    ConsentDeferred = "consentDeferred"
    ConsentRenewed = "consentRenewed"
    ConsentExpired = "consentExpired"
    ConsentTimedOut = "consentTimedOut"
    ConsentCancelled = "consentCancelled"
    ConsentRenewalDeclined = "consentRenewalDeclined"
    
def consentReasonForStatus(status):
    """Helper function to return the correct ConsentReason for the supplied
    ConsentStatus, used for the 'reason' attribute when sending templates to
    the server.
    
    Note that in theory this should never be used for anything other than 
    ACCEPTED or RENEWED, as the other options should never be sent as a
    reason in the 'Update Templates' message to the server. 
    """
    reasonMap = {
        ConsentStatus.ENROLLED:  ConsentReason.ConsentEnrolled,
        ConsentStatus.RENEWED:   ConsentReason.ConsentRenewed,
        ConsentStatus.CANCELLED: ConsentReason.ConsentCancelled,
        ConsentStatus.DECLINED:  ConsentReason.ConsentDeclined,
        ConsentStatus.DEFERRED:  ConsentReason.ConsentDeferred,
        ConsentStatus.DELETED:   ConsentReason.UserDeleted,
        ConsentStatus.EXPIRED:   ConsentReason.ConsentExpired,
        ConsentStatus.TIMEDOUT:  ConsentReason.ConsentTimedOut
    }
    
    result = ''
    if status in reasonMap:
        result = reasonMap[status]
        
    if status not in [ConsentStatus.ENROLLED, ConsentStatus.RENEWED]:
        # This is probably an error, but allow it anyway and just warn
        log.warn('consentReasonForStatus() called with status of "%s"' % status)

    return result

class ConsentRecord(object):
    """Class to hold the details of a single ConsentRecord record"""
    
    def __init__(self):
        """Assign default values to the record (these can be overwritten)"""
        self.consentId = str(uuid.uuid4())
        self.usage = "finger"
        self.source = getAppWebClientSetup().getDeviceID()
        self.time = datetime.datetime.utcnow().strftime(sqlTime.sqlTimeFormat)
        self.expiry = ""
        self.action = ConsentStatus.PENDING
        self.consentText = ""
        self.templateHashes = ""
        
    def asJSONStr(self):
        """Return the record as a JSON string, suitable for sending to GtConnect"""
        record = {'bio': {
            'verCode': '1',
            'consent': [
                {
                    'id': self.consentId,
                    'usage': self.usage,
                    'source': self.source,
                    'time': self.time,
                    'expiry': self.expiry,
                    'action': self.action,
                    'consentText': self.consentText,
                    'templateHashes': ''
                    }
                ]
            }
        }
        ss = json.dumps(record)
        return json.dumps(record)

class _HTMLToText(HTMLParser):
    """ Helper class for to extract plain text from HTML, e.g.::

        parser = _HTMLToText()
        try:
            parser.feed(html)
            parser.close()
        except HTMLParseError:
            pass
        return parser.get_text()

        """
    def __init__(self):
        HTMLParser.__init__(self)
        self._buf = []
        self.hide_output = False

    def handle_starttag(self, tag, attrs):
        if tag in ('p', 'br') and not self.hide_output:
            self._buf.append('\n')
        elif tag in ('script', 'style'):
            self.hide_output = True

    def handle_startendtag(self, tag, attrs):
        if tag == 'br':
            self._buf.append('\n')

    def handle_endtag(self, tag):
        if tag == 'p':
            self._buf.append('\n')
        elif tag in ('script', 'style'):
            self.hide_output = False

    def handle_data(self, text):
        if text and not self.hide_output:
            self._buf.append(re.sub(r'\s+', ' ', text))

    def handle_entityref(self, name):
        if name in name2codepoint and not self.hide_output:
            c = unichr(name2codepoint[name])
            self._buf.append(c)

    def handle_charref(self, name):
        if not self.hide_output:
            n = int(name[1:], 16) if name.startswith('x') else int(name)
            self._buf.append(unichr(n))

    def get_text(self):
        return re.sub(r' +', ' ', ''.join(self._buf))

class ConsentConfig():
    """Class providing access to the details of the biometric consent file"""
    
    def __init__(self, filename='/mnt/user/db/consentfinger.xml', empLanguage='en'):
        self.__xml = None
        self.__employeeLanguage = empLanguage.lower()
        try:
            if (os.path.exists(filename)):
                root = xml.etree.cElementTree.parse(filename).getroot()
                self.__removeNamespace(root)
                if (root.tag != 'consent'):
                    log.err('Error parsing %s; expected tag "consent" got "%s"' % (filename, root.tag))
                else:                    
                    self.__xml = root
            else:
                log.err('No consent available: {} not found!'.format(filename))
        except Exception as e:
            log.err('Error loading %s (%s)' % (filename, e))

    def __removeNamespace(self, doc, ns=None):
        """Remove namespace in the passed document in place."""
        for elem in doc.getiterator():
            if elem.tag.startswith('{'):
                uri, tagName = elem.tag[1:].split('}')
                if (ns == None):
                    elem.tag = tagName
                elif (ns == uri):
                    elem.tag = tagName

    def __removeCDataTags(self, html):
        """Returns the HTML with any wrapping CDATA tag removed"""
        result = re.sub("<!\[CDATA\[", "", html)
        result = re.sub("\]\]>", "", result)
        return result
    
    def __extractHTMLText(self, html):
            """
            Given a piece of HTML, return the plain text it contains.
            This handles entities and char refs, but not javascript and stylesheets.
            """
            parser = _HTMLToText()
            try:
                parser.feed(self.__removeCDataTags(html))
                parser.close()
            except HTMLParseError:
                pass
            return parser.get_text()

    def getMessage(self):
        """ Return extracted html corresponding to the correct language """
        # Go through XML and get consent
        try:          
            for c in self.__xml.findall('configuration/messages'):
                consentHtml = ""
                for i in c.getchildren():
                    # At first extract any language found
                    if (consentHtml == ""):
                        consentHtml = self.__extractHTMLText(i.text)
                    # As long as language property is empty continue
                    language = i.get('language').lower()
                    # Replace with language specified
                    if language  == "":
                        continue
                    else:
                        # Replace and return 'consentHtml' with language specified (if found)
                        if language == self.__employeeLanguage:
                            consentHtml = self.__extractHTMLText(i.text)
                            return consentHtml
                return consentHtml
        except Exception as e:
            return "Consent Text file could not be read: {}".format(e)

    def getExpiryTimeInDays(self):
        """ Return expiryTimeInDays """
        try:
            expiryTime = int(self.__xml.find('configuration/expiryTimeInDays').text)
        except:
            # Return default if no tag was found
            expiryTime = 365
        return expiryTime
    
    def getDaysToGiveWarning(self):
        """ Return daysToGiveWarning """            
        try:
            expiryTime = int(self.__xml.find('configuration/daysToGiveWarning').text)
        except:
            # Return default if no tag was found
            return 10
        return expiryTime
    

class ConsentManager(object):
    """Class to read, parse, and modify ConsentRecord details for Employees
    
    Usage:
        from plugins.consent import ConsentManager, ConsentStatus
        
        employee = emps.getEmpByBadgeCode("1234")
        
        # Read list of consents from Employee record
        consents = ConsentManager()
        consents.load(employee)

        # Retrieve the latest ConsentRecord
        consentRecord = consents.getLatest()
        log.info("ConsentRecord agreed at %s" % consentRecord.time)
        
        # Add a new consent
        consents.add("2015-05-15T13:19:21+0000", ConsentStatus.ENROLLED)
        
        # Store modified consents
        consents.save()
    """

    def __init__(self):
        self.records = []
        
    def load(self, employee):
        """Loads the consent details from the supplied employee"""
        if employee is None:
            log.err("No employee record provided for ConsentManager.load()")
            return
        empLanguage = employee.getLanguage(useManagerIfAvailable=False)
        self.config = ConsentConfig(empLanguage=empLanguage)
        jsonString = employee.getTemplatesAndConsents()
        self.parseJSONString(jsonString)
        
    def loadFromJSONString(self, jsonString):
        self.parseJSONString(jsonString)
        
    def clear(self):
        self.records = []
        
    def parseJSONString(self, jsonString):
        """
        Parses the supplied string to extract the consents and store them in the internal
        consentList
        
        The string is expected to be the complete JSON string for templates, as in this
        example:
        
            {
                "Templates": ["VWxOclRrWkpkM0ZXVlZsb..."],
                "Info": {"fingerInfo": [{"code": "ri", "quality": 70}], "numTemplates": 4},
                "Consents": [
                    {
                        "id": "f0d8d4d1-efc9-3501-e47a-0672aa8063dc",
                        "usage": "finger",
                        "source": "[DEVICE-ID]",
                        "time": "2022-01-12T11:30:00",
                        "expiry": "2023-01-12T11:30:00",
                        "action": "expired",
                        "consentText": "",
                        "templateHashes": ""
                    },
                    {
                        "id": "0c8d3abe-2187-3bf7-1f41-b60ddbd8f272",
                        "usage": "finger",
                        "source": "[DEVICE-ID]",
                        "time": "2023-01-12T11:30:00",
                        "expiry": "2024-01-12T11:30:00",
                        "action": "accepted",
                        "consentText": "",
                        "templateHashes": ""
                    }
            
                ]
            }
        """
        self.records = []
        try:
            if jsonString.strip() == "":
                return
            jsonConsents = json.loads(jsonString)
            if "Consents" in jsonConsents:
                for consent in jsonConsents["Consents"]:
                    record = ConsentRecord()
                    record.consentId = consent["id"]
                    record.source = consent["source"]
                    record.time = consent["time"]
                    record.expiry = consent["expiry"]
                    record.action = consent["action"]
                    record.consentText = consent["consentText"]
                    record.templateHashes = consent["templateHashes"]
                    self.records.append(record)
            else:
                log.dbg("No consents found for employee")
        except Exception as e:
            log.err("Failed to load Consent Records: {}".format(e))
            raise e

    def count(self):
        """Returns the number of Consent records held"""
        return len(self.records)

    def add(self, atTime, expiry, action, text):
        """Adds a new Consent Record with the supplied values. Any or all of 
        these can be None, in which case the default values will be used.
        """ 
        record = ConsentRecord()
        if atTime is not None:
            record.time = atTime # Date/time of Consent
        if expiry is not None:
            record.expiry = expiry # Date/time of Consent Expiry
        if action is not None:
            record.action = action # ConsentStatus
        if text is not None:
            record.consentText = base64.b64encode(text)
        # Insert the new consent as the first entry in the list, so that it
        # is used as the active consent
        self.records.insert(0, record)

    def getActiveConsent(self):
        if len(self.records) > 0:
            return self.records[0]
        else:
            return None

    def getActiveStatus(self):
        """Returns the ConsentStatus for the active record (the first consent 
        in the list).
        
        Returns a status of PENDING if there is no active record.
        """
        if len(self.records) > 0:
            return self.records[0].action
        else:
            return ConsentStatus.PENDING
        
    def getStatus(self, atDate=None):
        """Returns the ConsentStatus for the active record (the first consent 
        in the list). Usually this will simply be the `action` value, ACCEPTED
        or RENEWED. 
        
        However, it will also check the expiry date, and will return EXPIRING 
        if the consent is within the expiring period, or EXPIRED if the expiry 
        date has already been passed. 
        
        It will return PENDING if there are no consents, or if the consent 
        record is invalid.
        """
        if atDate is None:
            atDate = datetime.datetime.utcnow()
        if len(self.records) > 0:
            result = self.records[0].action
            record = self.records[0]
            if (record.expiry.strip() == ""):
                # We have an invalid record -- there is no Expiry date
                result = ConsentStatus.PENDING
            else:
                expiryDate = timeUtils.getUTCDatetimeFromISO8601(record.expiry)
                delta = expiryDate - atDate
                if (delta.days < 0):
                    result = ConsentStatus.EXPIRED
                elif (delta.days < self.config.getDaysToGiveWarning()):
                    result = ConsentStatus.EXPIRING
                else:
                    result = record.action
        else:
            result = ConsentStatus.PENDING

        return result 
        
    def asJSON(self):
        """Convert the records to JSON objects and return as a list."""
        jsonList = []
        for record in self.records:
            jsonList.append(
                {
                    "id": record.consentId,
                    "usage": "finger",
                    "source": record.source,
                    "time": record.time,
                    "expiry": record.expiry,
                    "action": record.action,
                    "consentText": record.consentText,
                    "templateHashes": record.templateHashes
                }
            )
        return jsonList

    def queueConsentData(self, empId, data):
        """ Queue consent data (XML string) to be send to server. """
        updateQueue = webClient.getAppEmpUpdatesQueue()
        updateQueue.addConsent(empId, data)

class ConsentMessages(object):
    """Class to return the various Consent messages in the correct (XML) format.
    
    This is only used for consent-only messages. Messages which include the 
    full template data will use the standard XML created by the Employee
    Updates system."""
    
    XMLTemplate = """<employee>
   <empID>%s</empID>
       <time>%s</time>
       <consentData>%s</consentData>
       <templates reason="%s"></templates>
</employee>"""
    
    @staticmethod
    def declineFinger(empId, base64ConsentData):
        timeStr = timeUtils.getXMLTimestampNow()
        data = ConsentMessages.XMLTemplate % (empId, timeStr, base64ConsentData, ConsentReason.ConsentDeclined)
        return data

    @staticmethod
    def deleteFinger(empId, base64ConsentData):
        timeStr = timeUtils.getXMLTimestampNow()
        data = ConsentMessages.XMLTemplate % (empId, timeStr, base64ConsentData, ConsentReason.UserDeleted)
        return data

    @staticmethod
    def deferFingerRenewal(empId, base64ConsentData):
        timeStr = timeUtils.getXMLTimestampNow()
        data = ConsentMessages.XMLTemplate % (empId, timeStr, base64ConsentData, ConsentReason.ConsentDeferred)
        return data
        
    @staticmethod
    def fingerConsentTimedOut(empId, base64ConsentData):
        timeStr = timeUtils.getXMLTimestampNow()
        data = ConsentMessages.XMLTemplate % (empId, timeStr, base64ConsentData, ConsentReason.ConsentTimedOut)
        return data
        
    @staticmethod
    def fingerConsentCancelled(empId, base64ConsentData):
        timeStr = timeUtils.getXMLTimestampNow()
        data = ConsentMessages.XMLTemplate % (empId, timeStr, base64ConsentData, ConsentReason.ConsentCancelled)
        return data
