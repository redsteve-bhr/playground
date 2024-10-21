# -*- coding: utf-8 -*-
#
# Copyright 2013 Grosvenor Technology
#
# 
import itg
from engine import dynButtons
 
 
class EnterUserPinDialog(itg.Dialog):
     
    def __init__(self, emp):
        super(EnterUserPinDialog, self).__init__()
        self.__emp = emp
        if (hasattr(emp, 'setUserPin') or hasattr(emp, 'setPin')):
            view = itg.NumberInputView(_('Please enter new PIN'), password=True )
            view.setButton(0, _('OK'), itg.ID_OK, cb=self.__onPin1)
            view.setButton(1, _('Cancel'), itg.ID_CANCEL, cb=self.cancel)
        else:
            view = itg.MsgBoxView()
            view.setText(_('User PINs are not supported.'))
            view.setButton(0, _('OK'), itg.ID_OK, self.quit)            
        self.addView(view)
 
    def __onPin1(self, btnID):
        view = self.getView()
        self.__pin1 = view.getValue()
        if (self.__pin1 == ''):
            if (hasattr(self.__emp, 'deleteUserPin')):
                resID = itg.msgbox(itg.MB_OK_CANCEL, _('Unset password?'))
                if (resID == itg.ID_OK):
                    itg.waitbox(_('Setting PIN, please wait...'), self.__unsetPin)
                self.quit(resID)
        else:
            view.setTitle(_('Please confirm PIN'))
            view.setValue('')
            view.setButton(0, _('OK'), itg.ID_OK, cb=self.__onPin2)
 
    def __onPin2(self, btnID):
        view = self.getView()
        if (self.__pin1 != view.getValue()):
            itg.msgbox(itg.MB_OK, _('The PINs you entered are not the same!'))
            self.cancel()
        else:
            itg.waitbox(_('Setting PIN, please wait...'), self.__setPin)
            self.quit(btnID)
 
    def __setPin(self):
        if (hasattr(self.__emp, 'setUserPin')):
            self.__emp.setUserPin(self.__pin1)
        else:
            self.__emp.setPin(self.__pin1)
 
    def __unsetPin(self):
        self.__emp.deleteUserPin()
 
 
class ProfilePinAction(dynButtons.Action):
     
    def getName(self):
        return 'profile.pin'
     
    def getButtonText(self, actionParam, employee, languages):
        return _('Enter PIN')
     
    def getDialog(self, actionParam, employee, languages):
        return EnterUserPinDialog(employee)
 
    def isEmployeeRequired(self, actionParam):
        return True
 
    def getHelp(self):
        return """
        Change User-Pin of employee.
         
        This action prompts for a new User-Pin for the employee running the
        action. The new PIN must be entered twice. The User-PIN is distributed
        to other terminals in the same group via network. 
         
        Please note that this action is also used by the *profile.editor* 
        action. 
         
        See *profile.editor* for more details.
                 
        Example::
         
            <button>
                <pos>1</pos>
                <action>
                    <profile.pin />
                </action>
            </button>
 
        """        
 
 
 
def loadPlugin():
    dynButtons.registerAction(ProfilePinAction())
   
 


