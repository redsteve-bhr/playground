# -*- coding: utf-8 -*-
#
# Copyright 2013 Grosvenor Technology
#

"""
:mod:`tblAppEvents` --- Application Event Logging
=================================================

.. versionadded:: 2.4
    
This module provides mechanism for logging application events such as biometric verification errors.
It is not intended for the logging of frequency events as the events are stored in the flash database.

The data fields that can be reported on per event are:

  - **EventID**   : Unique number auto created.
  - **Time**      : Time the event was added (local time).
  - **Employee**  : Reference to the employee where applicable.
  - **Category**  : The event category that can be logged, (bio, employee, system, comms)
  - **Type**      : The type of event e.g. bio.verification as text.
  - **Data**      : Any extra required information.

App events must first be enabled by using :func:`enableAppEvents`.

The following categories are supported and must first be enabled. If not enabled their associated 
'add' functions will just return:

 - **bio**
 - **employee**
 - **system**
 - **comms**


Example::

    # to enable the events specify the type of events 
    # to capture and the maximum number of historic events 
    # to store.
    enableAppEvents(('bio', 'employee'), 1000)
    
    # to setup the csv file handler
    fh = fileHandler.CsvExportFileHandler('tblAppEvents.csv', appEvents.getAppEvents())
    fileHandler.register('^tblAppEvents.csv$', fh)
    
    # to use the event
    addEmployeeEvent(emp.getEmpID(), 'bio.verification', 'biometric error whilst verifying employee')

"""

from applib.utils import crashReport
from applib.db import database, table
import time
import log

_appEvents = None

def enableAppEvents(categories, maxEvents):
    """ Enable the appEvents table. The *categories* is a list of categories to
    log (bio,employee,system,comms). The *maxEvents* is the maximum number of events 
    to hold in the table. If this threshold is reached then the oldest 10% of events
    are automatically removed.
    """
    getAppEvents().setCategories(categories)
    getAppEvents().setMaxEvents(maxEvents)


def addBiometricEvent(employee, evType, data=None, employeeIdPrefix=None):
    """ Add a biometric event for an employee into the event table.
    """
    if (employee):
        employee = (employeeIdPrefix or 'E') + ': ' +  employee
    getAppEvents().addEvent('bio', evType, employee, data)
    
def addEmployeeEvent(employee, evType, data=None, employeeIdPrefix=None):
    """ Add an employee event into the event table.
    """
    if (employee):
        employee = (employeeIdPrefix or 'E') + ': ' + employee
    getAppEvents().addEvent('employee', evType, employee, data)
    
def addSystemEvent(evType, data=None):
    """ Add a system event into the event table. Typical events may be
    application restart etc.
    """
    
    getAppEvents().addEvent('system', evType, None, data)

def addCommunicationEvent(evType, data=None):
    """ Add a comms event into the event table. Care must be taken not to
    add high frequency events.
    """
    getAppEvents().addEvent('comms', evType, None, data)


def getAppEvents():
    global _appEvents
    if (_appEvents == None):
        _appEvents = _TblAppEvents(database.getAppDB())
        _appEvents.open()
    return _appEvents


class _TblAppEvents(table.Table):

    columnDefs = {  'EventID'   : 'INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL',
                    'Time'      : 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL',
                    'Employee'  : 'TEXT',
                    'Category'  : 'TEXT',
                    'Type'      : 'TEXT',
                    'Data'      : 'TEXT' }
 
    def __init__(self, db):
        super(_TblAppEvents, self).__init__(db, "tblAppEvents")
        self.__maxEvents = 0
        self.__numEvents = 0
        self.__categories = []
        
    def open(self):
        super(_TblAppEvents, self).open()
        self.__numEvents = self.count()

    def setMaxEvents(self, maxEvents):
        self.__maxEvents = maxEvents
        
    def setCategories(self, categories):
        self.__categories = categories
        
        
    def addEvent(self, category, evType, employee, data):
        try:
            if (category not in self.__categories):
                return
            log.dbg('EVENT : %s %s %s %s' % (category, evType, employee, data))
            now = time.strftime("%Y-%m-%d %H:%M:%S")
            sql = 'INSERT INTO %s (Time, Category, Employee, Type, Data) VALUES (?,?,?,?,?)' % self.tableName
            self.runQuery(sql, (now, category, employee, evType, data))
            self.__numEvents += 1
            self._checkAndDeleteOldestEvents()
        except Exception as e:
            log.err('Error adding event (%s)' % e)
            crashReport.createCrashReportFromException()

    def _checkAndDeleteOldestEvents(self):
        if (not self.__maxEvents or self.__numEvents <= self.__maxEvents):
            return
        sql = 'SELECT EventID from %s ORDER BY EventID DESC LIMIT 1' % self.tableName
        row = self.runSelectOne(sql)
        if (row == None):
            return
        oldestID = int(row['EventID']) - (self.__maxEvents * 0.9)
        sql = 'DELETE FROM %s WHERE EventID < (?)' % self.tableName
        numberDeleted = self.runQuery(sql, (oldestID,))
        self.__numEvents = self.count()
        log.dbg('appEvents = %s deleted = %s' % (self.__numEvents, numberDeleted))
        


