# -*- coding: utf-8 -*-
#
# Copyright 2013 Grosvenor Technology
#
 
import itg
import log
import os
import playit
import updateit
from engine import dynButtons
 
from applib.utils import crashReport
 
class ProfilePhotoDialog(itg.Dialog):
     
    def __init__(self, emp):
        self.__emp = emp
        super(ProfilePhotoDialog, self).__init__()
        if (hasattr(emp, 'getProfilePicture')):
            view = itg.DetailsGridMenuView(_('Profile Photo'), emp.getProfilePicture())
            if (hasattr(emp, 'setProfilePicture')):
                view.setButton(0, _('Change'), 0, self.__onChange)
            if (hasattr(emp, 'deleteProfilePicture')):
                view.setButton(3, _('Delete'), 3, self.__onDelete)
            view.setButton(5, _('Back'), itg.ID_BACK, self.back)
        else:            
            view = itg.MsgBoxView()
            view.setText(_('Profile pictures are not supported.'))
            view.setButton(0, _('OK'), itg.ID_OK, self.quit)
        self.addView(view)
        
    def __onChange(self, btnID):
        dlg = dynButtons.getActionDialogByName('profile.picture.take', employee=self.__emp)
        resID = dlg.run()
        if (resID == itg.ID_OK or resID == itg.ID_YES):
            self.getView().setPicture(self.__emp.getProfilePicture())
    
    def __onDelete(self, btnID):
        dlg = dynButtons.getActionDialogByName('profile.picture.delete', employee=self.__emp)
        resID = dlg.run()
        if (resID == itg.ID_OK or resID == itg.ID_YES):
            self.getView().setPicture(self.__emp.getProfilePicture())
    

class ViewPictureDialog(itg.Dialog):
 
    def __init__(self, emp):
        super(ViewPictureDialog, self).__init__()
        if (hasattr(emp, 'getProfilePicture')):
            profilePic = emp.getProfilePicture()
            if (profilePic != None):
                if (updateit.get_type() != 'IT5100'):
                    view = itg.MsgBoxView()
                    view.setText(_('Viewing the profile picture is not supported on this terminal.'))
                    view.setButton(0, _('OK'), itg.ID_OK, self.quit)
                else:
                    view = itg.ImageView(profilePic, emp.getName(), scaleUp=True)
                    view.setButton(0, 'Back', itg.ID_BACK, cb=self.quit)
            else:
                view = itg.MsgBoxView()
                view.setText(_('%s has no profile photo.') % emp.getName())
                view.setButton(0, _('OK'), itg.ID_OK, self.quit)
        else:
            view = itg.MsgBoxView()
            view.setText(_('Profile pictures are not supported.'))
            view.setButton(0, _('OK'), itg.ID_OK, self.quit)
        self.addView(view)


        
class TakeProfilePhotoDialog(itg.Dialog):
    
    def __init__(self, emp):
        super(TakeProfilePhotoDialog, self).__init__()
        self.__emp = emp
        self.__player = playit.PlayIT()
        self.__filename = '/tmp/profile-photo.jpg'
        
    def __del__(self):
        if (os.path.exists(self.__filename)):
            os.unlink(self.__filename)
        super(TakeProfilePhotoDialog, self).__del__()
    
    def onCreate(self):
        if (not hasattr(self.__emp, 'setProfilePicture')):
            view = itg.MsgBoxView()
            view.setText(_('Taking profile pictures is not supported.'))
            view.setButton(0, _('OK'), itg.ID_OK, self.quit)        
        elif (hasattr(itg, 'WebcamView')):
            view = itg.WebcamView()
            view.setTitle(_('Take photo...'))
            view.setButton(0, _('Cancel'), itg.ID_CANCEL, cb=self.cancel)
            view.enableButton(itg.WebcamView.BTN_SNAPSHOT, self.__onPhoto)
        else:
            view = itg.MsgBoxView()
            view.setText(_('Taking a photo is not supported on this terminal.'))
            view.setButton(0, _('OK'), itg.ID_OK, self.quit)        
        self.addView(view)
        
    def onShow(self):
        super(TakeProfilePhotoDialog, self).onShow()
        if (hasattr(itg, 'WebcamView')):        
            try:
                self.__player.videoCameraShow(*self.getView().getVideoRect())                
            except Exception as e:
                crashReport.createCrashReportFromException()
                log.err('Failed to show camera preview: %s' % (e,))
        
    def __onPhoto(self):
        self.__player.videoCameraSnapshot(self.__filename)
        dlg = _ConfirmProfilePhotoDialog(self.__emp, self.__filename)
        resID = dlg.run()
        if (resID != itg.ID_BACK):
            self.quit(resID)
        
    
class _ConfirmProfilePhotoDialog(itg.Dialog):
    
    def __init__(self, employee, filename):
        super(_ConfirmProfilePhotoDialog, self).__init__()
        self.__emp = employee
        self.__filename = filename
        view = itg.ImageView(title = _('Use this photo?'))
        view.setImage(filename, True)
        view.setButton(0, _('Yes'),    itg.ID_YES,    cb=self.__onYes)
        view.setButton(1, _('Back'),   itg.ID_BACK,   cb=self.back)
        view.setButton(2, _('Cancel'), itg.ID_CANCEL, cb=self.cancel)
        self.addView(view)
        
    def __onYes(self, btnID):
        (_resID, err) = itg.waitbox(_('Saving profile picture'), self.__savePicture)
        if (err != None):
            itg.msgbox(itg.MB_OK, _('Unable to save photo. %s') % err)
        else:
            itg.msgbox(itg.MB_OK, _('Profile picture saved.'))
        self.quit(btnID)
        
    def __savePicture(self):
        try:
            rawData = open(self.__filename).read()
            self.__emp.setProfilePicture(rawData)
            return None
        except Exception as e:
            return '%s' % (e,)

