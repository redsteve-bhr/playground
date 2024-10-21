# -*- coding: utf-8 -*-
#
# Copyright 2010 Grosvenor Technology
#

import uuid
import log
import datetime
import base64

from applib.db import database, table, sqlTime


class TblLastClockingsData(table.Table):
    """ Create table instance. *db* is used if supplied. If *db* is **None**
    the application database is used (via :meth:`applib.db.database.getAppDB()`).
    *keepTimeInDays* if given specifies when entries are deleted. Too old entries 
    are automatically deleted when :meth:`TblLastClockingsData.add` is called.
    """ 
    
    columnDefs = {  'ID'    : 'TEXT PRIMARY KEY',
                    'Type'  : 'TEXT NOT NULL',
                    'Time'  : 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL',
                    'EmpID' : 'TEXT NOT NULL',
                    'Data'  : 'TEXT' }
        
    def __init__(self, db=None, keepTimeInDays=None, tableName='tblLastClockingsData'):
        if (db == None):
            db = database.getAppDB()
            
        if (keepTimeInDays == None):
            self.__keepTime = 7 * 60*60*24
        else:
            self.__keepTime = int(keepTimeInDays) * 60*60*24
        super(TblLastClockingsData, self).__init__(db, tableName)
        
        
    def open(self):
        """ Open table (create if necessary)."""
        super(TblLastClockingsData, self).open()
        log.dbg("Checking index for %s" % self.tableName)
        self.runQuery('CREATE INDEX IF NOT EXISTS %sIndex ON %s(Time DESC)' % (self.tableName, self.tableName))
        
        
    def add(self, dataType, when, empID, data=None):
        """ Add new meta data to the tables. *dataType* is a string specifying the dataType of
        data e.g. photo. *when* is a SQL time string holding the UTC
        time of the event. *empID* identifies the user who is clocking. *data* is the actual image etc.
        """
        dataID = str(uuid.uuid1())
        sql = 'INSERT INTO %s (ID, Type, Time, EmpID, Data) VALUES (?,?,?,?,?);' % self.tableName
        self.runQuery(sql, (dataID, dataType, when, empID, base64.encodestring(data)))
        self.deleteOld(when)
        return dataID


    def selectDataByUUID(self, dataID):
        sql = 'SELECT * FROM %s WHERE ID = ?' % self.tableName
        result_set = self.runSelectOne(sql, (dataID,))
        if (result_set == None):
            return (None, None)
        return (result_set['Type'], base64.decodestring(result_set['Data']))
    
    
    def selectDataByUUIDAndType(self, dataID, dataType):
        sql = 'SELECT * FROM %s WHERE ID = ? AND Type = ?' % self.tableName
        result_set = self.runSelectOne(sql, (dataID, dataType))
        if (result_set == None):
            return None
        return (base64.decodestring(result_set['Data']))
        
        

    def selectLast(self, empID, maxResults=5, localTimeFormat=None):
        """ Return last clockings. *empID* specifies the user as in :meth:`TblLastClockingsData.add`.
        The clocking time is converted to local time as well, if *localTimeFormat* is **None**
        '%x %X' is used as format (see `datetime.strftime() <http://docs.python.org/library/datetime.html#datetime.datetime.strftime>`_).
        
        This method returns a list of dictionaries containing the following elements:
        
         - *Type*
         - *Time*
         - *Data*
         - *LocalTime*
        """
        
        sql = 'SELECT * FROM %s WHERE EmpID = ? ORDER BY Time DESC LIMIT %d' % (self.tableName, maxResults)
        result_set = self.runSelectAll(sql, (empID,))
        results = []
        for i in result_set:
            results.append({ 'Type': i['Type'], 
                             'Time': i['Time'], 
                             'Data': i['Data'],
                             'LocalTime': self.__localTime(i['Time'], localTimeFormat)}) 
        return results

    def __localTime(self, time, timeFormat=None):
        try:
            if (timeFormat):
                return sqlTime.sqlTime2MyLocalTime(time, timeFormat)
            return sqlTime.sqlTime2MyLocalTime(time, '%x %X')
        except Exception as e:
            log.warn('Could not convert time to local time! (%s)' % e)
            return time

    def __getExpiryTimestamp(self, timeStamp):
        if (self.__keepTime < 0):
            return None
        period = datetime.timedelta(seconds=self.__keepTime)
        expiryTime = datetime.datetime.strptime(timeStamp, sqlTime.sqlTimeFormat) - period
        return expiryTime.strftime(sqlTime.sqlTimeFormat)
  
    def deleteOld(self, now):
        expiryTime = self.__getExpiryTimestamp(now)
        if (expiryTime == None):
            return
        sql = "DELETE FROM %s WHERE (Time < ?)" % self.tableName
        self.runQuery(sql, (expiryTime,))


def writeClockingDataToUSB(dataType, when, empID, data=None):
    if (data == None):
        return None
    try:
        usbdb = database.getUsbDB(databaseName='lastClockingsData.db', keep=True)
        extData = TblLastClockingsData(usbdb)
        extData.open()
        dataID = extData.add(dataType, when, empID, data)
        return dataID
    except database.NoWorkingUSBDeviceFoundException:
        log.dbg('No USB device found to store clocking data')    
    except Exception as e:
        log.warn('Error saving clocking data to USB (%s)' % e)
    return None

    
def readClockingDataFromUSB(dataID):
    if (dataID == None):
        return (None, None)    
    try:
        usbdb = database.getUsbDB(databaseName='lastClockingsData.db', keep=True)
        extData = TblLastClockingsData(usbdb)
        extData.open()
        (dataType, data) = extData.selectDataByUUID(dataID)
        return (dataType, data)
    except database.NoWorkingUSBDeviceFoundException:
        log.dbg('No USB device found to read clocking data')
    except Exception as e:
        log.warn('Error reading clocking data from USB (%s)' % e)
    return (None, None)

    
    
    