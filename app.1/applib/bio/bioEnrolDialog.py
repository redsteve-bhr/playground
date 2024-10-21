# -*- coding: utf-8 -*-
#
# Copyright 2012 Grosvenor Technology
#

import itg
import bioReader
import os
import log

from applib.utils import resourceManager
from applib.bio.bioThread import getBioLock
from applib.bio.bioSyncDialog import BioSyncDialog
from applib.bio.bioTemplates import hasTemplateRepository
from applib.bio.bioFinger import BioFinger, getFingerNameByCode
from applib.db import tblAppEvents


class BioEnrolDialog(itg.PseudoDialog):
    """ This dialog and its sub-dialogs can manage a complete
    user enrolment. All it needs is an *employee* object
    that implements the following three methods (see example above):
    
     - setTemplates
     - getTemplates
     - supportsTemplates
    
    *qualityWarnLevel* is a number between 0 and 100 specifying the
    recommended minimum fingerprint quality. If the fingerprint quality
    is below this threshold, a dialog recommending a re-scan will be shown.
    However, it is not mandatory to re-scan and not all biometric readers
    support fingerprint quality.
    
    If *templatePreviewEnabled* is **False** no fingerprint image is shown.
    
    """
    
    def __init__(self, employee, qualityWarnLevel, templatePreviewEnabled=True):
        super(BioEnrolDialog, self).__init__()
        self.__emp = employee
        self.__qualityWarnLevel = qualityWarnLevel
        self.__templatePreviewEnabled = templatePreviewEnabled
        if (not hasattr(employee, 'getTemplates') 
            or not hasattr(employee, 'setTemplates')
            or not hasattr(employee, 'supportsTemplates')):
            raise Exception('Employee object must implement setTemplates, getTemplates and supportsTemplates!')
    
    def run(self):
        if (not bioReader.isInitialised()):
            itg.msgbox(itg.MB_OK, _('Biometric unit not working'))
            return itg.ID_UNKNOWN
        if (not self.__emp.supportsTemplates()):
            itg.msgbox(itg.MB_OK, _('No template ID specified!'))
            return itg.ID_UNKNOWN
        
        if (hasattr(itg, 'BioFingerView') and hasattr(self.__emp, 'setFingers')):
            if (not self.__emp.getFingers() and self.__emp.getTemplates()):
                itg.msgbox(itg.MB_OK, _('No finger information available. Please enroll fingers.'))
            dlg = BioSelectFingerEnrolmentDialog(self.__emp, self.__qualityWarnLevel, self.__templatePreviewEnabled)
        elif (hasattr(itg, 'IconGridView')):
            dlg = BioAdvancedEnrolmentDialog(self.__emp, self.__qualityWarnLevel, self.__templatePreviewEnabled)
        else:
            dlg = BioSimpleEnrolmentDialog(self.__emp, self.__qualityWarnLevel, self.__templatePreviewEnabled)
        return dlg.run()


class BioSimpleEnrolmentDialog(itg.PseudoDialog):
    """ This enrolment dialog is like :class:`bio.BioEnrolDialog` but does not
    use :class:`itg.IconGridView`.
    """
    
    def __init__(self, employee, qualityWarnLevel, templatePreviewEnabled=True):
        super(BioSimpleEnrolmentDialog, self).__init__()
        self.__emp = employee
        self.__qualityWarnLevel = qualityWarnLevel
        self.__templatePreviewEnabled = templatePreviewEnabled
        self.__templateQualities = []
    
    def run(self):
        templatesPerFinger  = bioReader.getNumTemplatesPerFinger()
        fingersPerUser      = bioReader.getNumFingersPerUser()
        maxTemplatesPerUser = fingersPerUser * templatesPerFinger
        templates = []
        while True:
            # Scan first finger 
            dlg = BioScanFingerDialog(self.__qualityWarnLevel, self.__templatePreviewEnabled)
            resID = dlg.run()
            if (resID != itg.ID_OK):
                return resID
            self.__templateQualities.append(dlg.getTemplateQuality())
            templates.extend(dlg.getTemplates())
            #
            # Stop scanning more fingers after we did 10 templates
            if (len(templates) + templatesPerFinger > maxTemplatesPerUser):
                break
            #
            # Another finger?
            fingers = len(templates) / templatesPerFinger
            resID = itg.msgbox(itg.MB_YES_NO_CANCEL, _('%d finger(s) enrolled. Enrol another finger for this user?') % fingers)
            if (resID == itg.ID_NO):
                break
            elif (resID != itg.ID_YES):
                return resID
        # Commit and save data
        tblAppEvents.addBiometricEvent(self.__emp.getEmpID(), 'bio.enrol', '|'.join(['%s' % q for q in self.__templateQualities]) )
        dlg = BioCommitTemplatesDialog(self.__emp, templates)
        dlg.run()
        return itg.ID_OK        


