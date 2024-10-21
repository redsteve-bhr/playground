# -*- coding: utf-8 -*-
#
# Copyright 2013 Grosvenor Technology
#


from applib.db import database, table
from applib.utils import healthMonitor
import log
import random
import bioReader


_repos  = None
_health = None
_tblSyncStatus = None


def setTemplateRepository(repos, useHealthMonitor=True):
    """ Assign template repository. *repos* is a template repository which must provide
    the following methods:
    
     - addTemplatesChangedListener
     - getTemplates
     - getUserIDsAndTemplateCount
    
    The template repository is normally based on :class:`applib.bio.BioTemplateRepository` which
    implements :meth:`~applib.bio.BioTemplateRepository.addTemplatesChangedListener` and also provides
    :meth:`~applib.bio.BioTemplateRepository.notifyTemplatesModified` and 
    :meth:`~applib.bio.BioTemplateRepository.notifyTemplatesDeleted`.
    
    If *useHealthMonitor* is **True**, the synchronisation status is publish to the
    health monitor. 
    """
    global _repos
    if (repos != None):
        requiredMethods = ('addTemplatesChangedListener',
                           'getTemplates',
                           'getUserIDsAndTemplateCount')
        for m in requiredMethods:
            if (not hasattr(repos, m)):
                raise Exception('Error: template repository must implement "%s"!' % m)
        repos.addTemplatesChangedListener(getTblBioTemplatesSyncStatus().onTemplatesChanged)
        # also create health object
        if (useHealthMonitor):
            global _health
            _health = _BioHealth()
            healthMonitor.getAppHealthMonitor().add(_health)
            
    _repos = repos

def hasTemplateRepository():
    """ Return **True** if a template repository is assigned. """
    return (_repos != None)

def getTemplateRepository():
    """ Return template repository or **None**. """
    return _repos

def getBioHealth():
    return _health

def getTblBioTemplatesSyncStatus():
    global _tblSyncStatus
    if (_tblSyncStatus == None):
        _tblSyncStatus = _TblBioTemplatesSyncStatus()
        _tblSyncStatus.open()
    return _tblSyncStatus



class BioTemplateRepository(object):
    """ Mix-in for implementing template repository. This class implements the 
    adding and notification of listers.
    """

    __listener = []
        
    def addTemplatesChangedListener(self, cb):
        """ Add listener. *cb* is a callback function which takes three
        arguments:
        
         - event as **String** (either "deleted" or "modified")
         - the user ID of the template changed or deleted.
         - number of templates changed (or zero for deletions)
         
        If *event* is "deleted" and the user ID is **None**, all templates
        where removed.
        """
        self.__listener.append(cb)
    
    def notifyTemplatesDeleted(self, uID):
        """ Notify all listeners about deleted templates for user with ID *uID*. 
        If *uID* is **None**, all templates for all users have been deleted. """
        for l in self.__listener:
            l('deleted', uID, 0)
    
    def notifyTemplatesModified(self, uID, numTemplates):
        """ Notify all listeners about changed or new templates for user with ID *uID*. 
        *numTemplates* is a number specifying how many templates a user has. """
        for l in self.__listener:
            l('modified', uID, numTemplates)
    

