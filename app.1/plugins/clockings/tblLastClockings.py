# -*- coding: utf-8 -*-
#
# Copyright 2010 Grosvenor Technology
#

"""
:mod:`tblLastClockings` --- Hold information about recent clockings
===================================================================

:class:`TblLastClockings` is a simple table class which can be used to 
see recent clockings or transactions. It provides a method for adding
clockings (:meth:`TblLastClockings.add`) when they happen and a method
to get past clockings (:meth:`TblLastClockings.selectLast`).

:class:`TblLastClockings` also automatically deletes too old entries.

Example for adding new clockings::

    lastClockings = tblLastClockings.TblLastClockings()
    lastClockings.open()
    lastClockings.add(clockingType, clockingTime, cardNumber)

Example for showing last 10 clockings::

    class Dialog(itg.Dialog):
        
        def __init__(self, who):
            super(Dialog, self).__init__()
            view = itg.MenuView(_('Recent Clockings'))
            view.setBackButton(_('Back'), cb=self.back)
            lastClockings = tblLastClockings.TblLastClockings()
            lastClockings.open()
            for l in lastClockings.selectLast(who, 10):
                view.appendRow(l['Type'], l['LocalTime'])
            self.addView(view)    
            



"""

import log
import datetime
import json
from applib.db import database, table, sqlTime, tblSettings

_appLastClockings = None

def getAppLastClocking():
    global _appLastClockings
    if (_appLastClockings == None):
        keepTime = tblSettings.getAppSetting('emp_last_clockings_keeptime')
        _appLastClockings = TblLastClockings(keepTimeInDays=keepTime)
        _appLastClockings.open()
    return _appLastClockings


class TblLastClockings(table.Table):
    """ Create table instance. *db* is used if supplied. If *db* is **None**
    the application database is used (via :meth:`applib.db.database.getAppDB()`).
    *keepTimeInDays* if given specifies when entries are deleted. Too old entries 
    are automatically deleted when :meth:`TblLastClockings.add` is called.
    """ 
    
    columnDefs = {  'Type'  : 'TEXT NOT NULL',
                    'Time'  : 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL',
                    'EmpID' : 'TEXT NOT NULL',
                    'Data'  : 'TEXT',
                    'Label' : 'TEXT' }
        
    def __init__(self, db=None, keepTimeInDays=None):
        if (db == None):
            db = database.getAppDB()
        if (keepTimeInDays == None):
            self.__keepTime = 7 * 60*60*24
        else:
            self.__keepTime = int(keepTimeInDays) * 60*60*24
        super(TblLastClockings, self).__init__(db, "tblLastClockings")
        
    def open(self):
        """ Open table (create if necessary)."""
        super(TblLastClockings, self).open()
        log.dbg("Checking index for %s" % self.tableName)
        self.runQuery('CREATE INDEX IF NOT EXISTS %sIndex ON %s(Time DESC)' % (self.tableName, self.tableName))
        
    def add(self, action, when, who, data=None, labels=None):
        """ Add new clocking. *action* is a string specifying the type of
        clocking (e.g. IN, OUT, etc). *when* is a SQL time string holding the UTC
        time of the event. *who* identifies the user who is clocking. *data* can be optionally
        specified to add additional data to the clockings.
        *labels* if specified is a dictionary containing text for different languages.
        """
        sql = 'INSERT INTO %s (Type, Time, EmpID, Data, Label) VALUES (?,?,?,?,?);' % self.tableName
        try:
            if (labels!=None):
                labels = json.dumps(labels)
        except Exception as e:
            log.err('Error converting last clocking labels: %s' % (e,))
            labels = None 
        self.runQuery(sql, (action, when, who, data, labels))
        self.deleteOld(when)

    def selectLast(self, who, maxResults=5, localTimeFormat=None):
        """ Return last clockings. *who* specifies the user as in :meth:`TblLastClockings.add`.
        The clocking time is converted to local time as well, if *localTimeFormat* is **None**
        '%x %X' is used as format (see `datetime.strftime() <http://docs.python.org/library/datetime.html#datetime.datetime.strftime>`_).
        
        This method returns a list of dictionaries containing the following elements:
        
         - *Type*
         - *Time*
         - *Data*
         - *LocalTime*
         - *Labels*
         
        """
        
        sql = 'SELECT * FROM %s WHERE EmpID = ? ORDER BY Time DESC LIMIT %d' % (self.tableName, maxResults)
        result_set = self.runSelectAll(sql, (who,))
        results = []
        for i in result_set:
            results.append({ 'Type': i['Type'], 
                             'Time': i['Time'], 
                             'Data': i['Data'],
                             'LocalTime': self.__localTime(i['Time'], localTimeFormat),
                             'Labels': json.loads(i['Label']) if i['Label'] else None
                             }) 
        return results


    def getLastTime(self, who, clkType, localTimeFormat=None):
        """ Return the last clocking time for the specified clocking type. *who* specifies the user as in :meth:`TblLastClockings.add`.
        The clocking time is converted to local time as well, if *localTimeFormat* is **None**
        '%x %X' is used as format (see `datetime.strftime() <http://docs.python.org/library/datetime.html#datetime.datetime.strftime>`_).
        This method returns SQL timestamp string.
        
        .. versionadded:: 1.6
        
        """
        maxResults = 1
        sql = 'SELECT * FROM %s WHERE EmpID = ? AND Type = ? ORDER BY Time DESC LIMIT %d' % (self.tableName, maxResults)
        result_set = self.runSelectOne(sql, (who, clkType))
        if (result_set == None):
            return None
        return self.__localTime(result_set['Time'], localTimeFormat)
        

    def getLastUTCTime(self, who, clkType):
        """ Return the last UTC clocking time for the specified clocking type. *who* specifies the user as in :meth:`TblLastClockings.add`.
        This method returns SQL timestamp string.

        .. versionadded:: 1.6
                 
        """
        maxResults = 1
        sql = 'SELECT * FROM %s WHERE EmpID = ? AND Type = ? ORDER BY Time DESC LIMIT %d' % (self.tableName, maxResults)
        result_set = self.runSelectOne(sql, (who, clkType))
        if (result_set == None):
            return None
        return result_set['Time']
        

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

