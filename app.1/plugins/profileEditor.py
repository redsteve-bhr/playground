# -*- coding: utf-8 -*-
#
# Copyright 2013 Grosvenor Technology
#
import itg
from engine import dynButtons
from applib.db.tblSettings import getAppSetting
from applib import bio
import app 
 
class ProfileEditorDialog(itg.Dialog):
     
    def __init__(self, emp):
        super(ProfileEditorDialog, self).__init__()
        self.__emp = emp
        if (emp.isLocalSupervisor()):
            view = itg.MsgBoxView()
            view.setText(_('Local supervisor not allowed.'))
            view.setButton(0, _('OK'), itg.ID_OK, self.quit)
        else:
            view = itg.MenuView(emp.getName())
            view.setBackButton(_('Back'), self.back)
            self.__createMenu(view)
        self.addView(view)
 
    def __createMenu(self, menu):
        vMethods = self.__emp.getVerificationMethods()
        menu.removeAllRows()
        
        if (hasattr(self.__emp, 'setUserVerificationMethod') and getAppSetting('emp_verify_override_methods') and dynButtons.hasAction('profile.verifyMethod')):
            menu.appendRow(_('Set Verification Order'), hasSubItems=True, cb=self.__onSetMethod)
            
        if (hasattr(self.__emp, 'setTemplates') and (('bio' in vMethods or 'bioNone' in vMethods) or (bio.isWorking() and bio.hasTemplateRepository())) and dynButtons.hasAction('profile.templates.enrol')):
            menu.appendRow(_('Enrol Finger'), hasSubItems=True, cb=self.__onEnrol)
            
        if (hasattr(self.__emp, 'setUserPin') and 'userPin' in vMethods and dynButtons.hasAction('profile.pin')):
            menu.appendRow(_('Enter PIN'), hasSubItems=True, cb=self.__onUserPin)
        elif (hasattr(self.__emp, 'setPin') and 'pin' in vMethods and dynButtons.hasAction('profile.pin')):
            menu.appendRow(_('Enter PIN'), hasSubItems=True, cb=self.__onUserPin)

        if (app.hasCameraSupport() and hasattr(self.__emp, 'setProfilePicture') and dynButtons.hasAction('profile.picture.menu')):
            menu.appendRow(_('Change Photo'), hasSubItems=True, cb=self.__onPhoto)
            
        if (hasattr(self.__emp, 'setBadgeCode') and dynButtons.hasAction('profile.badge')):
            menu.appendRow(_('Change BadgeCode'), hasSubItems=True, cb=self.__onUserBadgeCode)
            
        if (hasattr(self.__emp, 'setUserName') and dynButtons.hasAction('profile.name')):
            menu.appendRow(_('Change Name'), hasSubItems=True, cb=self.__onName)
            
        if (hasattr(self.__emp, 'setUserLanguage') and dynButtons.hasAction('profile.language')):
            menu.appendRow(_('Change Language'), hasSubItems=True, cb=self.__onLanguage)
            
        if (hasattr(self.__emp, 'setUserRoles') and dynButtons.hasAction('profile.roles')):
            menu.appendRow(_('Change Roles'), hasSubItems=True, cb=self.__onRoles)
            
        menu.appendRow(_('View Details'), hasSubItems=True, cb=self.__onInfo)
        
        if (hasattr(self.__emp, 'deleteAccount')):
            menu.appendRow(_('Delete Profile'), hasSubItems=True, cb=self.__onDelete)
        
    def __onSetMethod(self, pos, row):
        dlg = dynButtons.getActionDialogByName('profile.verifyMethod', employee=self.__emp)
        resID = dlg.run()
        if (resID == itg.ID_OK):
            self.__createMenu(self.getView())
             
    def __onInfo(self, pos, row):
        dlg = dynButtons.getActionDialogByName('profile.info', employee=self.__emp)
        self.runDialog(dlg)        
 
    def __onEnrol(self, pos, row):
        dlg = dynButtons.getActionDialogByName('profile.templates.enrol', employee=self.__emp)
        self.runDialog(dlg)        
     
    def __onUserPin(self, pos, row):
        dlg = dynButtons.getActionDialogByName('profile.pin', employee=self.__emp)
        self.runDialog(dlg)        
         
    def __onUserBadgeCode(self, pos, row):
        dlg = dynButtons.getActionDialogByName('profile.badge', employee=self.__emp)
        self.runDialog(dlg)        
         
    def __onPhoto(self, pos, row):
        dlg = dynButtons.getActionDialogByName('profile.picture.menu', employee=self.__emp)
        self.runDialog(dlg)        

    def __onName(self, pos, row):
        dlg = dynButtons.getActionDialogByName('profile.name', employee=self.__emp)
        self.runDialog(dlg)        
 
    def __onLanguage(self, pos, row):
        dlg = dynButtons.getActionDialogByName('profile.language', employee=self.__emp)
        self.runDialog(dlg)
        
    def __onRoles(self, pos, row):
        dlg = dynButtons.getActionDialogByName('profile.roles', employee=self.__emp)
        self.runDialog(dlg)
        
    def __onDelete(self, pos, row):
        dlg = dynButtons.getActionDialogByName('profile.delete', employee=self.__emp)
        resID = dlg.run()
        # Quit profile editor when profile was deleted
        if (resID == itg.ID_OK):
            self.quit(itg.ID_OK)
 
 
 
