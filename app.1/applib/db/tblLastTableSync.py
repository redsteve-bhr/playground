# -*- coding: utf-8 -*-
#
# Copyright 2010 Grosvenor Technology
#

"""
:mod:`tblLastTableSync` --- Hold information about table synchronisation
========================================================================

:class:`TblLastTableSync` is a :class:`applib.db.table.Table` class which helps deciding
whether new data is actually different from what is in a table. It also keeps
the date of the last synchronisation.

The term synchronisation used here means a one-way server to terminal
synchronisation in which data (e.g. a table) is simply replaced by a more 
recent version from a server. To not replace the content of a table with
what is already in it, a MD5 checksum over the data in its original form
(e.g. XML) is stored in :class:`TblLastTableSync` and can be compared just 
before replacing the table with the checksum of the new data.
      
Example::

    # [...]

    def importFromXML(self, xmlData):
        # get current MD5
        lastTableSync = tblLastTableSync.TblLastTableSync()
        lastTableSync.open()
        (lastSync, lastMD5) = lastTableSync.getByTableName(self.tableName)
        
        # calculate MD5 of new data
        newMD5 = hashlib.md5(xmlData).hexdigest()
        if (newMD5 == lastMD5):
            log.dbg('Not applying data for %s, no changes.' % self.tableName)
            return
            
        # import data from XML ...
        # [...]
        
        # after importing
        lastTableSync.setSynched(self.tableName, newMD5)

In addition to the MD5 checksum, the time a table was synchronised last is also stored in 
:class:`TblLastTableSync`. If a table was never synchronised, the time is set to **None**.

.. note::
    :class:`TblLastTableSync` does not keep track of MD5 checksums and synchronisation 
    times automatically. Instead the MD5 checkums need to be created, compared and updated 
    manually. 
    
    
    

"""

from applib.db import database, table
import appit
import hashlib

class TblLastTableSync(table.Table):
    """ Create instance of class. The application database (via :func:`applib.db.database.getApPDB()`)
    is used if *db* is **None**. By specifing *tableName* it is possible to have multiple :class:`TblLastTableSync`
    tables, in case this is ever needed.
    """

    columnDefs = {  'TableName'     : 'TEXT UNIQUE NOT NULL PRIMARY KEY',
                    'LastSync'      : 'TEXT',
                    'LastMD5'       : 'TEXT' }

    def __init__(self, db=None, tableName='tblLastTableSync'):
        if (db==None):
            db= database.getAppDB()
        super(TblLastTableSync, self).__init__(db, tableName)

    def selectByTableName(self, tableName):
        sql = 'SELECT * FROM %s WHERE TableName = ?' % self.tableName
        return self.runSelectOne(sql, (tableName,))

    def getByTableName(self, tableName):
        """ Return last synchronisation time and MD5 checksum."""
        res = self.selectByTableName(tableName)
        return (res['LastSync'], res['LastMD5']) if (res != None) else (None, None)
    
    def getAllMD5s(self):
        """ Return dictionary of MD5 checksums. The table names are used as keys."""
        results = self.selectAll()
        md5s = {}
        for row in results:
            md5s[row['TableName']] = row['LastMD5']
        return md5s
    
    def getAllMD5sAndLastSyncs(self):
        """ Return dictionary of MD5 checksums and last synchronisation times. 
        The table names are used as keys.
        
        .. versionadded:: 1.4

        """
        results = self.selectAll()
        data = {}
        for row in results:
            data[row['TableName']] = (row['LastMD5'], row['LastSync'])
        return data
    
    def deleteByTableName(self, tableName):
        """ Delete data for a table by its *tableName*."""
        sql = "DELETE FROM %s WHERE TableName = ?" % self.tableName
        self.runQuery(sql, (tableName,))
    
    def setMD5(self, tableName, md5sum):
        """ Set MD5 checksum of table *tableName* to *md5sum* without changing or setting
        the last synchronisation time."""
        self.deleteByTableName(tableName)
        sql = "INSERT INTO %s (TableName, LastMD5) VALUES (?, ?)" % self.tableName
        self.runQuery(sql, (tableName, md5sum))
    
    def setSynched(self, tableName, md5sum):
        """ Set MD5 checksum of table *tableName* to *md5sum* and update
        last synchronisation time."""
        self.deleteByTableName(tableName)
        sql = "INSERT INTO %s (TableName, LastSync, LastMD5) VALUES (?, CURRENT_TIMESTAMP, ?)" % self.tableName
        self.runQuery(sql, (tableName, md5sum))


def createMD5Sum(data, includeAppVersion=True):
    """ Helper function to create and return  MD5 checksum of *data* 
    with optional parameter to include the application version

    .. versionadded:: 2.2
    """
    md5sum = hashlib.md5(data).hexdigest()
    if (includeAppVersion):
        md5sum += appit.AppInfo().version()
    return md5sum

