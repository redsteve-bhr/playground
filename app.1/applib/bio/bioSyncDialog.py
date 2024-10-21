# -*- coding: utf-8 -*-
#
# Copyright 2012 Grosvenor Technology
#

import threading
import itg
import log
import bioReader
import datetime
import time

from applib.utils import restartManager
from applib.bio.bioThread import bioNoSyncCheckWithinNext
from applib.bio.bioTemplates import getTblBioTemplatesSyncStatus, getBioHealth


class _BioSyncThread(threading.Thread):
    
    def __init__(self, dlg, sanityCheck):
        super(_BioSyncThread, self).__init__()
        self.__templatesPerFinger = bioReader.getNumTemplatesPerFinger()
        self.__sanityCheck = sanityCheck
        self.__dlg = dlg
        self.__event = threading.Event()
        self.__warnings = []
        self.__maxWarnings = 20
    
    def run(self):
        # Get dialog and remove it from instance so to not
        # have a circular reference.
        dlg = self.__dlg
        del self.__dlg
        
        errMsg = None
        errCounter = 0
        self.__warnCounter = 0
        tblSyncStatus = getTblBioTemplatesSyncStatus()
        try:
            log.dbg('Preparing fingerprint DB...')
            bioReader.prepareDB()
            for _tries in range(2):
                if (self.__event.isSet()):
                    break
                if (self.__tooManyWarnings()):
                    log.warn('Synchronisation stopped after too many warnings.')
                    for i, w in enumerate(self.__warnings):
                        log.warn('WARN %02d: %s' % (i+1, w))
                    break
                self.__handleUnloadedTemplates(tblSyncStatus, dlg)
                if (self.__event.isSet()):
                    break
                self.__doSanityCheck(tblSyncStatus)
                if (not tblSyncStatus.hasUsersToLoad()):
                    break
        except Exception as e:
            errMsg = _('Synchronisation failed: %s') % e
            errCounter += 1
            log.err(errMsg)
        if (not self.__event.isSet()):
            itg.runLater(dlg.onResult, (errMsg,self.__warnings))
        bh = getBioHealth()
        if (bh != None):
            bh.setLastSyncTime(str(datetime.datetime.today()))
            bh.setLastErrorMsg(errMsg, errCounter)
            if (self.__warnings):
                bh.setLastWarnMsg(self.__warnings[-1], len(self.__warnings))
            else:
                bh.setLastWarnMsg('', 0)
            bh.updateStats()

    def __tooManyWarnings(self):
        # Stop if we have more than the max allowed number of warnings
        if (len(self.__warnings) >= self.__maxWarnings):
            return True
        # Also stop if we got the same warning twice
        if (len(self.__warnings) >= 2 and self.__warnings[-1] == self.__warnings[-2]):
            return True
        return False
    
    def __handleUnloadedTemplates(self, tblSyncStatus, dlg):
        log.dbg('Handling unloaded templates')
        templID   = None
        errMsg    = None
        total     = 0
        unloaded  = 0
        readerIDs = None
        startTime = time.time()
        usersHandledCounter = 0        
        while not self.__event.isSet():
            total    = tblSyncStatus.count()
            unloaded = tblSyncStatus.getNumberOfUsersToLoad()
            # If all templates need loading (or not template at all),
            # delete all templates from reader.
            if (total == unloaded):
                self.__deleteAll()
                readerIDs = {}
            # Leave if total or unloaded number of templates is zero, 
            # nothing to do anyway and the progressbar would fail. 
            if (total == 0 or unloaded == 0):
                break
            # If readerIDs has not been set yet, do it now. readerIDs
            # is useful to decide whether deleting templates is actually
            # needed.
            if (readerIDs == None):
                readerIDs = self.__getAllReaderIDs()
            itg.runLater(dlg.onProgressUpdate, (1.0-float(unloaded)/total,))
            # Get next template to load or return if there aren't any.
            (rowID, templID, templates) = tblSyncStatus.getNextTemplatesToLoad(templID)
            if (templID == None):
                break
            # Load next template to reader, ignore errors
            try:
                with restartManager.PreventRestartLock():
                    res = self.__loadTemplates(tblSyncStatus, readerIDs, rowID, templID, templates)
                    usersHandledCounter += res
            except Exception as e:
                errMsg = 'Error loading template %s: %s' % (templID, e)
                log.err(errMsg)
                # Something went wrong while loading a template, try next 
                # template anyway...
        if (errMsg):
            raise Exception(errMsg)
        if (not self.__event.isSet()):
            tblSyncStatus.removeDeleted()
        totalTime = time.time() - startTime
        if (usersHandledCounter > 0):
            log.dbg('Handled %d users in %.2f seconds (%.2f seconds per user)' % (usersHandledCounter, totalTime, totalTime/usersHandledCounter))

        
    def __doSanityCheck(self, tblSyncStatus):
        if (not self.__sanityCheck):
            return
        # Do not do sanity check if there are templates not loaded yet
        if (tblSyncStatus.hasUsersToLoad()):
            return
        log.dbg('Executing sanity check...')
        startTime = time.time()
        log.dbg('Checking repository is in sync')
        tblSyncStatus.syncWithRepository()
        tmplInReader = self.__getAllReaderIDs()
        tmplInDB     = tblSyncStatus.getAllTemplateIDsWithCount()
        if (tmplInReader == tmplInDB):
            log.dbg('Sanity check done, everything looks fine (check took %.2f seconds)' % (time.time() - startTime))
            return
        tmplIDsInReader = set(tmplInReader.keys())
        tmplIDsInDB     = set(tmplInDB.keys())
        log.warn('Template mismatch detected')
        tmplsToDelete = tmplIDsInReader - tmplIDsInDB
        for tID in tmplsToDelete:
            if (self.__event.isSet()):
                break
            log.dbg('Deleting template for ID %s' % tID)
            bioReader.deleteTemplates(tID)
        tmplsToAdd = tmplIDsInDB - tmplIDsInReader
        # only mark templates to reload if there are any marked loaded
        if (len(tmplsToAdd) > 0 and tblSyncStatus.getNumberOfLoadedUsers() > 0):
            for tID in tmplsToAdd:
                if (self.__event.isSet()):
                    break
                log.dbg('Marking template for ID %s for reload (needs to be added)' % tID)
                tblSyncStatus.reload(tID)
        tmplsToCheck = tmplIDsInDB & tmplIDsInReader
        for tID in tmplsToCheck:
            if (self.__event.isSet()):
                break
            if (tmplInReader[tID] == tmplInDB[tID]):
                continue
            log.dbg('Marking template for ID %s for reload' % tID)
            tblSyncStatus.reload(tID)
        log.dbg('Sanity check done (check took %.2f seconds)' % (time.time() - startTime))            
        
    def stop(self):
        self.__event.set()
        self.join()
        
    def __getAllReaderIDs(self):
        return bioReader.getAllUserInfo()
    
    def __deleteAll(self):
        log.dbg('Deleting all templates')
        bioReader.deleteAllTemplates()
        bioReader.prepareDB()
        
    def __loadTemplates(self, tblSyncStatus, readerIDs, rowID, tID, templates): 
        # Check for correct number of templates.
        if ((len(templates) % self.__templatesPerFinger) != 0):
            self.__warnings.append('Incomplete number of templates for user %s, trying later...' % tID)
            log.dbg(self.__warnings[-1])
            return 0
        if (tID in readerIDs):
            log.dbg('Deleting template with ID %s' % tID)
            bioReader.deleteTemplates(tID, False)
            del readerIDs[tID]
        if (len(templates) > 0):
            log.dbg('Adding %d templates for ID %s' % (len(templates), tID)        )
            bioReader.addTemplates(tID, templates)
            readerIDs[tID] = len(templates)
        log.dbg('Marking templates with ID %s as loaded' % tID)
        tblSyncStatus.setLoaded(rowID)
        return 1
        