class DeleteProfilePhotoDialog(itg.PseudoDialog):
    
    def __init__(self, emp):
        super(DeleteProfilePhotoDialog, self).__init__()
        self.__emp = emp

    def run(self):
        if (not hasattr(self.__emp, 'deleteProfilePicture')):
            itg.msgbox(itg.MB_OK, _('Deleting profile pictures is not supported.'))
            return itg.ID_OK
        res = itg.msgbox(itg.MB_YES_NO, _('Delete photo?'))
        if (res == itg.ID_YES):
            (_resID, err) = itg.waitbox(_('Deleting photo...'), self.__deletePicture)
            if (err != None):
                itg.msgbox(itg.MB_OK, _('Unable to delete photo. %s') % err)
        return res
        
    def __deletePicture(self):
        try:
            self.__emp.deleteProfilePicture()
            return None
        except Exception as e:
            return '%s' % (e,)


#
#
# Support functions for dynamic buttons
#
#
class ProfilePictureMenuAction(dynButtons.Action):
     
    def getName(self):
        return 'profile.picture.menu'
     
    def getButtonText(self, actionParam, employee, languages):
        return _('Profile Photo')
     
    def getDialog(self, actionParam, employee, languages):
        return ProfilePhotoDialog(employee)
 
    def isEmployeeRequired(self, actionParam):
        return True
  
    def getHelp(self):
        return """
        Show profile picture menu.
         
        The profile picture menu shows the profile picture of the employee 
        running it and gives the option to take a new photo or to delete it.
         
        Actions used by this dialog are:
        
         - profile.picture.delete
         - profile.picture.take
 
        The profile picture is distributed to other terminals in the same group
        via network.
         
        Please note that this action is also used by the *profile.editor* 
        action.   
         
        See *profile.editor* for more details.
                 
        Example::
         
            <button>
                <pos>1</pos>
                <action>
                    <profile.picture.menu />
                </action>
            </button>
 
        """        
 
 
 
class ProfilePictureViewAction(dynButtons.Action):
     
    def getName(self):
        return 'profile.picture.view'
     
    def getButtonText(self, actionParam, employee, languages):
        return _('View Photo')
     
    def getDialog(self, actionParam, employee, languages):
        return ViewPictureDialog(employee)
 
    def isEmployeeRequired(self, actionParam):
        return True
 
    def getHelp(self):
        return """
        View profile picture.
         
        This action shows the profile picture of the employee running it.
         
        Please note that this action is also used by the *profile.picture.menu* 
        action.  
         
        See *profile.picture.menu* for more details.
                 
        Example::
         
            <button>
                <pos>1</pos>
                <action>
                    <profile.picture.view />
                </action>
            </button>
 
        """        
 
 
class ProfilePictureTakeAction(dynButtons.Action):
     
    def getName(self):
        return 'profile.picture.take'
     
    def getButtonText(self, actionParam, employee, languages):
        return _('Take Photo')
     
    def getDialog(self, actionParam, employee, languages):
        return TakeProfilePhotoDialog(employee)
 
    def isEmployeeRequired(self, actionParam):
        return True
 
    def getHelp(self):
        return """
        Take new profile picture.
         
        This action takes a new profile picture of the employee running it.
        The profile picture is distributed to other terminals in the same group 
        via network.
                 
        Please note that this action is also used by the *profile.editor* 
        action.  
        See *profile.editor* and *profile.picture.menu* for more details.
                 
        Example::
         
            <button>
                <pos>1</pos>
                <action>
                    <profile.picture.take />
                </action>
            </button>
 
        """        
 
 
 
class ProfilePictureDeleteAction(dynButtons.Action):
     
    def getName(self):
        return 'profile.picture.delete'
     
    def getButtonText(self, actionParam, employee, languages):
        return _('Delete Photo')
     
    def getDialog(self, actionParam, employee, languages):
        return DeleteProfilePhotoDialog(employee)
 
    def isEmployeeRequired(self, actionParam):
        return True
 
    def getHelp(self):
        return """
        Delete profile picture.
         
        This action deletes the profile picture of the employee running
        it.
         
        Please note that this action is also used by the *profile.picture.menu* 
        action.  
         
        See *profile.editor* and *profile.picture.menu* for more details.
                 
        Example::
         
            <button>
                <pos>1</pos>
                <action>
                    <profile.picture.delete />
                </action>
            </button>
 
        """        
 
 
 
def loadPlugin():
    dynButtons.registerAction(ProfilePictureMenuAction())
    dynButtons.registerAction(ProfilePictureViewAction())    
    dynButtons.registerAction(ProfilePictureTakeAction())    
    dynButtons.registerAction(ProfilePictureDeleteAction())    
 
 
 
 


