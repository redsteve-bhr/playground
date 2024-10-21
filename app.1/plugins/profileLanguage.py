# -*- coding: utf-8 -*-
#
# Copyright 2013 Grosvenor Technology
#
# 
import itg
from engine import dynButtons
from applib.db.tblSettings import getAppSetting

class EnterUserLanguageDialog(itg.Dialog):

    def __init__(self, emp):
        super(EnterUserLanguageDialog, self).__init__()
        self.__emp = emp
        if (hasattr(emp, 'setUserLanguage') and hasattr(emp, 'deleteUserLanguage')):
            view = itg.ListView(_('Select language'))
            view.setOkButton(_('OK'), self.__onOK)
            view.setCancelButton(_('Cancel'), self.cancel)
            langs = getAppSetting('emp_override_languages')
            for l in langs:
                view.appendRow(l.upper(), data=l)
            view.appendRow(_('Use system language'), data=None)
            currentLang = emp.getUserLanguage()
            (pos, _row) = view.findRowBy('data', currentLang)
            if (pos != None):
                view.selectRow(pos)            
        else:
            view = itg.MsgBoxView()
            view.setText(_('User languages are not supported.'))
            view.setButton(0, _('OK'), itg.ID_OK, self.quit)            
        self.addView(view)
        
    def __onOK(self, btnID):
        language = self.getView().getSelectedRow()['data']
        if (self.__emp.getUserLanguage() != language):
            itg.waitbox(_('Setting language, please wait...'), self.__setLanguage, (language,))
        self.quit(btnID)
 
    def __setLanguage(self, language):
        if (language == None):
            self.__emp.deleteUserLanguage()
        else:
            self.__emp.setUserLanguage(language)

        
 
 
class ProfileLanguageAction(dynButtons.Action):
     
    def getName(self):
        return 'profile.language'
     
    def getButtonText(self, actionParam, employee, languages):
        return _('Language')
     
    def getDialog(self, actionParam, employee, languages):
        return EnterUserLanguageDialog(employee)
 
    def isEmployeeRequired(self, actionParam):
        return True
 
    def getHelp(self):
        return """
        Change User-language of employee.
         
        This action allows an employee's preferred language to be changed.
        The User-language is distributed to other terminals in the same group via network. 
         
        Please note that this action is also used by the *profile.editor* 
        action. 
         
        See *profile.editor* for more details.
                 
        Example::
         
            <button>
                <pos>1</pos>
                <action>
                    <profile.language />
                </action>
            </button>
 
        """        
 
 
 
def loadPlugin():
    dynButtons.registerAction(ProfileLanguageAction())
   
 


