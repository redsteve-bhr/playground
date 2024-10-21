# -*- coding: utf-8 -*-
#
# Copyright 2013 Grosvenor Technology
#

"""
:mod:`tblAntipassback` --- Antipassback class
===============================================

The antipassback time is checked against a particular badge for a particular node/location.
This table provides an easy mechanism to check a badge code against the entries stored
in the table and to save the new code, the time and the node in the table

Example::

    if (self.settings.get('app_antipassback_enable')):
        period = self.settings.get('app_antipassback_time')
        if (not self.antiPassback.checkAndSave(clockingTime, badgeCode, 0, period)):
            itg.msgbox(itg.MB_OK, "Failed Anti-passback (%s)" % badgeCode)
            return
            

"""

from applib.db import database, table, sqlTime
import datetime

_appAntipassback = None

def getAppAntipassback():
    global _appAntipassback
    if (_appAntipassback == None):
        _appAntipassback = TblAntipassback()
        _appAntipassback.open()
    return _appAntipassback


class TblAntipassback(table.Table):
    """ Create an TblAntipassback instance
    
    :param db: is the database object (Database)
    
    """

    columnDefs = {  'RecID'     : 'INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL',
                    'BadgeCode' : 'TEXT NOT NULL',
                    'Node'      : 'INTEGER NOT NULL',
                    'Time'      : 'TIMESTAMP NOT NULL',
                    'ExpiryTime': 'TIMESTAMP NOT NULL' }
 
    def __init__(self, db=None):
        if (db == None):
            db = database.getAppMemDB()
        super(TblAntipassback, self).__init__(db, "tblAntipassback")


    def add(self, clockingTime, badgeCode, node, period):
        # expiryTime is current time + period seconds
        expiryTime = self.getExpiryTimestampNow(clockingTime, period)
        sql = 'INSERT INTO tblAntipassback (BadgeCode, Node, Time, ExpiryTime) VALUES (?,?,?, ?)'
        self.runQuery(sql, (badgeCode, node, clockingTime, expiryTime))


    def deleteExpiredData(self, clockingTime, badgeCode, node):
        """ Deletes all occurrences of a badgeCode node pair and all expired data
        
         :param badgeCode: is the code to delete for the associated node
         :param node: is the associated node
        """
        sql = "DELETE FROM tblAntipassback WHERE BadgeCode = ? AND Node = ? OR (ExpiryTime < ?)"
        self.runQuery(sql, (badgeCode, node, clockingTime))


    def getExpiryTimestampNow(self, clockingTime, timeout):
        """ Get the antipassback expiry time as a timestamp

        :param clockingTime: time of clocking as SQL time string
        :param timeout: is the period time in seconds        
        :return: The expiry time as a time stamp
        """
        period = datetime.timedelta(seconds=timeout)
        expiryTime = datetime.datetime.strptime(clockingTime, sqlTime.sqlTimeFormat) + period
        return expiryTime.strftime(sqlTime.sqlTimeFormat)
  
        
    def save(self, clockingTime, badgeCode, node, period):
        """ Add a transaction to the antipassback table
        
        :param clockingTime: time of clocking as SQL time string
        :param badgeCode: is the code to add
        :param node: is the location / reader / clocking type to check against
        :param period: is the time in seconds in which clockings are not allowed
        """
        self.deleteExpiredData(clockingTime, badgeCode, node)
        self.add(clockingTime, badgeCode, node, period)


    def check(self, clockingTime, badgeCode, node):
        """ Check to see whether the antipassback test passes
         
        :param clockingTime: time of clocking as SQL time string         
        :param badgeCode: is the code to validate
        :param node: is the location / reader / clocking type to check against
        :return: True if there was no clocking within last period
        """
        
        sql = '''SELECT COUNT (*) FROM %s 
                WHERE BadgeCode = ? AND Node = ?
                AND (ExpiryTime > ?)''' % self.tableName
        count = self.runSelectOne(sql, (badgeCode, node, clockingTime))
        return (count == None or count[0] == 0)


    def checkAndSave(self, clockingTime, badgeCode, node, period):
        """ Checks antipassback and updates the antipassback table
         
         :param badgeCode: is the code to validate
         :param node: is the node where the swipe occurred
         :param period: is the antipassback time to use in seconds
         :return: True if there was no clocking within last period
        """
        rc = self.check(clockingTime, badgeCode, node)
        if (rc):
            self.save(clockingTime, badgeCode, node, period)
        return rc 


