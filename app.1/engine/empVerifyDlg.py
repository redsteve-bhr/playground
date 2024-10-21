# -*- coding: utf-8 -*-
#
# Copyright 2013 Grosvenor Technology
#

import itg
import log
import playit
import os
import tempfile

from applib import bio
from applib.gui import msg
from applib.utils import crashReport
from applib.db import tblAppEvents


def _getVerificationMethodClasses():
    return {'none'      : AlwaysPassVerifyDialog,
           'denied'     : AlwaysDenyVerifyDialog,
           'bio'        : BioVerifyDialog,
           'pin'        : PINVerifyDialog,
           'cam'        : CamVerifyDialog,
           'bioNone'    : BioNoneVerifyDialog,
           'voice'      : VoiceVerifyDialog,                           
           'noneIfBadge': NoneIfBadgeVerifyDialog,
           'noneIfBio'  : NoneIfBioVerifyDialog, }

def getVerificationMethods():
    """ Return list of all available verification methods. """
    return _getVerificationMethodClasses().keys()

def getVerificationMethodName(vMethod):
    """ Return translatable name of verification method. """
    vMethodClasses = _getVerificationMethodClasses()
    if (vMethod in vMethodClasses):
        vMethodClass = vMethodClasses[vMethod]
        if (hasattr(vMethodClass, 'getName')):
            return vMethodClass.getName()
    log.warn('Verification method %s has no name!' % (vMethod,))
    return vMethod

def getVerificationMethodDialog(vMethod, emp):
    """ Return verification method dialog. """
    vMethodClasses = _getVerificationMethodClasses()
    if (vMethod in vMethodClasses):
        vMethodClass = vMethodClasses[vMethod]
        return vMethodClass(emp)
    return None

def getVerificationMethodHelp(vMethod):
    """ Return help text for verification method. """
    vClasses = _getVerificationMethodClasses()
    if (vMethod in vClasses and vClasses[vMethod].__doc__):
        doctxt = vClasses[vMethod].__doc__
        return '\n'.join( [ l.strip() for l in doctxt.splitlines() ])
    return 'No help'


class Dialog(itg.PseudoDialog):
    
    def __init__(self, employee):
        super(Dialog, self).__init__()
        self.__emp = employee
            
    def run(self):
        allVerifyMethods = getVerificationMethods()
        self.__verified = False
        self.__wasCancelled = False
        for vMethod in self.__emp.getVerificationMethods():
            if (vMethod not in allVerifyMethods):
                log.warn('Unsupported verification method (%s)' % vMethod)
                continue
            verifyDlg = getVerificationMethodDialog(vMethod, self.__emp)
            if (not verifyDlg.canRun()):
                log.dbg('Verification method "%s" not available for employee' % vMethod)
                continue
            verifyDlg.run()
            self.__verified = verifyDlg.verified()
            self.__wasCancelled = verifyDlg.wasCancelled()
            self.__emp.setUsedVerificationMethod(vMethod)
            if (self.__verified):
                tblAppEvents.addEmployeeEvent(self.__emp.getEmpID(), 'verify.success', '%s|%s' % (self.__emp.getUsedIdentificationMethod(), self.__emp.getUsedVerificationMethod()))
                return itg.ID_OK
            elif (self.__wasCancelled):
                return itg.ID_CANCEL
            log.dbg('Verification (%s) failed' % vMethod)
            tblAppEvents.addEmployeeEvent(self.__emp.getEmpID(), 'verify.failure', self.__emp.getUsedVerificationMethod())
            return itg.ID_OK
        msg.failMsg(_('Access denied, no available verification methods!'))
        
    def verified(self):
        return self.__verified
    
    def wasCancelled(self):
        return self.__wasCancelled
            


class AlwaysPassVerifyDialog(itg.PseudoDialog):
    """ This verification method has no dialogs and
    will always successfully verify a user. It can be used
    to basically "disable" verification and only rely on
    identification.
    """
    
    @staticmethod
    def getName():
        return _('Always pass')

    def __init__(self, employee):
        super(AlwaysPassVerifyDialog, self).__init__()
        
    def canRun(self):
        return True
        
    def verified(self):
        return True

    def run(self):
        return itg.ID_OK
    
    def wasCancelled(self):
        return False


class AlwaysDenyVerifyDialog(itg.PseudoDialog):
    """ This verification method will always deny verification and
    show a dialog with the message "Access denied!". It can be used
    as a means to deny single users access to the system.
    """
    
    @staticmethod
    def getName():
        return _('Always deny')

    def __init__(self, employee):
        super(AlwaysDenyVerifyDialog, self).__init__()
        
    def canRun(self):
        return True
        
    def verified(self):
        return False

    def run(self):
        msg.failMsg(_('Access denied!'))
        return itg.ID_OK

    def wasCancelled(self):
        return False