class BioAdvancedEnrolmentDialog(itg.Dialog):
    
    def __init__(self, employee, qualityWarnLevel, templatePreviewEnabled=True):
        super(BioAdvancedEnrolmentDialog, self).__init__()
        self.__qualityWarnLevel = qualityWarnLevel
        self.__templatePreviewEnabled = templatePreviewEnabled
        if (templatePreviewEnabled):
            self.__tmplRemoveIcon = resourceManager.get('applib/icons/template-remove')
            self.__tmplIcon = resourceManager.get('applib/icons/template')
        else:
            self.__tmplRemoveIcon = resourceManager.get('applib/icons/data-remove')
            self.__tmplIcon = resourceManager.get('applib/icons/data')
        self.__emp = employee
        self.__templatesPerFinger  = bioReader.getNumTemplatesPerFinger()
        self.__maxFingersPerUser   = bioReader.getNumFingersPerUser()
        self.__maxTemplatesPerUser = self.__templatesPerFinger * self.__maxFingersPerUser
        self.__templates           = self.__emp.getTemplates()
        self.__templateQualities   = [-1] * (len(self.__templates) / self.__templatesPerFinger)
        if (self.__maxFingersPerUser == 2):
            self.__columns = 2
            self.__rows    = 1
        else:
            self.__columns = 3
            self.__rows = (self.__maxFingersPerUser + self.__columns - 1) / self.__columns
        view = itg.IconGridView(self.__rows, self.__columns, _('Finger template enrolment'))
        fingers = len(self.__templates)/self.__templatesPerFinger
        for i in range(fingers):
            (row, col) = self.__getPos(i)
            if (i<fingers-1):
                view.setIcon(row, col, self.__tmplIcon, None)
            else:
                view.setIcon(row, col, self.__tmplRemoveIcon, None, self.__onRemove, i)
        self.__setButtons(view)
        self.addView(view)
    
    def run(self):
        if (len(self.__templates) == 0):
            self.__onAdd(itg.ID_ADD)
            # if still no templates, don't even bother showing this dialog
            if (len(self.__templates) == 0):
                self.setResultID(itg.ID_BACK)
                return itg.ID_BACK
        super(BioAdvancedEnrolmentDialog, self).run()
        
    def __setButtons(self, view):
        numFingers = len(self.__templates)/self.__templatesPerFinger
        if (numFingers < self.__maxFingersPerUser):
            view.setButton(0, _('Enrol'), itg.ID_ADD, self.__onAdd)
        else:
            view.setButton(0, None, 0)
        if (numFingers > 0):
            view.setButton(1, _('Test'), itg.ID_TEMPLATE, self.__onTest)
        else:
            view.setButton(1, None, 0)            
        if (numFingers > 0):            
            view.setButton(2, _('Save'), itg.ID_OK, self.__onSave)
        else:
            view.setButton(2, None, 0)
        view.setButton(3, _('Cancel'), itg.ID_CANCEL, self.quit)
        
    def __getPos(self, idx):
        row = idx / self.__columns
        col = idx % self.__columns
        return (row, col)
        
    def __onAdd(self, btnID):
        dlg = BioScanFingerDialog(self.__qualityWarnLevel, self.__templatePreviewEnabled)
        resID = dlg.run()
        if (resID != itg.ID_OK):
            return
        self.__templateQualities.append(dlg.getTemplateQuality())
        self.__templates.extend(dlg.getTemplates())
        idx = (len(self.__templates) / self.__templatesPerFinger) - 1
        (row, col) = self.__getPos(idx)
        view = self.getView()
        view.setIcon(row, col, self.__tmplRemoveIcon, None, self.__onRemove, idx)
        if (idx > 0):
            idx -= 1
            (row, col) = self.__getPos(idx)
            view.setIcon(row, col, self.__tmplIcon, None)
        self.__setButtons(view)
    
    def __onTest(self, btnID):
        dlg = BioTestVerifyDialog(self.__templates)
        dlg.run()
    
    def __onRemove(self, fingerIdx):
        listIdx = fingerIdx * self.__templatesPerFinger
        del self.__templates[listIdx:listIdx + self.__templatesPerFinger]
        del self.__templateQualities[-1]
        (row, col) = self.__getPos(fingerIdx)
        view = self.getView()
        view.setIcon(row, col, None, None)
        if (fingerIdx > 0):
            fingerIdx -= 1
            (row, col) = self.__getPos(fingerIdx)
            view = self.getView()
            view.setIcon(row, col, self.__tmplRemoveIcon, None, self.__onRemove, fingerIdx)
        self.__setButtons(view)
 
    
    def __onSave(self, btnID):
        tblAppEvents.addBiometricEvent(self.__emp.getEmpID(), 'bio.enrol', '|'.join(['%s' % q for q in self.__templateQualities]) )
        dlg = BioCommitTemplatesDialog(self.__emp, self.__templates)
        dlg.run()
        self.quit(btnID)
        
    

