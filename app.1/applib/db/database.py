# -*- coding: utf-8 -*-
#
# Copyright 2010 Grosvenor Technology
#

from sqlite3 import dbapi2 as sqlite3
import log
import weakref
import os
import threading
import appit

from applib.utils.usbAccess import USBAccess, NoWorkingUSBDeviceFoundException #@UnusedImport

_appDB = None
_usbDBs = {}
_persistentUsbDBs = {}

def getAppDB():
    """ Get the application's database object. The first time this is 
        called the database will be automatically opened.
    """
    global _appDB
    if (_appDB == None):
        appInfo = appit.AppInfo()
        _appDB = Database(appInfo.name() + '.db')   
    return _appDB


_appMemDB = None

def getAppMemDB():
    """ Get the application's MEMORY database object. The first time this is 
        called the database will be automatically opened. The content of a 
        memory database will be lost on application exit.
    """
    global _appMemDB
    if (_appMemDB == None):
        _appMemDB = Database(':memory:')   
    return _appMemDB
        

def getUsbDB(path=None, databaseName=None, keep=False):
    """ Get USB database. The database will be created, if it does not yet 
    exist. The first working USB device will be used. 
    
    *path* is a relative path for the USB device. If **None** it defaults to
    'IT-Databases/APPLICATION_NAME/'. 
    
    *databaseName* is a string specifying the database filename. If *databaseName*
    is **None** 'APPLICATION_NAME.db' will be used.
    
    .. versionadded:: 1.2
        
    """
    appInfo = appit.AppInfo()
    if (path == None):
        path = os.path.join('IT-Databases', appInfo.name())
    if (databaseName == None):
        databaseName = appInfo.name() + '.db'
    dbPath = os.path.join(path ,databaseName)
    usbDB = _usbDBs[dbPath]() if dbPath in _usbDBs else None
    if (usbDB == None):
        usbDB = USBDatabase(dbPath)
        _usbDBs[dbPath] = weakref.ref(usbDB)
    if (keep and dbPath not in _persistentUsbDBs):
        if (len(_persistentUsbDBs) == 0):
            from applib.utils import restartManager
            restartManager.registerCleanup(closeUsbDBs)
        _persistentUsbDBs[dbPath] = usbDB
    return usbDB
 
def closeUsbDBs():
    log.dbg('Closing all persistent USB databases (%d in total)' % (len(_persistentUsbDBs)))
    _persistentUsbDBs.clear()
 
 
class Database(object):
    """Create database object.
    
    The database will be placed in '/mnt/user/db/' unless *name* is 
    an absolute filename. The directory for the database will be
    automatically created. The database filename specified by *name*
    normally ends in ".db" (e.g. "mydb.db").
    
    .. note::
        If *name* is ':memory:' a temporary memory based database will
        be created.
    
    In most cases the functions :func:`~applib.db.database.getAppDB`, 
    :func:`~applib.db.database.getAppMemDB` or :func:`~applib.db.database.getUsbDB` 
    should be used to acquire a database handle.
    
    """
    
    #-----------------------------------------------------------------------
    def __init__(self, name):
        """ Init."""
        self.lock    = threading.RLock()
        self.is_open = False
        self.dbconn  = None
        self.dbcursor= None

        if (name == ":memory"):
            log.err("Wrong memory database name!!!")
            self.dbname = ":memory:"
        elif (name == ":memory:"):
            self.dbname = name
        else:
            if (os.path.isabs(name)):
                self.dbname = name
            else:
                self.dbname = os.path.join("/mnt/user/db/", name)

            path = os.path.dirname(self.dbname)
            if (not os.path.exists(path)):
                os.makedirs(path)

    def isMemoryDB(self):
        """ Return **True** if this database is a memory database. 
        
        .. versionadded:: 2.2
        
        """
        return (self.dbname == ':memory:')
    
    def delete(self):
        """Delete database from file system"""
        with self.lock:
            if (self.isOpen()):
                self.close()
            try:
                if (self.dbname != ":memory:"):
                    os.remove(self.dbname)
            except:
                log.dbg("Database does not exist")

    def open(self):
        """Open the database, create if necessary"""
        log.dbg('Open database (%s)' % self.dbname)
        self.dbconn = sqlite3.connect(self.dbname, check_same_thread=False)
        self.dbconn.row_factory = sqlite3.Row
        self.dbcursor = self.dbconn.cursor()
        self.dbcursor.execute('PRAGMA foreign_keys = ON;')
        self.is_open = True
    
    def close(self):
        """Close database connection"""
        log.dbg("Close database")
        if (self.dbconn != None):
            self.dbconn.close()
        self.is_open = False

    def isOpen(self):
        """Return True if database is open"""
        return self.is_open

    def tableExists(self, tableName):
        """Return True if table exists.
        
        .. versionadded:: 2.0
                
        """
        sql = "SELECT tbl_name FROM sqlite_master WHERE tbl_name = ?"
        with self.lock:
            try:
                self.dbcursor.execute(sql, (tableName,) )
                result_set = self.dbcursor.fetchone()
            except:
                result_set = None
        if (result_set == None):
            return False
        return True
    
    def dropTable(self, tableName):
        """Delete table from database.
        
        .. versionadded:: 2.0        
        
        """
        # delete the table
        log.dbg("Dropping table %s" % tableName)
        sql = "DROP TABLE IF EXISTS %s" % tableName
        log.sql(sql)
        with self.lock:
            self.dbcursor.execute(sql)
            self.dbconn.commit()


class USBDatabase(Database):
    
    def __init__(self, dbPath):
        self._usbAccessObject = USBAccess()
        fullPath = os.path.join(self._usbAccessObject.getPath(), dbPath)
        super(USBDatabase, self).__init__(fullPath)

    def __del__(self):
        if (hasattr(self, 'dbconn')):
            self.close()



