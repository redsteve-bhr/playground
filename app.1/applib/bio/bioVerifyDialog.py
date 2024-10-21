# -*- coding: utf-8 -*-
#
# Copyright 2012 Grosvenor Technology
#

import itg
import bioReader
import led
import log
import time
import playit
import os

from applib.gui import msg
from applib.bio.bioThread import getBioLock
from applib.db import tblAppEvents


def employeeCanBeVerified(emp):
    """ Returns **True** if the following preconditions are fulfilled:
    
     - Working biometric reader.
     - Employee supports templates.
     - Employee has templates.
     
    """
    if (not bioReader.isInitialised()):
        log.dbg('Biometric unit not available for verification')
        return False
    if (not hasattr(emp, 'supportsTemplates') or not emp.supportsTemplates()):
        log.dbg('User does not support biometric verification!')
        return False
    templates = emp.getTemplates()
    if (not templates):
        log.dbg('No templates available for verification')
        return False
    return True
        


class BioVerifyDialog(itg.PseudoDialog):
    """ This dialog implements biometric verification of a user/employee.
    All it needs is an *employee* object that implements the following 
    two methods (see example above):
    
     - getTemplates
     - supportsTemplates
    
    .. versionchanged:: 2.2
        Optional parameter *showFailMsg* added. When set to **False** fail message is 
        suppressed when verification fails.
        
    .. versionchanged:: 2.3
        Optional parameter *tries* added. When set to a number greater than 0, the dialog
        attempts to try verifying after a failure until *tries* attempts. For this, the 
        failure indication is shown as part of the dialog.
    
    .. versionchanged:: 2.4
        Optional parameter *retrySound* added. The WAV file specified by *retrySound*
        is played when a user failed to verify but can try again. The buzzer will be used
        if set to **None** .
    

    :meth:`~applib.bio.BioVerifyDialog.verified` can be called to see 
    whether the user verified successfully. The dialog returns **itg.ID_CANCEL**
    if the cancel button was pressed or no finger was detected within timeout.
    
    """
    
    def __init__(self, employee, showFailMsg=True, tries=None, retrySound=None):
        super(BioVerifyDialog, self).__init__()
        self.title = _('Verify...')
        self.__verified = False
        self.__emp = employee
        self.__showFailMsg = showFailMsg
        self.__triesLeft = tries
        self.__triesUsed = 0 # counting failed attempts
        self.__retrySound = retrySound
        self.__running = True
        if (not hasattr(employee, 'getTemplates') 
            or not hasattr(employee, 'supportsTemplates')):
            raise Exception('Employee object must implement getTemplates and supportTemplates!')

    def verified(self):
        """ Returns **True** if user verified successfully. """
        return self.__verified

    def run(self):
        self.setResultID(itg.ID_OK)
        if (not bioReader.isInitialised()):
            itg.msgbox(itg.MB_OK, _('Biometric unit not working'))
            return self.getResultID()
        if (not self.__emp.supportsTemplates()):
            itg.failureSound()
            itg.msgbox(itg.MB_OK, _('User does not support biometric verification!'))
            return self.getResultID()
        templates = self.__emp.getTemplates()
        if (not templates):
            itg.failureSound()
            itg.msgbox(itg.MB_OK, _('No biometric data available to verify user!'))
            return self.getResultID()
        while True:
            if (hasattr(self.__emp, 'hasTemplateInfo') and hasattr(itg, 'BioFingerView') and self.__emp.hasTemplateInfo()):
                buttons = ( (itg.ID_HELP, _('Help')), (itg.ID_CANCEL, _('Cancel')) )
                (resID, res) = itg.bioScanWithProgressManager(self.title, self.__verify, (templates,), self.__cancel, False, buttons)
            else:
                (resID, res) = itg.bioScanWithProgressManager(self.title, self.__verify, (templates,), self.__cancel, False)
            if (resID == itg.ID_HELP):
                BioShowEnrolledDialog(self.__emp).run()
                continue
            elif (res == bioReader.SUCCESS):
                self.__verified = True
                tblAppEvents.addBiometricEvent(self.__emp.getEmpID(), 'bio.verify.success', '%d' % self.__triesUsed)
            elif (res == bioReader.NO_MATCH or res == bioReader.LATENT_DETECT):
                tblAppEvents.addBiometricEvent(self.__emp.getEmpID(), 'bio.verify.failure', '%d' % self.__triesUsed)
                if self.__showFailMsg:
                    msg.failMsg(_('User could not be verified!'))
            elif (res == bioReader.TIMED_OUT or res == bioReader.CANCELLED):
                self.setResultID(itg.ID_CANCEL)
            else:
                itg.failureSound()
                itg.msgbox(itg.MB_OK, _('Error verifying! (%s)' % res))
            return self.getResultID()            

    def __verify(self, progressManager, templates):
        self.__running = True        
        with getBioLock():
            try:
                while self.__running:
                    (res, _details) = bioReader.verifyUser(templates, self.__scanComplete, (progressManager,))
                    if (res in (bioReader.NO_MATCH, bioReader.LATENT_DETECT)):
                        # Failed to verify
                        self.__triesUsed += 1
                        # Handle multiple tries, if supported
                        if (self.__triesLeft and self.__triesLeft>1 and hasattr(progressManager, 'indicateFailure')):
                            self.__triesLeft -= 1
                            led.on(led.LED_ALL | led.LED_STATUS, led.RED, 2*1000)
                            if (self.__retrySound and os.path.exists(self.__retrySound)):
                                p = playit.PlayIT()
                                p.play(self.__retrySound)
                            else:
                                itg.failureSound()
                            progressManager.indicateFailure()
                            progressManager.setTitle(_('User could not be verified!'))
                            time.sleep(1)
                            progressManager.clearIndicator()
                            progressManager.setTitle(self.title)
                            continue
                    return res
                return bioReader.CANCELLED
            except Exception as e:
                log.err('Error in verify: %s' % e)
                return str(e)

    def __scanComplete(self, state, progressManager):
        if (state != bioReader.PROGRESSING_DATA):
            return
        itg.tickSound()
        progressManager.indicateScanComplete()
        
    def __cancel(self, *args):
        try:
            self.__running = False
            bioReader.cancel()
        except Exception as e:
            log.err('Error cancelling bioScan: %s' % e)


class BioShowEnrolledDialog(itg.Dialog):
    
    def __init__(self, employee):
        super(BioShowEnrolledDialog, self).__init__()
        selectedFingers = [ finger.getFingerCode() for finger in employee.getFingers() ]
        view = itg.BioFingerView(_('Enrolled fingers...'), readOnly=True)
        view.setButton(0, _('OK'), itg.ID_OK, self.quit)
        view.setSelectedFingers(selectedFingers)        
        self.addView(view)