class ProfileInfoDialog(itg.Dialog):
     
    def __init__(self, emp):
        super(ProfileInfoDialog, self).__init__()
        view = itg.MenuView(emp.getName())
        view.appendRow(_('Name'), emp.getName(), cb=self.__onDetails)
        view.appendRow(_('Languages'), ','.join(emp.getLanguages(useManagerIfAvailable=False)), cb=self.__onDetails)
        view.appendRow(_('Roles'), ','.join(emp.getRoles()), cb=self.__onDetails)
        view.appendRow(_('Verification Methods'), ','.join(emp.getVerificationMethods()), cb=self.__onDetails)
        view.appendRow(_('Employee ID'), emp.getEmpID(), cb=self.__onDetails)
        view.appendRow(_('BadgeCode'), emp.getBadgeCode(), cb=self.__onDetails)
        view.appendRow(_('Keypad ID'), emp.getKeypadID(), cb=self.__onDetails)
        if (hasattr(emp, 'getProfileDataID')):
            view.appendRow(_('Profile Data ID'), emp.getProfileDataID(), cb=self.__onDetails)        
        if (hasattr(emp, 'getTemplates')):
            view.appendRow(_('Templates enrolled'), str(self.__getNumberOfTemplates(emp)), cb=self.__onDetails)        
        view.setBackButton(_('Back'), self.back)
        view.setCancelButton(_('Cancel'), self.cancel)
        self.addView(view)
 
    def __getNumberOfTemplates(self, emp):
        tmpls = emp.getTemplates()
        numTemplates = len(tmpls) if (tmpls != None) else 0
        return numTemplates
 
    def __onDetails(self, pos, row):
        itg.msgbox(itg.MB_OK, row['value'])
 
 
 
class ProfileDeleteDialog(itg.PseudoDialog):
     
    def __init__(self, emp):
        super(ProfileDeleteDialog, self).__init__()
        self.__emp = emp
 
    def run(self):
        res = itg.msgbox(itg.MB_YES_NO, _('Delete profile?'))
        if (res != itg.ID_YES):
            return itg.ID_CANCEL
        itg.waitbox(_('Deleting profile...'), self.__delete)
        if (bio.isWorking() and bio.hasTemplateRepository()):
            dlg = bio.BioSyncDialog()
            res = dlg.run()
        return itg.ID_OK
         
    def __delete(self):
        self.__emp.deleteAccount()
 
#
#
# Support functions for dynamic buttons
#
#
class ProfileInfoAction(dynButtons.Action):
     
    def getName(self):
        return 'profile.info'
     
    def getButtonText(self, actionParam, employee, languages):
        return _('Profile Info')
     
    def getDialog(self, actionParam, employee, languages):
        return ProfileInfoDialog(employee)
 
    def isEmployeeRequired(self, actionParam):
        return True
 
    def getHelp(self):
        return """
        Show employee/user profile information.
         
        This action shows profile information of the employee running it. The 
        following information are shown:
        
         - name of employee
         - preferred languages
         - roles of employee
         - verification methods
         - employee ID
         - badge code
         - keypad ID
         - template ID
         - templates enrolled    
         
        Please note that this action is also used by the *profile.editor* 
        action.  
         
        See *profile.editor* for more details.
                 
        Example::
         
            <button>
                <pos>1</pos>
                <action>
                    <profile.info />
                </action>
            </button>
 
        """        
 
 
class ProfileEditorAction(dynButtons.Action):
     
    def getName(self):
        return 'profile.editor'
     
    def getButtonText(self, actionParam, employee, languages):
        return _('Profiles')
     
    def getDialog(self, actionParam, employee, languages):
        return ProfileEditorDialog(employee)
 
    def isEmployeeRequired(self, actionParam):
        return True
 
    def getHelp(self):
        return """
        Show profile options.
         
        Actions used by the *profile.editor*:
        
         - profile.verifyMethod
         - profile.templates.enrol
         - profile.picture.menu
         - profile.pin
         - profile.info
         - profile.delete
         - profile.language
         - profile.roles

        The *switchEmployee* button option can be used to allow users to 
        change the profile of other users (see :ref:`button_options`).
        
        Example::
         
            <button>
                <pos>1</pos>
                <action>
                    <profile.editor />
                </action>
                <options><switchEmployee /></options>
                <requiredRole>supervisor</requiredRole>                
            </button>
 
        """        
 
 
 
class ProfileDeleteAction(dynButtons.Action):
     
    def getName(self):
        return 'profile.delete'
     
    def getButtonText(self, actionParam, employee, languages):
        return _('Delete Profile')
     
    def getDialog(self, actionParam, employee, languages):
        return ProfileDeleteDialog(employee)
 
    def isEmployeeRequired(self, actionParam):
        return True
 
    def getHelp(self):
        return """
        Delete employee/user profile (templates, user-pin, etc).
         
        This action deletes the profile of the employee running it. The profile
        will be deleted locally and also via data distribution (e.g. on other
        terminals in the distribution group).
         
        Please note that this action is also used by the *profile.editor* 
        action. 
         
        See *profile.editor* for more details.
                 
        Example::
         
            <button>
                <pos>1</pos>
                <action>
                    <profile.delete />
                </action>
            </button>
 
        """        
 
 
def loadPlugin():
    dynButtons.registerAction(ProfileInfoAction())
    dynButtons.registerAction(ProfileEditorAction())
    dynButtons.registerAction(ProfileDeleteAction())
 
 
 
 
 
 
 
 
 