class BioSyncDialog(itg.Dialog):
    """ Biometric template synchronisation dialog.
    
    This dialog shows a progress bar while synchronising biometric
    templates from the terminal to the biometric reader.
    
    A message box with errors and warnings is shown at the end
    of the synchronisation, if *showWarnings* is **True**. This can be useful
    when synchronising within the application setup, which is likely to be
    supervised.
    
    The sanity check can be disabled by setting *sanityCheck* to **False**. 
    This might be useful when using :class:`BioSyncDialog` directly after
    an enrolment as the sanity check may take a couple of seconds but is not
    strictly needed.
    
    """
    
    def __init__(self, showWarnings=False, sanityCheck=True):
        super(BioSyncDialog, self).__init__()
        view = itg.ProgressView(_('Updating finger templates...'))
        view.setButton(0, _('Finish later'), itg.ID_NEXT, self.__cancel)
        self.disableTimeout()
        self.addView(view)
        self.__standAlone = showWarnings
        self.__thread = _BioSyncThread(self, sanityCheck)

    def onShow(self):
        super(BioSyncDialog, self).onShow()
        if (self.__thread):
            self.__thread.start()
    
    def __cancel(self, btnID):
        self.getView().setText(_('Please wait...'))
        self.__thread.stop()
        self.__thread = None
        bioNoSyncCheckWithinNext(120)
        self.quit(btnID)
        
    def onProgressUpdate(self, progress):
        self.getView().setFraction(progress)
    
    def onResult(self, errMsg, warnings):
        self.__thread = None        
        if (errMsg):
            bioNoSyncCheckWithinNext(120)
            itg.msgbox(itg.MB_OK, errMsg, timeout=10)
            self.quit(itg.ID_CANCEL)
        elif (self.__standAlone and warnings):
            itg.msgbox(itg.MB_OK, _('Synchronisation finished with %d warnings.' % len(warnings)))
            self.quit(itg.ID_CANCEL)
        else:
            bioNoSyncCheckWithinNext(60)
            self.quit(itg.ID_OK)


        