class NoneIfBadgeVerifyDialog(itg.PseudoDialog):
    """ This method will verify a user successfully
    if identified by a card or badge. The next verification
    method is used, if the user was identified differently.
    """ 
    
    @staticmethod
    def getName():
        return _('Pass if identified by badge')

    def __init__(self, employee):
        super(NoneIfBadgeVerifyDialog, self).__init__()
        self.__emp = employee
        
    def canRun(self):
        if (self.__emp.isIdentifiedByReader()):
            return True
        # skip this verification method if not identified by badge
        return False
        
    def verified(self):
        return True

    def run(self):
        return itg.ID_OK
    
    def wasCancelled(self):
        return False


class NoneIfBioVerifyDialog(itg.PseudoDialog):
    """ This method will verify a user successfully
    if identified by the biometric reader. The next verification
    method is used, if the user was identified differently.
    """
    
    @staticmethod
    def getName():
        return _('Pass if identified by biometric')

    def __init__(self, employee):
        super(NoneIfBioVerifyDialog, self).__init__()
        self.__emp = employee
        
    def canRun(self):
        if (self.__emp.isIdentifiedByBiometric()):
            return True
        # skip this verification method if not identified by badge
        return False
        
    def verified(self):
        return True

    def run(self):
        return itg.ID_OK
    
    def wasCancelled(self):
        return False


class BioVerifyDialog(itg.PseudoDialog):
    """ The biometric reader is used
    to verify a user. This method is skipped if the terminal has
    no biometric reader or if there are no biometric templates
    available for the user.
    """

    @staticmethod
    def getName():
        return _('Biometric')

    def __init__(self, employee, fakeResult=False):
        super(BioVerifyDialog, self).__init__()
        self.__employee = employee
        self.__verified = False
        self.__wasCancelled = False
        self.__fakeResult = fakeResult
        self.__tries = 5 if not fakeResult else None

    def canRun(self):
        if (not hasattr(self.__employee, 'getTemplates')):
            return False
        if (self.__employee.isIdentifiedByBiometric()):
            return False
        if (not bio.employeeCanBeVerified(self.__employee)):
            return False
        return True
    
    def run(self):
        if (bio.employeeCanBeVerified(self.__employee)):
            dlg = bio.BioVerifyDialog(self.__employee, not self.__fakeResult, self.__tries)
            resID = dlg.run()
            if (resID in (itg.ID_CANCEL, itg.ID_TIMEOUT)):
                self.__wasCancelled = True
                return itg.ID_CANCEL
            elif (dlg.verified() or self.__fakeResult):
                # Check for consent
                if not self.__employee.checkConsent():
                    return itg.ID_CANCEL
                self.__verified = True
                return itg.ID_OK
            else:
                return itg.ID_OK
        return itg.ID_CANCEL
         
    def verified(self):
        return self.__verified
 
    def wasCancelled(self):
        return self.__wasCancelled


class BioNoneVerifyDialog(BioVerifyDialog):
    """ Same as *bio*, but always verifies successfully
    once finger has been placed on reader. """

    @staticmethod
    def getName():
        return _('Biometric (always pass)')

    def __init__(self, employee):
        super(BioNoneVerifyDialog, self).__init__(employee, True)


class PINVerifyDialog(itg.Dialog):
    """ This method uses a PIN-entry dialog in order
    to compare an entered PIN with the PIN contained
    in the employee database table loaded from the server.
    
    This method is skipped if the user has no PIN set.
    """ 
    
    @staticmethod
    def getName():
        return _('PIN')

    def __init__(self, employee):
        super(PINVerifyDialog, self).__init__()
        self.__emp = employee
        self.__verified = False
        self.__wasCancelled = True
        
    def onCreate(self):
        super(PINVerifyDialog, self).onCreate()
        view = itg.NumberInputView(_('Please enter PIN'), password=True)
        view.setButton(0, _('OK'), itg.ID_OK, self.__onOK)
        view.setButton(1, _('Cancel'), itg.ID_CANCEL, self.cancel)
        self.addView(view)

    def canRun(self):
        return (self.__emp.getPIN() != None)

    def __onOK(self, btnID):
        self.__wasCancelled = False        
        self.__verified = (self.getView().getValue() == self.__emp.getPIN())
        if (not self.__verified):
            msg.failMsg(_('Wrong PIN!'))
        self.quit(btnID)
        
    def verified(self):
        return self.__verified
    
    def wasCancelled(self):
        return self.__wasCancelled


