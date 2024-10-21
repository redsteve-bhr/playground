# -*- coding: utf-8 -*-
#
# Copyright 2015 Grosvenor Technology
#

import log
import threading
import base64
from contextlib import closing
from collections import namedtuple
import xml.etree.cElementTree as ET
from applib.db.tblSettings import getAppSetting, getAppSettings
from applib.db import table, database
from applib.utils import jobs
import commsHelper

_syncLock = threading.Lock()
_appEmpInfos = None

_EmpInfo = namedtuple('_EmpInfo', ['empID', 'infoTypeID', 'revision', 'title', 'contentType', 'encoding', 'data']) 
_DeletedEmpInfo = namedtuple('_DeletedEmpInfo', ['empID', 'infoTypeID', 'revision'])

def getAppEmpInfo():
    """ Return global employeeInfos table. """
    global _appEmpInfos
    if (_appEmpInfos == None):
        _appEmpInfos = _TblEmpInfo()
        _appEmpInfos.open()
    return _appEmpInfos


def _parseRecordIDs(stream):
    """ Parse and return all record identifier (ID and type). """
    for (_ev, elem) in ET.iterparse(stream):
        if (elem.tag == 'employeeInfo'):
            # return ID and type and free elements
            yield (elem.find('empID').text, elem.find('infoTypeID').text)
            elem.clear()

def _requestAllIDs(conn):
    """Request list of all identifier (ID and type) from server. """
    stream = commsHelper.httpStreamRequest(conn, 'GET', '/employeeInfoIDs')
    recordIDs = set(_parseRecordIDs(stream))
    return recordIDs

def _parseUpdates(stream, optAttribs=None):
    """ Parse and return changed records. """
    for (_ev, elem) in ET.iterparse(stream):
        if (elem.tag == 'employeeInfo'):
            payloadTag = elem.find('payload')
            if (payloadTag == None):
                yield _DeletedEmpInfo(elem.find('empID').text,
                              elem.find('infoTypeID').text,
                              elem.find('revision').text)
            else:
                yield _EmpInfo(elem.find('empID').text,
                              elem.find('infoTypeID').text,
                              elem.find('revision').text,
                              elem.find('title').text,
                              payloadTag.get('contentType'),
                              payloadTag.get('encoding'),
                              payloadTag.text)
            # free memory
            elem.clear()
        elif (elem.tag == 'employeeInfoRecords' and optAttribs!=None):
            optAttribs.update(elem.attrib)

def _getRevision():
    """ Return last known revision. """
    return getAppSetting('webclient_employeeinfo_revision')

def _saveRevision(revision):
    """ Save new revision. """
    if (revision != getAppSetting('webclient_employeeinfo_revision')):
        getAppSettings().set('webclient_employeeinfo_revision', revision)

def _syncUpdates(localTbl, conn, forceResync):
    """ Request all changes after revision and apply to table. Last
        revision is updated at the end and the number of received
        records and total records on the server is returned.
    """
    revision = _getRevision() if not forceResync else None
    log.dbg('Requesting updates (revision since %s)' % revision)
    extraParams = {}
    if (revision):
        extraParams['Revision'] = revision
    stream = commsHelper.httpStreamRequest(conn, 'GET', '/employeeInfo', None, extraParams)
    # parse every employee entry
    optAttribs = {}
    numReceived = 0
    for empInfo in _parseUpdates(stream, optAttribs):
        # count received updates
        numReceived += 1
        # add, update or delete record
        if (type(empInfo) is _DeletedEmpInfo or empInfo.contentType==None):
            localTbl.removeEmpInfo(empInfo.empID, empInfo.infoTypeID)
        else:
            localTbl.addEmpInfoToDB(empInfo)
        revision = empInfo.revision
    # went through all requests, we assume that the
    # server does not have any more entries with the 
    # the same revision field
    if (numReceived > 0):
        _saveRevision(revision)
    # return number of received updates and total server count
    totalServerCount = optAttribs.get('totalEmployeeInfoCount')
    if (totalServerCount == None):
        raise Exception('total server count not specified!')
    return (numReceived, int(totalServerCount))

