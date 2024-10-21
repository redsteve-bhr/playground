# -*- coding: utf-8 -*-
#
# Copyright 2012 Grosvenor Technology
#
import log
import itg

from applib.bio.bioThread import BioThread
from applib.bio import bioStatus, bioTemplates
from applib.db import tblAppEvents

class BioIdentifyMixin(object):
    """ Mix-in class to enable a dialog to do biometric identification (1:N) 
    and to check whether reader synchronisation is needed. 
    
    Apart from the mandatory methods *onBioIdentify* for identification and
    *onBioSyncRequest* for synchronisation, a dialog may also implement the
    following two methods::
    
        # [...]
    
        def onBioScanComplete(self):
            # Called between scan and fingerprint lookup. 
            itg.tickSound()


        def onBioError(self, errMsg):
            # log error message?
            pass
    """
    
    bioIdentifyEnabled  = False
    bioSyncCheckEnabled = False
    bioIdentifyThread   = None
    
    def bioIdentifyEnable(self):
        """ Enable biometric identification for the dialog using the Mix-in.
        
        The dialog must implement a method called  *onBioIdentify* (see above).
        
        Example::
        
            def onBioIdentify(self, userID):
                pass
        
        .. note::
          Biometric identification must have been enabled by assigning a template
          repository (see :func:`bio.setTemplateRepository`).

        """
        if (bioTemplates.hasTemplateRepository()):
            if (bioStatus.isWorking()):
                self.bioIdentifyEnabled = True
                log.dbg('Enabling biometric identification')
                itg.runLater(self.__startBioWork)
            else:
                log.warn('Cannot enable biometric identification, no working reader')

    def bioSyncCheckEnable(self):
        """ Enable synchronisation check for the dialog using the Mix-in.
        
        The dialog must implement a method called *onBioSyncRequest* (see above).
        
        Example::
        
            def onBioSyncRequest(self):
                # Run biometric synchronisation
                bio.BioSyncDialog().run()
        
        .. note::
          Biometric identification must have been enabled by assigning a template
          repository (see :func:`bio.setTemplateRepository`).

        """
        if (bioTemplates.hasTemplateRepository()):        
            if (bioStatus.isWorking()):
                self.bioSyncCheckEnabled = True                
                log.dbg('Enabling biometric sync check')
                itg.runLater(self.__startBioWork)
            else:
                log.warn('Cannot enable biometric sync check, no working reader')

    def onShow(self):
        super(BioIdentifyMixin, self).onShow()
        if (self.bioIdentifyEnabled or self.bioSyncCheckEnabled):
            itg.runLater(self.__startBioWork)

    def onHide(self):
        super(BioIdentifyMixin, self).onHide()
        self.__stopBioWork()

    def bioIdentifyRestart(self):
        """ Restart biometric identification. Biometric identification and sync-check
        are stopped once a user has been identified or failed to identify. Identification is
        automatically started again when the dialog is shown (again). So if a new dialog
        (e.g. message box) is used on any of the events, then the identification is automatically
        started when the message box dialog is left.
        :meth:`~applib.bio.BioIdentifyMixin.bioIdentifyRestart` can be used, if the identification 
        process should be resumed without re-showing the dialog.
        
        .. versionadded:: 2.3

        """
        if (self.bioIdentifyEnabled or self.bioSyncCheckEnabled):
            itg.runLater(self.__startBioWork)
        
    def __startBioWork(self):
        if (not bioStatus.isWorking()):
            return
        if (not self.isTopDialog()):
            return
        if (not self.bioIdentifyEnabled and not self.bioSyncCheckEnabled):
            return        
        if (self.bioIdentifyThread == None):
            log.dbg('Starting BioWork thread')
            identifyCb = syncRequestCb = scanCompleteCb = None
            if (self.bioIdentifyEnabled):
                identifyCb = self._onBioIdentify
                scanCompleteCb = self._onBioScanComplete if hasattr(self, 'onBioScanComplete') else None
            if (self.bioSyncCheckEnabled):
                syncRequestCb = self._onBioSyncRequest
            errorCb = self._onBioError
            self.bioIdentifyThread = BioThread(identifyCb, scanCompleteCb, syncRequestCb, errorCb)
            self.bioIdentifyThread.start()

    def __stopBioWork(self):
        if (self.bioIdentifyThread != None):
            log.dbg('Stopping BioWork thread')
            self.bioIdentifyThread.stop()
            self.bioIdentifyThread = None

    def onBioIdentify(self, userID):
        raise Exception('onBioIdentify function needs to be overwritten!')
        
    def _onBioIdentify(self, userID):
        if (userID == None):
            tblAppEvents.addBiometricEvent(None, 'bio.identify.failure')
        else:
            tblAppEvents.addBiometricEvent(userID, 'bio.identify.success', employeeIdPrefix='T')
        self.bioIdentifyThread = None        
        if (self.isTopDialog()):
            itg.restartTimeout()
            self.onBioIdentify(userID)

    def onBioSyncRequest(self):
        raise Exception('onBioSyncRequest function needs to be overwritten!')
        
    def _onBioSyncRequest(self):
        self.bioIdentifyThread = None        
        if (self.isTopDialog()):
            itg.restartTimeout()
            self.onBioSyncRequest()

    def _onBioError(self, errMsg):
        self.bioIdentifyThread = None
        if (hasattr(self, 'onBioError') and self.isTopDialog()):
            self.onBioError(errMsg)
    
    def _onBioScanComplete(self):
        if (self.isTopDialog()):
            itg.restartTimeout()
            self.onBioScanComplete()