class _TblBioTemplatesSyncStatus(table.Table):

    columnDefs = { 'RowID'     : 'INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL',
                   'UserID'    : 'TEXT UNIQUE NOT NULL',
                   'TmplID'    : 'INTEGER UNIQUE NOT NULL',
                   'NumTmpls'  : 'INTEGER NOT NULL DEFAULT 0',
                   'Loaded'    : 'INTEGER NOT NULL DEFAULT 0' }
 
    def __init__(self, db=None, tableName='tblBioSyncStatus'):
        if (db == None):
            db = database.getAppDB()        
        super(_TblBioTemplatesSyncStatus, self).__init__(db, tableName)
        
    def onTemplatesChanged(self, event, uID, numTemplates=0):
        if (event == 'deleted'):
            self.__markDeleted(uID)
        else:
            self.__markChanged(uID, numTemplates)

    def __markDeleted(self, uID):
        if (uID == None):
            # all templates got deleted
            sql = 'UPDATE %s SET Loaded = 0, NumTmpls = 0' % self.tableName
            self.runQuery(sql)
        else:
            tID = self.__getTemplateIDByUserID(uID)
            if (tID == None):
                return
            sql = 'INSERT OR REPLACE INTO %s (UserID, TmplID) VALUES (?, ?)' % self.tableName
            self.runQuery(sql, (uID, tID))
    
    def __markChanged(self, uID, numTemplates):
        tID = self.__getTemplateIDByUserID(uID)
        if (tID == None):
            repos = getTemplateRepository()
            if (hasattr(repos, 'getTemplateIDForUser')):
                tID = repos.getTemplateIDForUser(uID)
                if (tID == None):
                    log.err('Failed to acquire template ID for UserID %s' % uID)
                    return
            else:
                tID = self.__getNewTemplateID()
        sql = 'INSERT OR REPLACE INTO %s (UserID, TmplID, NumTmpls) VALUES (?, ?, ?)' % self.tableName
        self.runQuery(sql, (uID, tID, numTemplates))

    def __getTemplateIDByUserID(self, uID):
        sql = 'SELECT TmplID FROM %s WHERE UserID = ?' % self.tableName
        res = self.runSelectOne(sql, (uID,))
        if (res == None):
            return None
        return res[0]
    
    def __getNewTemplateID(self):
        log.dbg('Creating new Template ID')
        for tries in xrange(1, 20):
            tID = random.randint(1, 0x7fffffff)
            uID = self.getUserIDByTemplateID(tID)
            if (uID == None):
                log.dbg('New Template ID is %d (%d tries needed)' % (tID, tries))
                return tID
        raise Exception('Could not create new template ID!')

    # [bioThread] 
    def getUserIDByTemplateID(self, tID):
        """ Return user ID for template ID or None. """
        sql = 'SELECT UserID FROM %s WHERE TmplID = ?' % self.tableName
        res = self.runSelectOne(sql, (tID,))
        if (res == None):
            return None
        return res[0]
        
    def getNumberOfUsersToLoad(self):
        """ Return number of templates to load, update or delete. """
        sql = 'SELECT COUNT(*)  FROM %s WHERE Loaded == 0' % self.tableName
        res = self.runSelectOne(sql)
        return res[0]
    
    def hasNumbersMismatch(self):
        """ Return **True** if number of users in sync table is different from users
        in template repository. Please note that this could take a while depending
        on number of users, etc.
        
        .. versionadded:: 2.2
        
        """
        num1 = self.getNumberOfUsers()
        num2 = len(getTemplateRepository().getUserIDsAndTemplateCount())
        return (num1!=num2)
    
    # [bioInfoDialog]
    def getNumberOfUsers(self):
        """ Returns the number of users with valid templates."""
        sql = 'SELECT COUNT(*)  FROM %s WHERE NumTmpls > 0' % self.tableName
        res = self.runSelectOne(sql)
        return res[0]
    
    def getNumberOfLoadedUsers(self):
        """ Returns the number of users with valid templates which have been loaded."""
        sql = 'SELECT COUNT(*)  FROM %s WHERE NumTmpls > 0 AND Loaded = 1' % self.tableName
        res = self.runSelectOne(sql)
        return res[0]
    
    def reloadAll(self):
        """ This will trigger a re-synchronisation of all templates. """
        sql = 'UPDATE %s SET Loaded = 0' % self.tableName
        self.runQuery(sql)
    
    #
    # [Used by bioSyncDialog ]
    #

    def hasUsersToLoad(self):
        """ Return **True** if there are templates of users to be loaded/synchronised. """
        return (self.getNumberOfUsersToLoad() > 0)
    
    def reload(self, tID):
        """ Trigger re-synchronisation of all templates with that template ID. """
        sql = 'UPDATE %s SET Loaded = 0 WHERE TmplID = ?' % self.tableName
        self.runQuery(sql, (tID,))
    
    def getNextTemplatesToLoad(self, lastTemplateID):
        """ Return next RowID, Template ID and templates for loading. """
        if (lastTemplateID == None):
            sql = 'SELECT RowID, TmplID, UserID FROM %s WHERE Loaded == 0 ORDER BY TmplID LIMIT 1' % self.tableName
            res = self.runSelectOne(sql)
        else:
            sql = 'SELECT RowID, TmplID, UserID FROM %s WHERE Loaded == 0 AND TmplID > ? ORDER BY TmplID LIMIT 1' % self.tableName
            res = self.runSelectOne(sql, (lastTemplateID,))
        if (res == None):
            return (None, None, [])
        return (res['RowID'], res['TmplID'], getTemplateRepository().getTemplates(res['UserID'])) 
        
    def setLoaded(self, rowID):
        """ Mark templates specified by rowID as loaded. """
        sql = 'UPDATE %s SET Loaded = 1 WHERE RowID = ? AND Loaded == 0' % self.tableName
        self.runQuery(sql, (rowID,))
    
    def removeDeleted(self):
        sql = 'DELETE FROM %s WHERE Loaded == 1 AND NumTmpls == 0' % self.tableName
        self.runQuery(sql)

    def getMaxTemplatesPerUser(self):
        templatesPerFinger  = bioReader.getNumTemplatesPerFinger()
        fingersPerUser      = bioReader.getNumFingersPerUser()
        return fingersPerUser * templatesPerFinger

    def getAllTemplateIDsWithCount(self):
        sql = 'SELECT TmplID, NumTmpls FROM %s' % self.tableName
        res = self.runSelectAll(sql)
        maxTemplates = self.getMaxTemplatesPerUser()
        # Put rows into dictionary
        tIDsWithCount = {}
        for row in res:
            tIDsWithCount[ row['TmplID'] ] = min(row['NumTmpls'], maxTemplates)
        return tIDsWithCount

    def getAllUserIDsWithCount(self):
        sql = 'SELECT UserID, NumTmpls FROM %s' % self.tableName
        res = self.runSelectAll(sql)
        # Put rows into dictionary
        tIDsWithCount = {}
        for row in res:
            tIDsWithCount[ row['UserID'] ] = row['NumTmpls']
        return tIDsWithCount

    def syncWithRepository(self):
        reposUserIDs = getTemplateRepository().getUserIDsAndTemplateCount()
        synchUserIDs = self.getAllUserIDsWithCount()
        if (reposUserIDs == synchUserIDs):
            return
        log.warn('Repository not in sync!')
        reposUsers = set(reposUserIDs.keys())
        synchUsers = set(synchUserIDs.keys())
        usersToDelete = synchUsers - reposUsers
        for uID in usersToDelete:
            log.warn('Deleting user %s from sync table' % uID)
            self.__markDeleted(uID)
        usersToAdd = reposUsers - synchUsers
        for uID in usersToAdd:
            log.warn('Adding user %s to sync table' % uID)
            self.__markChanged(uID, reposUserIDs[uID])            
        usersToCheck = reposUsers & synchUsers
        for uID in usersToCheck:
            if (reposUserIDs[uID] != synchUserIDs[uID]):
                log.warn('Updating user %s in sync table' % uID)
                self.__markChanged(uID, reposUserIDs[uID])



