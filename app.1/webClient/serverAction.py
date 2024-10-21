# -*- coding: utf-8 -*-
#
# Copyright 2023 Grosvenor Technology
#
"""Classes and functions to handle Server Action Requests"""
import xml.etree.cElementTree as ET
import httplib
import log
from applib.utils import timeUtils
from plugins.schedules import tblSchedules
from miscUtils import getElementText
import onlineState
# Wrapped to prevent circular reference issues. Issue occurs during manual/build_doc.py.
try:
    from webClient import commsHelper
except ImportError:
    log.dbg("Error while importing: {}".format(str(ImportError)))

# Constants
WC_SERVER_ACTION_PREFIX = "/serveractionrequest"

INTERFACE_XML = """
<interface>
    <action>{actionName}</action>
    <requestedOn>{requestedOn}</requestedOn>
    <requestType>POST</requestType>
    <payload>
        {itemList}
    </payload>
</interface>"""

ITEM_XML = """<item key="{itemKey}">{itemValue}</item>\n"""

ACTION_GETPUNCHRESTRICTIONS = 'GetPunchRestrictions'
ACTION_SENDATTESTATIONRESPONSE = 'SendAttestationResponse'
ACTION_FINDCATCHUPTIMECARDS = 'FindCatchupTimecards'
ACTION_STARTATTESTATION = 'StartAttestation'
ACTION_GETOVERRIDES = 'GetOverrides'

SERVERSTATUS_UNKNOWN = 'Unknown'
SERVERSTATUS_SUCCESS = 'Success'
SERVERSTATUS_FAILURE = 'Failed'
SERVERSTATUS_TIMEOUT = 'Timeout'

class ServerResponse(object):
    """Wrapper for details of result of a Server Action call."""
    
    def __init__(self):
        self.resultElement = None
        self.status = SERVERSTATUS_UNKNOWN
        
def makeRequest(actionName, data):
    serverResponse = ServerResponse()
    try:
        conn = commsHelper.openHttpConnection()
        response = commsHelper.httpPost(conn, WC_SERVER_ACTION_PREFIX + '/' + actionName, data)
        serverResponse.status = SERVERSTATUS_SUCCESS
        onlineState.setIsOnline(True)
    except httplib.HTTPException as e:
        serverResponse.status = SERVERSTATUS_FAILURE
        log.err('Server request failed: %s' % str(e))
        onlineState.setIsOnline(False)
        return serverResponse
    except Exception as e:
        log.err('Server request failed: %s' % str(e))
        return None

    # Check to see if the server returned a response body that is not empty for parsing
    if response is not None and response != "":
        responseXml = unwrapResponse(response)
        serverResponse.resultElement = responseXml

    return serverResponse
    
def wrapRequest(actionName, items):
    itemsXml = ""
    for item in items:
        # Each item is assumed to be a dict with 'key' and 'value'
        itemsXml += ITEM_XML.format(itemKey=item['key'], itemValue=item['value'])

    requestedOn = timeUtils.getXMLTimestampNow()
    wrappedXml = INTERFACE_XML.format(actionName=actionName, requestedOn=requestedOn, itemList=itemsXml)

    # For debug (the netTrace call in commsHelper will escape any CDATA section, giving misleading output)    
    lines = wrappedXml.split('\n')
    for line in lines:
        if line != "":
            log.info(line)
    
    return wrappedXml

def unwrapResponse(xmlStr):
    root = ET.fromstring(xmlStr)
    tagName = "Result"
    if root.tag == "ServerActionResponse":
        resultElement = root.find(tagName)
        if resultElement is not None:
            return resultElement
        else:
            log.err("No 'Result' element found in response")
            resultElement = None
    else:
        log.warn("Expected response root of 'ServerActionResponse' but found '%s'" % root.tag)
        # Assume that this must be non-wrapped XML and return it as-is
        resultElement = root
    
    return resultElement

def getCDATA(data):
    """Wraps the supplied data (assumed to be an XML string) in a CDATA section"""
    return "<![CDATA[{data}]]>".format(data=data)

def buildPunchRestrictionsRequestXml(transactionXml, employeeID):
    items = [
        {'key': 'empId', 'value': employeeID},
        {'key': 'transaction', 'value': getCDATA(transactionXml)}
    ]
    return wrapRequest(ACTION_GETPUNCHRESTRICTIONS, items)

def buildSendAttestationResponseXml(transactionXml, employeeID):
    items = [
        {'key': 'empId', 'value': employeeID},
        {'key': 'tx', 'value': getCDATA(transactionXml)}
    ]
    return wrapRequest(ACTION_SENDATTESTATIONRESPONSE, items)

def buildCatchupTimecardsRequestXml(employeeID):
    items = [
        {'key': 'empId', 'value': employeeID}
    ]
    return wrapRequest(ACTION_FINDCATCHUPTIMECARDS, items)

def buildStartAttestationRequestXml(transactionXml, employeeID):
    items = [
        {'key': 'empId', 'value': employeeID},
        {'key': 'transaction', 'value': getCDATA(transactionXml)}
    ]
    return wrapRequest(ACTION_STARTATTESTATION, items)
    
def buildSupervisorOverridesRequestXml():
    items = [
        {'key': 'overrideStatus', 'value': 'Active'}
    ]
    return wrapRequest(ACTION_GETOVERRIDES, items, '')

class ScheduleResultData(object):
    """Class to parse and store response data from server for Schedules"""
    
    def __init__(self, element, language):
        self.supervisorOverrideActive = False
        self.hasPositiveHealthAttest = True
        self.schedules = []
        self.lastPunch = None
        if element is not None:
            scheduleResultElement = element.find('scheduleResult')
            if scheduleResultElement is not None:
                self.supervisorOverrideActive = getElementText(scheduleResultElement, 'supervisorOverrideActive', 'false').lower() == 'true'
                self.hasPositiveHealthAttest = getElementText(scheduleResultElement, 'hasPositiveHealthAttest', 'true').lower() == 'true'
                self.schedules = self.parseSchedulesElement(scheduleResultElement)
                self.lastPunch = self.parseLastPunchElement(scheduleResultElement)
            else:
                log.warn('No schedule result data found. Using defaults.')
        else:
            log.warn('No schedule result data found. Using defaults.')
        
    def parseSchedulesElement(self, element):
        scheduleList = []
        schedulesElements = element.find('schedules')
        if schedulesElements is not None:
            scheduleElements = schedulesElements.findall('schedule')
            for scheduleElement in scheduleElements:
                shiftID = getElementText(scheduleElement, 'externalSchId')
                empID = getElementText(scheduleElement, 'empID')
                startDateTime = getElementText(scheduleElement, 'allowedStart')
                endDateTime = getElementText(scheduleElement, 'allowedEnd')
                schedule = tblSchedules.Schedule(empID, shiftID, startDateTime, endDateTime)
                scheduleList.append(schedule)
        else:
            log.err("No schedules element found in Schedules XML")
        return scheduleList

    def parseLastPunchElement(self, element):
        lastPunch = None
        lastPunchElement = element.find('lastPunch')
        if lastPunchElement is not None:
            empID = getElementText(lastPunchElement, 'empID')
            punchTime = getElementText(lastPunchElement, 'time')
            # punchType = getElementText(lastPunchElement, 'type')
            lastPunch = tblSchedules.LastPunch(empID, punchTime)
        else:
            log.warn("No Last Punch element found in Schedules XML")
        return lastPunch