def syncEmployeeInfo(forceResync=False):
    """ Synchronise employee info. 

        This function connects to the server and requests all updates
        after the last known revision. After that and if the total server
        count is not the same as the local count, all IDs are requested
        and compared with all local IDs to detect records that were deleted
        on the server. These records are then deleted locally.
    """
    with _syncLock:    
        localTbl = getAppEmpInfo()
        # create connection object to be shared
        with closing(commsHelper.openHttpConnection()) as conn:
            while True:
                # request all new and updated employees and receive total count
                (numReceived, serverCount) = _syncUpdates(localTbl, conn, forceResync)
                # run again until we receive no updates
                if (numReceived == 0):
                    break
            # compare with local count
            if (serverCount != None and serverCount != localTbl.count()):
                # the counts are not the same so employee info may have been deleted from server
                localIDs = localTbl.getAllIDs()
                log.dbg('Count mismatch, local: %d server: %s' % (len(localIDs), serverCount))
                # request all IDs from server
                serverIDs = _requestAllIDs(conn)
                deletedIDs = localIDs - serverIDs
                log.dbg('Records on server: %d local: %d deleting: %d' % (len(serverIDs), len(localIDs), len(deletedIDs)))
                for (empID, infoTypeID) in deletedIDs:
                    localTbl.removeEmpInfo(empID, infoTypeID)



class _EmployeeInfoRequestResponse(object):
    
    def __init__(self, title=None, contentType=None, data=None):
        self.__title = title
        self.__contentType = contentType
        self.__data = data
    
    def getTitle(self):
        return self.__title
 
    def getData(self):
        return self.__data
    
    def getContentType(self):
        return self.__contentType


def _parseEmployeeInfoResponse(data):
    """ Parse XML string and return _EmployeeInfoRequestResponse object. """
    root = ET.fromstring(data)
    title = None
    decodedData = None
    titleTag = root.find('title')
    if (titleTag != None):
        title = titleTag.text
    payload = root.find('payload')
    encoding = payload.get('encoding')
    contentType = payload.get('contentType')
    if (encoding == 'base64'):
        decodedData = base64.b64decode(payload.text)
    else:
        decodedData = payload.text
    if (title != None or contentType != None or decodedData != None):   
        return _EmployeeInfoRequestResponse(title, contentType, decodedData)
    return None

 
class EmployeeInfoRequest(jobs.Job):
    """This is used for the on-demand employee info requests""" 
    def __init__(self, employee, infoTypeID):
        super(EmployeeInfoRequest, self).__init__()
        self.__emp    = employee
        self.__infoTypeID = infoTypeID
        self.__infoRequestResponse = None
     
    def getName(self):
        return self.__infoTypeID
     
    def getResponse(self):
        return self.__infoRequestResponse

    def execute(self):
        with closing(commsHelper.openHttpConnection()) as conn:
            data = commsHelper.httpGet(conn, '/employeeInfo/%s/%s' % (self.__emp.getEmpID(), self.__infoTypeID)) 
        self.__infoRequestResponse = _parseEmployeeInfoResponse(data)

  

class _TblEmpInfo(table.Table):

    columnDefs = { 'EmpID'       : 'TEXT',
                   'InfoTypeID'  : 'TEXT',
                   'ContentType' : 'TEXT',
                   'Title'       : 'TEXT',
                   'Encoding'    : 'TEXT',
                   'Data'        : 'TEXT', }

    tableConstraints = [ 'PRIMARY KEY (EmpID, InfoTypeID)' ]  
    
    def __init__(self, db=None, tableName='tblEmpInfo'):
        if (db==None):
            db = database.getAppDB()
        super(_TblEmpInfo, self).__init__(db, tableName)
            
    def getEmpInfo(self, empID, infoTypeID):
        """ Return _EmployeeInfoRequestResponse object or None. """
        sql = 'SELECT * FROM %s WHERE EmpID = ? AND InfoTypeID = ?' % self.tableName
        row = self.runSelectOne(sql, (empID, infoTypeID,))
        if (row == None):
            return None
        title = row['Title']
        payload = row['Data']
        encoding = row['Encoding']
        contentType = row['ContentType']
        if (encoding == 'base64'):
            decodedData = base64.b64decode(payload)
        else:
            decodedData = payload
        if (title != None or contentType != None or decodedData != None):   
            return _EmployeeInfoRequestResponse(title, contentType, decodedData)
        return None

    def getAllIDs(self):
        """ Return set with all emp info identifier (ID and type). """
        ids = set()
        sql = 'SELECT EmpID, InfoTypeID FROM %s' % self.tableName
        rows = self.runSelectAll(sql)
        for row in rows:
            ids.add((row['EmpID'],row['InfoTypeID']))
        return ids
    
    def addEmpInfoToDB(self, empInfo):
        sql = 'INSERT OR REPLACE INTO %s (EmpID, InfoTypeID, ContentType, Title, Encoding, Data) VALUES (?,?, ?, ?, ?, ?)' % self.tableName
        self.runQuery(sql, (empInfo.empID, empInfo.infoTypeID, empInfo.contentType, empInfo.title, empInfo.encoding, empInfo.data))
        
    def removeEmpInfo(self, empID, infoTypeID):
        sql = 'DELETE FROM %s WHERE EmpID = ? AND InfoTypeID = ?' % self.tableName
        self.runQuery(sql, (empID, infoTypeID))

