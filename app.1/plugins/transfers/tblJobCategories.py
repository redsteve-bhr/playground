# -*- coding: utf-8 -*-
#
# Copyright 2023 Grosvenor Technology
#
from applib.db.table import Table
from applib.db.database import getAppDB

_appJobCategories = None

class JobCategory(object):

    def __init__(self, jobCategoryID='', level='', name=''):
        self.jobCategoryID = jobCategoryID
        self.level = level
        self.name = name

    def record(self):
        """Returns a dictionary with the supplied Schedule data. The returned
        dict is compatible with the Table.insert() method
        """
        return {"JobCategoryID": self.jobCategoryID, "Level": self.level, "Name": self.name}


def getAppJobCategories():
    """ Return global Job Categories table. """
    global _appJobCategories
    if (_appJobCategories == None):
        _appJobCategories = _TblJobCategories()
        _appJobCategories.open()
    return _appJobCategories


class _TblJobCategories(Table):
    columnDefs = {
        'ID'            : 'INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL',
        'JobCategoryID' : 'TEXT NOT NULL DEFAULT ""',
        'Level'         : 'TEXT NOT NULL DEFAULT ""',
        'Name'          : 'TEXT NOT NULL DEFAULT ""'
    }

    def __init__(self, db=None, tableName='tblJobCatgories'):
        if (db == None):
            db = getAppDB()
        super(_TblJobCategories, self).__init__(db, tableName)

    def jobCategory(self, jobCategoryID='', level='', name=''):
        """Returns a dictionary with the supplied Schedule data. The returned
        dict is compatible with the Table.insert() method
        """
        return {"JobCategoryID": jobCategoryID, "Level": level, "Name": name}

    def count(self):
        sql = "SELECT COUNT (*) FROM %s" % self.tableName
        row = self.runSelectOne(sql)
        return row[0]

    def deleteAll(self):
        sql = "DELETE from %s" % self.tableName
        self.runQuery(sql)

    def getJobCategoryByLevel(self, level):
        sql = "SELECT * FROM %s WHERE Level = ?" % self.tableName
        row = self.runSelectOne(sql, (level, ))
        return row

    def getAllJobCategories(self):
        sql = "SELECT * from %s" % self.tableName
        rows = self.runSelectAll(sql)
        return rows

    def getJobCategory(self, jobCategoryId):
        sql = "SELECT * FROM %s WHERE JobCategoryID = ?" % self.tableName
        row = self.runSelectOne(sql, (jobCategoryId, ))
        return row

    def getAllJobCategoryIDs(self):
        sql = "SELECT ID, JobCategoryID from %s" % self.tableName
        rows = self.runSelectAll(sql)
        ids = {}
        for row in rows:
            ids[row['JobCategoryID']] = row['ID']
        return ids

    def deleteByJobCategoryID(self, jobCategoryID):
        sql = "DELETE FROM %s WHERE JobCategoryID = ?" % self.tableName
        self.runQuery(sql, (jobCategoryID, ))