class CamVerifyDialog(itg.WizardDialog):
    """ This method takes a photo of the user and saves it
    temporarily as part of the user data. An action can access
    the photo when executed and send or save it.
    """

    @staticmethod
    def getName():
        return _('Camera Picture')

    def __init__(self, employee):
        super(CamVerifyDialog, self).__init__()
        self.__emp = employee
        self.__verified = False

    def run(self):
        pages = ( _TakePictureDialog(self.__emp),
                 _ConfirmPictureDialog(self.__emp))
        self._runWizard(pages)
        return self.getResultID()

    def canRun(self):
        return hasattr(itg, 'WebcamView')

    def verified(self):
        return (self.getResultID() == itg.ID_OK)
    
    def wasCancelled(self):
        return (not self.verified())


class _TakePictureDialog(itg.Dialog):    
    
    def __init__(self, employee):
        super(_TakePictureDialog, self).__init__()
        self.__emp = employee
        self.__player = playit.PlayIT()        
    
    def onCreate(self):
        super(_TakePictureDialog, self).onCreate()        
        view = itg.WebcamView()
        view.setTitle(_('Take picture...'))
        view.setButton(0, _('Cancel'), itg.ID_CANCEL, cb=self.cancel)
        view.enableButton(itg.WebcamView.BTN_SNAPSHOT, self.__onPhoto)        
        self.addView(view)

    def skip(self):
        return (self.__emp.getVerifyPhoto() != None)
            
    def onShow(self):
        super(_TakePictureDialog, self).onShow()
        try:
            if (self.__player):
                self.__player.videoCameraShow(*self.getView().getVideoRect())
        except Exception as e:
            crashReport.createCrashReportFromException()
            log.err('Failed to show camera preview: %s' % (e,))

    def onHide(self):
        super(_TakePictureDialog, self).onHide()
        try:
            if (self.__player):     
                self.__player.videoCameraHide()
        except Exception as e:
            crashReport.createCrashReportFromException()
            log.err('Failed to hide camera preview: %s' % (e,))            
        
    def __onPhoto(self):
        filename = '/tmp/verifyPhoto.jpg'        
        if (os.path.exists(filename)):
            os.unlink(filename)
        self.__player.videoCameraSnapshot(filename)
        self.__emp.setVerifyPhoto(open(filename, 'r').read())
        os.unlink(filename)
        self.quit(itg.ID_OK)
    
    
class _ConfirmPictureDialog(itg.Dialog):
    
    def __init__(self, employee):
        super(_ConfirmPictureDialog, self).__init__()
        self.__emp = employee
        view = itg.ImageView(title = _('Use this picture?'))
        view.setButton(0, _('Yes'),     itg.ID_OK,     cb=self.quit)
        view.setButton(1, _('Re-take'), itg.ID_BACK,   cb=self.__onRetake)
        view.setButton(2, _('Cancel'),  itg.ID_CANCEL, cb=self.cancel)
        self.addView(view)

    def onRefreshData(self):
        self.getView().setImage(self.__getPicture(), True)
        
    def __onRetake(self, btnID):
        self.__emp.setVerifyPhoto(None)
        self.__file = None
        self.quit(btnID)
        
    def __getPicture(self):
        try:
            rawData = self.__emp.getVerifyPhoto()
            if (not rawData):
                return None
            self.__file = tempfile.NamedTemporaryFile(suffix='.jpg')
            self.__file.write(rawData)
            self.__file.flush()
            return self.__file.name
        except Exception as e:
            log.err('Error getting profile picture (%s)' % e)
            return None     


class VoiceVerifyDialog(itg.Dialog):
    """ This method takes a voice recording of the user and saves
    it temporarily as part of the user data. An action can access
    the recording when executed and send or save it.
    """
    
    @staticmethod
    def getName():
        return _('Voice')

    def __init__(self, employee):
        super(VoiceVerifyDialog, self).__init__()
        self.__player = playit.PlayIT()
        self.__emp = employee
        self.__verified = False
        self.__wavFile = '/tmp/voiceVerify.wav'
    
    def __del__(self):
        super(VoiceVerifyDialog, self).__del__()
        if (os.path.exists(self.__wavFile)):
            os.unlink(self.__wavFile)
        
    def onCreate(self):
        view = itg.MicrophoneView(_('Please say your name'))
        view.setButton(0, _('OK'), itg.ID_OK, self.__onOK)
        view.setButton(1, _('Cancel'), itg.ID_CANCEL, self.cancel)
        self.addView(view)

    def canRun(self):
        return True

    def onShow(self):
        super(VoiceVerifyDialog, self).onShow()
        try:
            if (self.__player != None):
                self.__player.record(self.__wavFile)
        except Exception as e:
            crashReport.createCrashReportFromException()
            log.err('Failed start recording voice: %s' % (e,))

    def __onOK(self, btnID):
        itg.waitbox(_('Please wait, processing data'), self.__saveData)
        self.quit(btnID)
        
    def __saveData(self):
        if (self.__player != None):
            self.__player.stopRecording()
            self.__player = None
        if (os.path.exists(self.__wavFile)):
            data = open(self.__wavFile, 'r').read()
            self.__emp.setVerifyVoice(data)
            os.unlink(self.__wavFile)
            self.__verified = True
        else:
            self.__verified = False
        
    def verified(self):
        return self.__verified

    def wasCancelled(self):
        return (not self.verified())