class BioCommitTemplatesDialog(itg.PseudoDialog):
    
    def __init__(self, emp, templates=None, fingers=None):
        super(BioCommitTemplatesDialog, self).__init__()
        self.__emp = emp
        self.__templates = templates
        self.__fingers = fingers
    
    def run(self):
        (_resID, errMsg) = itg.waitbox(_('Processing data, please wait...'), self.__commitData)
        if (errMsg != None):
            itg.msgbox(itg.MB_OK, errMsg)
            return itg.ID_BACK
        if (hasTemplateRepository()):
            dlg = BioSyncDialog(showWarnings=False, sanityCheck=False)
            res = dlg.run()
            if (res != itg.ID_OK):
                return res
        itg.msgbox(itg.MB_OK, _('User successfully enrolled!'))
        return itg.ID_OK

    def __commitData(self):
        try:
            if (self.__fingers != None):
                self.__emp.setFingers(self.__fingers)
            else:
                self.__emp.setTemplates(self.__templates)
        except Exception as e:
            log.err('Error saving template: %s' % e)
            return 'Error saving template: %s' % e
        return None
    


class BioScanFingerDialog(itg.PseudoDialog):
    
    def __init__(self, qualityWarnLevel, templatePreviewEnabled=True, title=None):
        super(BioScanFingerDialog, self).__init__()
        self.__templates = []
        self.__bioImageFile = '/tmp/bioImage.bmp' if templatePreviewEnabled else None
        self.__templatesPerFinger = bioReader.getNumTemplatesPerFinger()
        self.__qualityWarnLevel = qualityWarnLevel
        self.__templateQuality = -1
        self.__title = title
        
    def getTemplateQuality(self):
        return self.__templateQuality
    
    def run(self):
        while True:
            #
            # scan finger
            if (self.__title == None):
                title = _('Place finger')
            else:
                title = self.__title
            (_resID, (errCode, templates, details)) = itg.bioScanWithProgressManager(title, self.__scan, (), self.__cancel)
            quality = details['quality'] if 'quality' in details else -1
            if (errCode == bioReader.CANCELLED):
                return itg.ID_CANCEL
            elif (errCode == bioReader.TIMED_OUT):
                resID = itg.msgbox(itg.MB_YES_NO, _('No finger detected, cancel enrolment?'))
                if (resID == itg.ID_NO):
                    continue
                return itg.ID_CANCEL
            elif (errCode == bioReader.NO_MATCH):
                resID = itg.msgbox(itg.MB_YES_NO, _('Fingerprints do not match same finger! Try again?'))
                if (resID == itg.ID_YES):
                    continue
                return itg.ID_CANCEL
            elif (errCode == bioReader.LATENT_DETECT):
                resID = itg.msgbox(itg.MB_YES_NO, _('Fingerprint is of insufficient quality! Try again?'))
                if (resID == itg.ID_YES):
                    continue
                return itg.ID_CANCEL
            elif (errCode != bioReader.SUCCESS):
                itg.msgbox(itg.MB_OK, _('Failed to enrol finger: %s') % errCode)
                return itg.ID_UNKNOWN
            #
            # check templates are OK to enrol
            if (bioReader.hasTemplateTest()):
                (_resID, templatesGood) = itg.waitbox(_('Processing templates, please wait...'), bioReader.testTemplates, (templates,))
                if (not templatesGood):
                    log.warn('Template test failed (%s)' % (details,))
                    resID = itg.msgbox(itg.MB_YES_NO, _('Unable to enrol finger! Try again?'))
                    if (resID == itg.ID_YES):
                        continue
                    return itg.ID_CANCEL
            #
            # check quality
            if (quality>0 and quality<self.__qualityWarnLevel):
                params = {'fingerQuality': quality, 'warnLevel': self.__qualityWarnLevel }
                msg = _('Your fingerprint quality of %(fingerQuality)s%% is below the recommended level of %(warnLevel)s%%.')
                itg.msgbox(itg.MB_OK,  msg % params )
            #
            # accept finger
            dlg = BioAcceptFingerDialog(self.__bioImageFile, quality)
            resID = dlg.run()
            if (self.__bioImageFile and os.path.exists(self.__bioImageFile)):
                os.unlink(self.__bioImageFile)
            if (resID == itg.ID_BACK):
                continue # Try again
            elif (resID == itg.ID_OK):
                # accept finger -> save templates
                self.__templates = templates
                self.__templateQuality = quality
            return resID 

    def __scan(self, progressManager):
        self.__progress = 0
        try:
            with getBioLock():
                return bioReader.scanTemplates(self.__templatesPerFinger, self.__bioImageFile, self.__onProgress, (progressManager,))
        except Exception as e:
            return (str(e), [], {})
    
    def __cancel(self, progressManager):
        try:
            bioReader.cancel()
        except Exception as e:
            log.warn('Error cancelling enrolment: %s' % e)

    def __onProgress(self, state, progressManager):
        if (bioReader.hasFingerLiftOffDetect() and state == bioReader.WAITING_FOR_FINGER):
            progressManager.indicatePlaceFinger()
            if (self.__progress > 0):
                progressManager.setTitle(_('Replace finger'))
        elif (state == bioReader.PROGRESSING_DATA):
            if (bioReader.hasFingerLiftOffDetect()):
                progressManager.indicateScanComplete()
                progressManager.setTitle(_('Processing...'))
            self.__progress += 1
            progressManager.setProgress( float(self.__progress) / (self.__templatesPerFinger+1) )
        elif (state == bioReader.WAITING_FOR_FINGER_LIFT_OFF):
            progressManager.indicateLiftFinger()
            progressManager.setTitle(_('Remove finger'))                
            itg.tickSound()
        
    def getTemplates(self):
        return self.__templates


