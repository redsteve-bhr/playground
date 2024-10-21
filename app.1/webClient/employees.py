# -*- coding: utf-8 -*-
#
# Copyright 2015 Grosvenor Technology
#

import log
import threading
import hashlib
from contextlib import closing
import xml.etree.cElementTree as ET
from applib.db.tblSettings import getAppSetting, getAppSettings
import commsHelper
import emps

_syncLock = threading.Lock()

_tagNameMapping = {  'empID'           : 'EmpID', 
                     'externalID'      : 'ExternalID',
                     'name'            : 'Name',
                     'language'        : 'Language',
                     'roles'           : 'Roles',
                     'verifyBy'        : 'VerifyBy',
                     'keypadID'        : 'KeypadID',
                     'pin'             : 'PIN',
                     'badgeCode'       : 'BadgeCode',
                     'photo'           : 'Photo',
                     'templates'       : 'Templates',
                     'displayItems'    : 'DisplayItems',
                     'homeJobCodes'    : 'HomeJobCodes',
                     'fingerTemplates' : 'Templates', # Accept both 'templates' and 'fingerTemplates' as sources for templates
                     'revision'        : 'Revision' }    
 
def _getItemMD5Hash(employee):
    """ Create MD5 of employee dictionary. """
    cols = _tagNameMapping.values()
    cols.remove('Revision') # don't include revision in MD5
    cols.sort()
    lst = []
    for c in cols:
        lst.append(unicode(employee[c]) if c in employee else '')
    return hashlib.md5( '|'.join(lst) ).hexdigest()
 
def _parseRecordIDs(stream):
    """ Parse and return all record identifier. """
    for (_ev, elem) in ET.iterparse(stream):
        if (elem.tag == 'empID'):
            # return ID and free elements
            yield elem.text
            elem.clear()

def _requestAllIDs(conn):
    """Request list of all identifier from server. """
    stream = commsHelper.httpStreamRequest(conn, 'GET', '/employeeIDs')
    recordIDs = set(_parseRecordIDs(stream))
    return recordIDs

def _parseUpdates(stream, optAttribs=None):
    """ Parse and return changed records. """
    for (_ev, elem) in ET.iterparse(stream):
        if (elem.tag == 'employee'):
            # put all employee data into dictionary
            employee = {}
            for e in elem:
                if (e.tag == 'displayItems'):
                    items = getDisplayItems(elem)
                    if items is not None:
                        jsonStr = emps._DisplayItems().compileToJSON(items)
                        employee['DisplayItems'] = jsonStr
                elif (e.tag == 'homeJobCodes'):
                    items = getHomeJobCodes(elem)
                    if items is not None:
                        jsonStr = emps._HomeJobCodes().compileToJSON(items)
                        employee['HomeJobCodes'] = jsonStr
                elif (e.tag in _tagNameMapping):
                    employee[_tagNameMapping[e.tag]] = e.text 
            # return parsed dictionary
            yield employee
            # free memory
            elem.clear()
        elif (elem.tag == 'employees' and optAttribs!=None):
            optAttribs.update(elem.attrib)

def _getRevision():
    """ Return last known revision. """
    return getAppSetting('webclient_employees_revision')

def _saveRevision(revision):
    """ Save new revision. """
    if (revision != getAppSetting('webclient_employees_revision')):
        getAppSettings().set('webclient_employees_revision', revision)