class UserPinVerifyDialog(itg.Dialog):
    """ This method uses a PIN-entry dialog in order
    to compare an entered PIN with the PIN set by the user via the
    profile editor.
    
    This method is skipped if the user has no PIN set.
    """ 
      
    @staticmethod
    def getName():
        return _('User PIN')

    def __init__(self, employee):
        super(UserPinVerifyDialog, self).__init__()
        self.__emp = employee
        self.__pin = employee.getUserPin() if hasattr(employee, 'getUserPin') else None
        self.__verified = False
        self.__wasCancelled = True
        
    def onCreate(self):
        super(UserPinVerifyDialog, self).onCreate()          
        view = itg.NumberInputView(_('Please enter PIN'), password=True)
        view.setButton(0, _('OK'), itg.ID_OK, self.__onOK)
        view.setButton(1, _('Cancel'), itg.ID_CANCEL, self.cancel)
        self.addView(view)

    def canRun(self):
        if (not hasattr(self.__emp, 'createUserPin')):
            return None
        return (self.__pin != None)

    def __onOK(self, btnID):
        self.__wasCancelled = False
        hashedPin = self.__emp.createUserPin(self.getView().getValue())
        self.__verified = (hashedPin == self.__pin)
        if (not self.__verified):
            msg.failMsg(_('Wrong PIN!'))
        self.quit(btnID)
        
    def verified(self):
        return self.__verified

    def wasCancelled(self):
        return self.__wasCancelled


def getHelp(appInfo):
    helptxt = \
"""
Identification and verification
===============================

The identification and verification process is automatically executed 
whenever the application goes from one *action* to another requiring
a user to be known (e.g. from the idle menu action to the 
clocking action). 

.. graphviz::

    digraph fig1 {
        size = "2.5";
        compound=true;

        subgraph cluster0 {
            identify -> verify;
            
            identify [label="Identify user"];
            verify [label="Verify user"];
        }

        idle -> identify;
        verify -> clocking;
        idle [label="Action(idle.menu)"];
        clocking [label="Action(clocking)"];
    }

The identification verification process can also be enforced by using the
button option *needEmployee* (see :ref:`button_options`).

.. _identification:

Identification
--------------

There are three identification methods:

 - Card or badge
 - Fingerprint templates via biometric reader
 - Numeric ID via keypad

Some menus have built-in identification (e.g. *idle.menu*), which can be 
configured via swipe actions (see :ref:`swipe_actions`).


Badge code decoding
~~~~~~~~~~~~~~~~~~~

The badge code and optional site code are processed in the following way and order:

 #. Check badge code length  (:ref:`setting_badge_length`).
 #. Extract part of badge code (:ref:`setting_strip_badge`).
 #. Remove leading zeros (:ref:`setting_strip_zeros_from_badge`).
 #. Pad badge code with zeros (:ref:`setting_pad_badge`).
 #. Check site code (:ref:`setting_site_code_check`).

All of the steps above are optional and can be enabled or disabled.


.. _verification:

Verification
------------

How a user is verified depends on the configured verification methods and 
their availability. Every user can have a list of verification methods as part
of their user data. If none are defined, the application falls back to the 
default verification methods found in the application setting :ref:`setting_emp_default_verify_methods`.

The verification methods are specified by their name in a comma separated list 
(e.g. "bio,cam,pin") of which the first available method is used. A method may
not be available for the following reasons:

 - Required hardware component is not present (e.g. no biometric reader for "bio").
 - User does not have necessary data (e.g. no templates enrolled for "bio" or 
   no PIN set for "pin").

.. important::
   A verification method is not skipped if the user fails to verify (e.g. by wrong PIN).

Examples for "bio,pin":

 - "bio" is skipped and "pin" is used, if the user has no biometric templates enrolled but a PIN set.
 - "pin" will not be executed, if the user has biometric templates enrolled but fails biometric verification.
 - The verification process will fail if no verification method is available.
    
The following verification methods exist:

 - %s

""" % '\n - '.join(sorted(getVerificationMethods()))
    helptxt = helptxt.splitlines()
    for vMethod in sorted(getVerificationMethods()):
        vName = getVerificationMethodName(vMethod)
        vHelp = getVerificationMethodHelp(vMethod)
        vSect = '%s (*%s*)' % (vName, vMethod)
        helptxt.append(vSect)
        helptxt.append('~' * len(vSect))
        helptxt.append('')
        helptxt.append(vHelp)
        helptxt.append('')
    return '\n'.join(helptxt)  
