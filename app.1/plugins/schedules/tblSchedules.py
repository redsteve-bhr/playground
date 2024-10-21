# -*- coding: utf-8 -*-
#
# Copyright 2023 Grosvenor Technology
#
from applib.db.table import Table
from applib.db.database import getAppDB

_appSchedules = None

class Schedule(object):
    
    def __init__(self, empID='', shiftID='', startDateTime='', endDateTime=''):
        self.empID = empID
        self.shiftID = shiftID
        self.startDateTime = startDateTime
        self.endDateTime = endDateTime

    def record(self):
        """Returns a dictionary with the supplied Schedule data. The returned 
        dict is compatible with the Table.insert() method
        """
        return {"EmpID": self.empID, "ShiftID": self.shiftID, "StartDateTime": self.startDateTime, "EndDateTime": self.endDateTime}

class LastPunch(object):
    
    def __init__(self, empID='', punchTime='', punchType='*'):
        self.empID = empID
        self.punchTime = punchTime
        self.punchType = punchType
            
def getAppSchedules():
    """ Return global Schedules table. """
    global _appSchedules
    if (_appSchedules == None):
        _appSchedules = _TblSchedules()
        _appSchedules.open()
    return _appSchedules

class _TblSchedules(Table):
    columnDefs = { 
                   'ID'           : 'INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL',
                   'EmpID'        : 'TEXT NOT NULL DEFAULT ""',
                   'ShiftID'      : 'TEXT NOT NULL DEFAULT ""',
                   'StartDateTime': 'TEXT NOT NULL DEFAULT ""',
                   'EndDateTime'  : 'TEXT NOT NULL DEFAULT ""'
                 }

    def __init__(self, db=None, tableName='tblSchedules'):
        if (db == None):
            db = getAppDB()
        super(_TblSchedules, self).__init__(db, tableName)

    def schedule(self, empID='', shiftID='', startDateTime='', endDateTime=''):
        """Returns a dictionary with the supplied Schedule data. The returned 
        dict is compatible with the Table.insert() method
        """
        return {"EmpID": empID, "ShiftID": shiftID, "StartDateTime": startDateTime, "EndDateTime": endDateTime}
        
    def getSchedulesByEmpID(self, empID):
        sql = "SELECT * FROM %s WHERE EmpID = ? ORDER BY StartDateTime ASC" % self.tableName
        rows = self.runSelectAll(sql, (empID,))
        return rows

    def getScheduleByEmpIdAndActiveDate(self, empID, curTime):
        sql = "SELECT * FROM %s WHERE EmpId = ? AND ? >= StartDateTime AND ? <= EndDateTime ORDER BY StartDateTime" % self.tableName
        rows = self.runSelectAll(sql, (empID, curTime, curTime))
        return rows

    def deleteAll(self):
        sql = "DELETE from %s" % self.tableName
        self.runQuery(sql)
    
    def deleteByEmpId(self, empID):
        sql = "DELETE FROM %s WHERE empID = ?" % self.tableName
        self.runQuery(sql, (empID, ))
        
    def deleteByShiftID(self, shiftID):
        sql = "DELETE FROM %s WHERE shiftID = ?" % self.tableName
        self.runQuery(sql, (shiftID, ))
    
    def count(self):
        sql = "SELECT COUNT (*) FROM %s" % self.tableName
        row = self.runSelectOne(sql)
        return row[0]
    
    def getAllSchedulesShiftIDs(self):
        sql = "SELECT shiftID from %s" % self.tableName
        rows = self.runSelectAll(sql)
        return rows
    
    def getAllSchedules(self):
        sql = "SELECT * from %s" % self.tableName
        rows = self.runSelectAll(sql)
        return rows
    
    def getAllSchedulesByEmployee(self):
        sql = "SELECT * from %s ORDER BY EmpID" % self.tableName
        rows = self.runSelectAll(sql)
        return rows
    
    def getSchedulesByShiftID(self, shiftID):
        sql = "SELECT * FROM %s WHERE shiftID = ? ORDER BY StartDateTime ASC" % self.tableName
        rows = self.runSelectAll(sql, (shiftID, ))
        return rows

    def getSchedule(self, empID, shiftID):
        sql = "SELECT * FROM %s WHERE empID = ? AND shiftID = ?" % self.tableName
        row = self.runSelectOne(sql, (empID, shiftID, ))
        return row