def _syncUpdates(tblEmps, conn, forceResync):
    """ Request all changes after revision and apply to table. Last
        revision is updated at the end and the number of received
        records and total records on the server is returned.
    """
    localIDsAndMD5s = tblEmps.getAllEmpIDsAndMD5s()
    revision = _getRevision() if not forceResync else None
    log.dbg('Requesting updates (revision since %s)' % revision)
    extraParams = {}
    if (revision):
        extraParams['Revision'] = revision
    stream = commsHelper.httpStreamRequest(conn, 'GET', '/employees', None, extraParams)
    # parse every employee entry
    optAttribs = {}
    numReceived = 0
    for employee in _parseUpdates(stream, optAttribs):
        # count received updates
        numReceived += 1
        # add, update or delete record
        if ('Name' in employee):
            employee['MD5'] = _getItemMD5Hash(employee)
            if (localIDsAndMD5s.get(employee['EmpID']) != employee['MD5']):
                log.dbg('Updating employee  %s' % employee['EmpID'])
                tblEmps.addOrUpdate(employee)
            else:
                log.dbg('Ignoring unchanged employee %s' % employee['EmpID'])
        else:
            log.dbg('Deleting employee %s' % employee['EmpID'])
            tblEmps.deleteByEmpID(employee['EmpID'])
        revision = employee['Revision']
    # went through all requests, we assume that the
    # server does not have any more entries with the 
    # the same revision field
    if (numReceived > 0):
        _saveRevision(revision)
    # return number of received updates and total server count
    totalServerCount = optAttribs.get('totalEmployeeCount')
    if (totalServerCount == None):
        totalServerCount = 0
        log.warn('total server count not specified!')
    return (numReceived, int(totalServerCount))

def syncEmployees(forceResync=False):
    """ Synchronise employees. 

        This function connects to the server and requests all updates
        after the last known revision. After that and if the total server
        count is not the same as the local count, all IDs are requested
        and compared with all local IDs to detect records that were deleted
        on the server. These records are then deleted locally.
    """
    with _syncLock:    
        tblEmps = emps.getAppEmps()
        # create connection object to be shared
        with closing(commsHelper.openHttpConnection()) as conn:
            while True:
                # request all new and updated employees and receive total count
                (numReceived, serverCount) = _syncUpdates(tblEmps, conn, forceResync)
                # run again until we receive no updates
                if (numReceived == 0):
                    break
            # compare with local count
            if (serverCount != None and serverCount != tblEmps.count()):
                # the counts are not the same so employees may have been deleted from the server
                localIDs = set(tblEmps.getAllEmpIDsAndMD5s()) 
                log.dbg('Count mismatch, local: %d server: %s' % (len(localIDs), serverCount))
                # request all IDs from server
                serverIDs = _requestAllIDs(conn)
                deletedIDs = localIDs - serverIDs
                log.dbg('Records on server: %d local: %d deleting: %d' % (len(serverIDs), len(localIDs), len(deletedIDs)))
                for empID in deletedIDs:
                    tblEmps.deleteByEmpID(empID)

def reSyncAllEmployees():
    syncEmployees(forceResync=True)

def getDisplayItems(elem):
    """Assumes that elem is an Employee element from an XML import, and returns any
    DisplayItems element from it. Returns None if the element cannot be found or is
    empty. 
    
    The XML format is expected to match this:
    
        <employee>
            ...
            <displayItems>
                <items>
                    <item>...</item>
                    <item>...</item>
                    ...
                </items>
            </displayItems>
            ...
        </employee>
    
    """
    result = None
    items = elem.find("displayItems")
    if items is not None:
        subItems = items.find("items")
        if subItems is not None:
            item = subItems.find("item")
            if item is not None:
                # We have at least one item entry
                result = items
    return result


def getHomeJobCodes(elem):
    """Assumes that elem is an Employee element from an XML import, and returns any
    HomeJobCodes element from it. Returns None if the element cannot be found or is
    empty.

    The XML format is expected to match this:

        <employee>
            ...
            <homeJobCodes>
                <jobCode level="...">...</jobCode>
                <jobCode level="...">...</jobCode>
                <jobCode level="...">...</jobCode>
            </homeJobCodes>
            ...
        </employee>

    """
    result = None
    items = elem.find("homeJobCodes")
    if items is not None:
        subItems = items.find("jobCode")
        if subItems is not None:
            # We have at least one item entry
            result = items
    return result