class BioAcceptFingerDialog(itg.Dialog):

    def __init__(self, imgFile, quality):
        self.__imgFile = imgFile
        super(BioAcceptFingerDialog, self).__init__()
        if (imgFile == None):
            view = itg.MsgBoxView()
            if (quality >= 0):
                view.setText(_('Finger template quality is %s%%.') % quality)
            else:
                view.setText(_('Finger template acquired.'))
        else:
            view = itg.BioImageView(imgFile, quality)
        view.setButton(0, _('Accept'), itg.ID_OK, cb=self.quit)
        view.setButton(1, _('Retry'),  itg.ID_BACK, cb=self.quit)
        view.setButton(2, _('Cancel'), itg.ID_CANCEL, cb=self.quit)
        self.addView(view)


class BioTestVerifyDialog(itg.PseudoDialog):
    
    def __init__(self, templates):
        super(BioTestVerifyDialog, self).__init__()
        self.__templates = templates
    
    def run(self):
        (_resID, res) = itg.bioScanWithProgressManager(_('Verify...'), self.__verify, (), self.__cancel, False)
        if (res == bioReader.SUCCESS):
            itg.successSound()
            itg.msgbox(itg.MB_OK, _('User verified successfully!'))
        elif (res == bioReader.NO_MATCH or res == bioReader.LATENT_DETECT):
            itg.failureSound()
            itg.msgbox(itg.MB_OK, _('User could not be verified!'))
        elif (res == bioReader.TIMED_OUT or res == bioReader.CANCELLED):
            pass
        else:
            itg.failureSound()
            itg.msgbox(itg.MB_OK, _('Error verifying! (%s)' % res))
        return itg.ID_OK
        
    def __verify(self, progressManager):
        with getBioLock():
            try:
                if (not self.__templates):
                    return bioReader.NO_MATCH
                (res, _details) = bioReader.verifyUser(self.__templates, self.__scanComplete, (progressManager,))
                return res
            except Exception as e:
                return str(e)
    
    def __scanComplete(self, state, progressManager):
        if (state == bioReader.PROGRESSING_DATA):
            itg.tickSound()
            progressManager.indicateScanComplete()
        
    def __cancel(self, *args):
        try:
            bioReader.cancel()
        except Exception as e:
            log.err('Error cancelling bioScan: %s' % e)


        
