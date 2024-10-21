# -*- coding: utf-8 -*-
#
# Copyright 2012 Grosvenor Technology
#

import threading
import bioReader
import log
import itg
import time

from applib.utils import crashReport
from applib.bio.bioTemplates import getTblBioTemplatesSyncStatus, getBioHealth

bioLock = None
bioNoSyncCheckBefore   = 0
bioNoSyncCheckMaxDelay = 300
bioLastSanitySynchCheck = 0
bioSanitySyncCheckInterval = 60 * 60

def bioLockInit():
    global bioLock
    bioLock = threading.Lock()

def getBioLock():
    """ Returns the lock object for synchronising access to the reader. """
    return bioLock
    
def bioNoSyncCheckWithinNext(seconds):
    global bioNoSyncCheckBefore
    log.dbg('No sync check within next %d seconds' % seconds)
    bioNoSyncCheckBefore = time.time() + seconds

def bioUpdateLastSanitySyncCheck():
    global bioLastSanitySynchCheck
    bioLastSanitySynchCheck = time.time()

class BioThread(threading.Thread):

    def __init__(self, identifyCb, scanCompleteCb, syncRequestCb, errorCb):
        super(BioThread, self).__init__()
        self.exitEvent = threading.Event()
        self.isRunning = False
        self.identificationInProgress = False
        self.identifyCb     = itg.WeakCb(identifyCb)     if identifyCb else None
        self.scanCompleteCb = itg.WeakCb(scanCompleteCb) if scanCompleteCb else None
        self.syncRequestCb  = itg.WeakCb(syncRequestCb)  if syncRequestCb else None
        self.errorCb        = itg.WeakCb(errorCb)        if errorCb else None

        
    def run(self):
        self.isRunning = True
        numErrors = 0
        log.dbg('Waiting for Biometric to become available')
        with bioLock:
            try:
                bioReader.prepareDB()
            except Exception as e:
                log.err("Biometric database preparation failed: %s" % str(e))
                return
            while (not self.exitEvent.isSet()):
                try:                
                    if (self.identifyCb != None and bioReader.getNumLoadedTemplates() > 0):
                        self.identify()
                    else:
                        self.exitEvent.wait(20)
                    if (self.exitEvent.isSet()):
                        break
                    if (self.syncRequestCb != None):
                        self.check()
                    if (self.exitEvent.isSet()):
                        break
                    # got till here, clear old errors
                    numErrors = 0
                except Exception as e:
                    log.err('Error: %s' % e)
                    numErrors += 1
                    if (numErrors == 1):
                        log.err('Biometric unit error, trying to restart unit!')
                        bioReader.release()
                        time.sleep(2)
                        bioReader.initialise()
                        if (bioReader.isInitialised()):
                            continue
                    log.err('Unrecoverable biometric unit error!')
                    crashReport.createCrashReportFromException()
                    getBioHealth().setLastErrorMsg(str(e), 1)
                    if (not self.errorCb.isDead()):
                        itg.runLater(self.errorCb, (str(e),))
                    break
        self.isRunning = False
        log.dbg('BioThread stopped')

    def stop(self):
        self.exitEvent.set()
        if (self.identificationInProgress):
            try:
                bioReader.cancel()
            except Exception as e:
                log.dbg('Cancel failed: %s' % e)
    
    def execCb(self, cb, params=()):
        if (not cb.isDead()):
            itg.runLater(cb, params)
        self.exitEvent.set()

    def identify(self):
        self.identificationInProgress = True
        cb = self.onScanComplete if self.scanCompleteCb != None else None
        (res, tmplID, _details) = bioReader.identifyUser(cb)
        self.identificationInProgress = False
        if (res == bioReader.SUCCESS):
            userID = getTblBioTemplatesSyncStatus().getUserIDByTemplateID(tmplID)            
            self.execCb(self.identifyCb, (userID,))
        elif (res == bioReader.NO_MATCH):
            self.execCb(self.identifyCb, (None,))
        elif (res == bioReader.CANCELLED):
            pass
        elif (res == bioReader.TIMED_OUT):
            return True
        elif (res == bioReader.LATENT_DETECT):
            pass
        else:
            raise Exception('Unknown result code: %d' % res)
        return False

    def check(self):
        timeDiff = bioNoSyncCheckBefore - time.time()
        if (timeDiff > 0 and timeDiff < bioNoSyncCheckMaxDelay):
            return
        tblSyncStatus = getTblBioTemplatesSyncStatus()
        usersToLoad = tblSyncStatus.getNumberOfUsersToLoad() 
        if (usersToLoad > 0):
            log.dbg('BioSync needed, %d users require synchronisation' % usersToLoad)
            self.execCb(self.syncRequestCb)
            return
        # Do not force sanity check when starting up first time
        if (bioLastSanitySynchCheck == 0):
            bioUpdateLastSanitySyncCheck()
            # but lets do a quick sanity check if sync table thinks we
            # got no users at all (e.g. when bio identify was just enabled),
            # or there are no users loaded in the reader, but we have templates
            # in the database.
            hasMismatch = (usersToLoad==0 and tblSyncStatus.hasNumbersMismatch())
            userCount = tblSyncStatus.getNumberOfUsers()
            loadedCount = bioReader.getNumLoadedTemplates()
            usersToLoad = ((userCount > 0) and (loadedCount == 0))
            if hasMismatch or usersToLoad:
                self.execCb(self.syncRequestCb)
            return
        # Force synchronisation every hour        
        timeDiff = time.time() - bioLastSanitySynchCheck 
        if (timeDiff > 0 and timeDiff < bioSanitySyncCheckInterval):
            return
        log.dbg('Force BioSync...')
        self.execCb(self.syncRequestCb)
        bioUpdateLastSanitySyncCheck()                
            
    def onScanComplete(self, state):
        if (state != bioReader.PROGRESSING_DATA):
            return
        if (not self.scanCompleteCb.isDead()):
            itg.runLater(self.scanCompleteCb)