class _BioHealth(object):
    
    healthMonitorUpdatePeriod = 20
    totalUsers  = 0
    usersLoaded = 0
    usersToLoad = 0
    numErrors = 0
    lastErrorMsg = ''
    lastSync = 'unknown'
    numWarnings = 0
    lastWarnMsg = ''
    
    def setLastSyncTime(self, lastSync):
        self.lastSync = lastSync
    
    def setLastErrorMsg(self, errMsg, numErrors):
        self.lastErrorMsg = errMsg if (errMsg) else ''
        self.numErrors = numErrors
        
    def setLastWarnMsg(self, warnMsg, numWarnings):
        self.lastWarnMsg = warnMsg if (warnMsg) else ''
        self.numWarnings = numWarnings
        
    def updateStats(self):
        tss = getTblBioTemplatesSyncStatus()    
        self.totalUsers  = tss.getNumberOfUsers()
        self.usersLoaded = tss.getNumberOfLoadedUsers()
        self.usersToLoad = tss.getNumberOfUsersToLoad()
    
    def getWarnings(self):
        warnings = []
        if (self.numErrors != 0):
            warnings.append({ 'msg': _('Biometric synchronisation errors') })
        if (bioReader.isInitialised()):
            self.updateStats()
            if (self.usersToLoad > 0):
                warnings.append({ 'msg': _('Biometric unit not synchronised') })
        return warnings

    def getHealth(self):
        name    = _('Biometric')
        healthy = (self.numErrors == 0 and self.usersToLoad == 0)
        items = [   ('Errors',              self.numErrors),
                    ('Last error',          self.lastErrorMsg),
                    ('Warning',             self.numWarnings),
                    ('Last warning',        self.lastWarnMsg),                    
                    ('Last sync',           self.lastSync),
                    ('Number Users',        self.totalUsers),                    
                    ('Users loaded',        self.usersLoaded),
                    ('Users to load',       self.usersToLoad)]
        return (name, healthy, items)