class BioSelectFingerEnrolmentDialog(itg.Dialog):
    
    def __init__(self, employee, qualityWarnLevel, templatePreviewEnabled=True):
        super(BioSelectFingerEnrolmentDialog, self).__init__()
        self.__qualityWarnLevel = qualityWarnLevel
        self.__templatePreviewEnabled = templatePreviewEnabled
        self.__emp = employee
        self.__fingers = self.__emp.getFingers()
        view = itg.BioFingerView(_('Please select finger'), readOnly=False)
        view.setSelectedCb(self.__onFingerSelected)
        self.__updateView(view)
        self.addView(view)

    def __updateView(self, view):
        numFingers = len(self.__fingers)
        if (numFingers > 0):
            view.setButton(1, _('Test'), itg.ID_TEMPLATE, self.__onTest)
        else:
            view.setButton(1, None, 0)            
        view.setButton(2, _('Save'), itg.ID_OK, self.__onSave)
        view.setButton(3, _('Cancel'), itg.ID_CANCEL, self.quit)
        selectedFingers = [ finger.getFingerCode() for finger in self.__fingers ]
        view.setSelectedFingers(selectedFingers)
    
    def __onTest(self, btnID):
        templates = []
        for finger in self.__fingers:
            templates.extend(finger.getTemplates())
        dlg = BioTestVerifyDialog(templates)
        dlg.run()
    
    def __onSave(self, btnID):
        qualities = '|'.join(['%s' % finger.getQuality() for finger in self.__fingers])
        tblAppEvents.addBiometricEvent(self.__emp.getEmpID(), 'bio.enrol', qualities)
        dlg = BioCommitTemplatesDialog(self.__emp, fingers=self.__fingers)
        resID = dlg.run()
        if (resID == itg.ID_OK):
            self.quit(btnID)
        
    def __onFingerSelected(self, fingerCode):
        for idx, finger in enumerate(self.__fingers):
            if (fingerCode == finger.getFingerCode()):
                dlg = _AskDeleteReEnrolFinger(fingerCode)
                res = dlg.run()
                if (res == itg.ID_DELETE):
                    del self.__fingers[idx]
                    self.__updateView(self.getView())
                    return
                elif (res == itg.ID_TEMPLATE):
                    # Re-enrol, so delete existing
                    del self.__fingers[idx]
                    break
                else:
                    return
        # check if we allow another finger
        maxFingers = bioReader.getNumFingersPerUser()
        if (len(self.__fingers) >= maxFingers):
            itg.msgbox(itg.MB_OK, _('You cannot enrol more fingers! Please delete one first.'))
        else:
            # must be enrolling new finger or re-enrolling an existing finger
            self.__enrolFinger(fingerCode)

    def __enrolFinger(self, fingerCode):
        title =  _('Place finger (%s)' % getFingerNameByCode(fingerCode))
        dlg = BioScanFingerDialog(self.__qualityWarnLevel, self.__templatePreviewEnabled, title=title)
        resID = dlg.run()
        if (resID == itg.ID_OK):
            # save the template in the list
            finger = BioFinger(fingerCode, dlg.getTemplates(), dlg.getTemplateQuality())
            self.__fingers.append(finger)
        self.__updateView(self.getView())
    
 
class _AskDeleteReEnrolFinger(itg.Dialog):

    def __init__(self, fingerCode):
        super(_AskDeleteReEnrolFinger, self).__init__()
        view = itg.MsgBoxView()
        view.setText(_('Your "%s" finger is already enrolled.\nDelete or re-enrol the finger?' % getFingerNameByCode(fingerCode)))
        view.setButton(1, _('Re-Enrol'), itg.ID_TEMPLATE, self.quit)
        view.setButton(2, _('Delete'), itg.ID_DELETE, self.quit)
        view.setButton(3, _('Back'), itg.ID_BACK, self.back)
        self.addView(view)
    
    


    
    
