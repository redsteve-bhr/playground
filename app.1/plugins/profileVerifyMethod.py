# -*- coding: utf-8 -*-
#
# Copyright 2013 Grosvenor Technology
#
 
import itg
from engine import dynButtons, empVerifyDlg
 
from applib.db.tblSettings import getAppSetting
 
 
class SelectPrimaryVerificationMethod(itg.Dialog):
     
    def __init__(self, emp):
        super(SelectPrimaryVerificationMethod, self).__init__()
        self.__emp = emp
        if (hasattr(self.__emp, 'setUserVerificationMethod')):
            view = itg.ListView(_('Select Method'))
            view.setOkButton(_('OK'), self.__onOK)
            view.setCancelButton(_('Cancel'), self.cancel)
            vMethods = getAppSetting('emp_verify_override_methods')
            for vMethod in vMethods:
                view.appendRow(empVerifyDlg.getVerificationMethodName(vMethod), data=vMethod)
            if (hasattr(self.__emp, 'setUserVerificationDefaultMethod')):
                view.appendRow(_('Use system order'), data=None)            
            currentMethod = emp.getUserVerificationMethod()
            (pos,_row) = view.findRowBy('data', currentMethod)
            if (pos != None):
                view.selectRow(pos)
        else:
            view = itg.MsgBoxView()
            view.setText(_('User verification methods are not supported.'))
            view.setButton(0, _('OK'), itg.ID_OK, self.quit)                    
        self.addView(view)
     
    def __onOK(self, btnID):
        newMethod = self.getView().getSelectedRow()['data']
        if (newMethod == self.__emp.getUserVerificationMethod()):
            self.back()
        elif (newMethod == None and hasattr(self.__emp, 'setUserVerificationDefaultMethod')):
            itg.waitbox(_('Setting verification method, please wait...'), self.__unsetMethod)
            self.quit(btnID)
        else:
            itg.waitbox(_('Setting verification method, please wait...'), self.__setMethod, (newMethod,))
            self.quit(btnID)
 
    def __setMethod(self, vMethod):
        self.__emp.setUserVerificationMethod(vMethod)
 
    def __unsetMethod(self):
        self.__emp.setUserVerificationDefaultMethod()
 
 
 
class ProfileVerifyMethodAction(dynButtons.Action):
     
    def getName(self):
        return 'profile.verifyMethod'
     
    def getButtonText(self, actionParam, employee, languages):
        return _('Verification Method')
     
    def getDialog(self, actionParam, employee, languages):
        return SelectPrimaryVerificationMethod(employee)
 
    def isEmployeeRequired(self, actionParam):
        return True
 
    def getHelp(self):
        return """
        Set preferred verification method.
         
        This action prompts for the preferred verification method for the 
        employee running the action. The selected method is distributed
        to other terminals in the same group via network.
         
        The application setting 'emp_verify_override_methods' defines which
        methods are available.
         
        Please note that this action is also used by the *profile.editor* 
        action.  
         
        See *profile.editor* for more details.
                 
        Example::
         
            <button>
                <pos>1</pos>
                <action>
                    <profile.verifyMethod />
                </action>
            </button>
 
        """        
 
 
def loadPlugin():
    dynButtons.registerAction(ProfileVerifyMethodAction())


