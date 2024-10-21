# -*- coding: utf-8 -*-
#
# Copyright 2023 Grosvenor Technology
#
from applib.db.table import Table
from applib.db.database import getAppDB

_appJobCodes = None

class JobCode(object):
    
    def __init__(self, jobCodeID='', jobCategoryID='', code='', name=''):
        self.jobCodeID = jobCodeID
        self.jobCategoryID = jobCategoryID
        self.code = code
        self.name = name

    def record(self):
        """Returns a dictionary with the supplied Job Code data. The returned
        dict is compatible with the Table.insert() method
        """
        return {"JobCodeID": self.jobCodeID, "JobCategoryID": self.jobCategoryID, "Code": self.code,
                "Name": self.name}
            
def getAppJobCodes():
    """ Return global Job Codes table. """
    global _appJobCodes
    if (_appJobCodes == None):
        _appJobCodes = _TblJobCodes()
        _appJobCodes.open()
    return _appJobCodes

class _TblJobCodes(Table):
    columnDefs = { 
                   'ID'             : 'INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL',
                   'JobCodeID'      : 'TEXT NOT NULL DEFAULT ""',
                   'JobCategoryID'  : 'TEXT NOT NULL DEFAULT ""',
                   'Code'           : 'TEXT NOT NULL DEFAULT ""',
                   'Name'           : 'TEXT NOT NULL DEFAULT ""'
                 }

    def __init__(self, db=None, tableName='tblJobCodes'):
        if (db == None):
            db = getAppDB()
        super(_TblJobCodes, self).__init__(db, tableName)

    def jobCode(self, jobCodeID='', jobCategoryID='', code='', name=''):
        """Returns a dictionary with the supplied Job Code data. The returned
        dict is compatible with the Table.insert() method
        """
        return {"JobCodeID": jobCodeID, "JobCategoryID": jobCategoryID, "Code": code, "Name": name}

    def deleteAll(self):
        sql = "DELETE from %s" % self.tableName
        self.runQuery(sql)
    
    def count(self):
        sql = "SELECT COUNT (*) FROM %s" % self.tableName
        row = self.runSelectOne(sql)
        return row[0]
    
    def getAllJobCodes(self):
        sql = "SELECT * from %s" % self.tableName
        rows = self.runSelectAll(sql)
        return rows
    
    def getJobCode(self, jobCodeID):
        sql = "SELECT * FROM %s WHERE jobCodeID = ?" % self.tableName
        row = self.runSelectOne(sql, (jobCodeID, ))
        return row

    def getJobCodesByJobCategoryID(self, jobCategoryID):
        sql = "SELECT * FROM %s WHERE jobCategoryID = ?" % self.tableName
        rows = self.runSelectAll(sql, (jobCategoryID, ))
        return rows

    def getAllJobCodeIDs(self):
        sql = "SELECT ID, JobCodeID from %s" % self.tableName
        rows = self.runSelectAll(sql)
        ids = {}
        for row in rows:
            ids[row['JobCodeID']] = row['ID']
        return ids

    def deleteByJobCodeID(self, jobCodeID):
        sql = "DELETE FROM %s WHERE JobCodeID = ?" % self.tableName
        self.runQuery(sql, (jobCodeID, ))
