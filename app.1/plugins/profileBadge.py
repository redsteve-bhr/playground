# -*- coding: utf-8 -*-
#
# Copyright 2013 Grosvenor Technology
#
# 
import itg
from engine import badge
from engine import dynButtons
import emps 
 
class EnterUserBadgeDialog(itg.Dialog):
     
    def __init__(self, emp):
        super(EnterUserBadgeDialog, self).__init__()
        self.__emp = emp
        if (hasattr(emp, 'setUserBadgeCode') or hasattr(emp, 'setBadgeCode')):
            view = itg.NumberInputView(_('Please enter new Badge'), password=False )
            view.setButton(0, _('OK'), itg.ID_OK, cb=self.__onBadge)
            view.setButton(1, _('Cancel'), itg.ID_CANCEL, cb=self.cancel)
            self.setReaderCb(self.__onCardRead)
        else:
            view = itg.MsgBoxView()
            view.setText(_('User BadgeCodes are not supported.'))
            view.setButton(0, _('OK'), itg.ID_OK, self.quit)            
        self.addView(view)
 
    def __onBadge(self, btnID):
        view = self.getView()
        self.__Badge = view.getValue()
        if (self.__Badge == ''):
            if (hasattr(self.__emp, 'deleteUserBadgeCode')):
                resID = itg.msgbox(itg.MB_OK_CANCEL, _('Unset badgecode?'))
                if (resID == itg.ID_OK):
                    itg.waitbox(_('Setting BadgeCode, please wait...'), self.__unsetBadge)
                self.quit(resID)
        else:
            itg.waitbox(_('Setting BadgeCode, please wait...'), self.__setBadge)
            self.quit(btnID)
 
    def __setBadge(self):
        if not self.__isDuplicate(self.__Badge):
            if (hasattr(self.__emp, 'setUserBadgeCode')):
                self.__emp.setUserBadgeCode(self.__Badge)
            else:
                self.__emp.setBadgeCode(self.__Badge)
 
    def __unsetBadge(self):
        self.__emp.deleteUserBadge()
 
    def __onCardRead(self, valid, reader, decoder, data):
        (siteCode, badgeCode) = badge.decodeBadgeData(data)
        view = self.getView()
        view.setValue(badgeCode)
        
    def __isDuplicate(self, badgeCode):
        """If there is another employee with the same badge code, report this
        to the user and return True
        """
        rows = emps.getAppEmps().getEmpsByBadgeCode(badgeCode)
        empID = self.__emp.getEmpID()
        for row in rows:
            if row['EmpID'] != empID:
                itg.msgbox(itg.MB_OK, _('Badgecode already registered, against %s' % row['Name']))
                return True
        return False

class ProfileBadgeAction(dynButtons.Action):
     
    def getName(self):
        return 'profile.badge'
     
    def getButtonText(self, actionParam, employee, languages):
        return _('Enter BadgeCode')
     
    def getDialog(self, actionParam, employee, languages):
        return EnterUserBadgeDialog(employee)
 
    def isEmployeeRequired(self, actionParam):
        return True
 
    def getHelp(self):
        return """
        Change User-Badge of employee.
         
        This action prompts for a new User-Badge for the employee running the
        action. The User-Badge is distributed to other terminals in the same 
        group via network. 
         
        Please note that this action is also used by the *profile.editor* 
        action. 
         
        See *profile.editor* for more details.
                 
        Example::
         
            <button>
                <pos>1</pos>
                <action>
                    <profile.badge />
                </action>
            </button>
 
        """        
 
 
 
def loadPlugin():
    dynButtons.registerAction(ProfileBadgeAction())
   
 

