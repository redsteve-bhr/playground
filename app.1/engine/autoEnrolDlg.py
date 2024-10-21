# -*- coding: utf-8 -*-
#
# Copyright 2011 Grosvenor Technology
#

import itg
import dynButtons
import led
from applib.db.tblSettings import getAppSetting

class Dialog(itg.PseudoDialog):

    def __init__(self, emp, manager):
        super(Dialog, self).__init__()
        self.__emp = emp
        self.__manager = manager
    
    def run(self):
        supervisorWasManager = (self.__manager != None)
        # check if manager is known and has required role
        if (self.__manager == None): # identify manager
            dlg = AskToAddEmployeeDialog();
            resID = dlg.run()
            if (resID != itg.ID_YES):
                return itg.ID_CANCEL
            dlg = dynButtons.IdentifyVerifyDialog(interceptLocalSupervisor=False, allowAutoEnrol=False)
            dlg.setIdentifyTitle(_('Please identify as supervisor'))
            resID = dlg.run()
            if (resID not in (itg.ID_OK, itg.ID_KEYPAD, itg.ID_NEXT)):
                return itg.ID_CANCEL
            self.__manager = dlg.getEmployee()            
            if (self.__manager == None):
                return itg.ID_CANCEL
        # check required role
        if (self.__manager.isSupervisor() or self.__manager.isLocalSupervisor()):
            # ask manager if he wants to create employee
            if (supervisorWasManager):
                resID = itg.msgbox(itg.MB_YES_NO, _('Employee is not in database, create now?'))
            else:
                resID = itg.ID_YES # asked already before identified supervisor
            if (resID == itg.ID_YES):
                try:
                    self.__emp.setUserValid()
                except Exception as e:
                    itg.msgbox(itg.MB_OK, _('Error creating employee (%s)') % e)
                    return itg.ID_CANCEL
                itg.msgbox(itg.MB_OK, _('Employee has been created.'))
                self.__emp.setManager(self.__manager)
                # go to profile editor
                dlg = dynButtons.getActionDialogByName('profile.editor', employee=self.__emp)
                dlg.run()
                return itg.ID_OK
        else:
            # not supervisor
            itg.msgbox(itg.MB_OK, _('Not supervisor'))
        return itg.ID_CANCEL
            
        
class AskToAddEmployeeDialog(itg.Dialog):

    def __init__(self, timeout=None):
        super(AskToAddEmployeeDialog, self).__init__()
        led.on(led.LED_ALL | led.LED_STATUS, led.RED, 5*1000)
        itg.failureSound()        
        view = itg.MsgBoxView()
        view.setText(_('Employee is not in database!\nCall supervisor to enrol.'))
        view.setButton(0, _('OK'), itg.ID_OK, cb=self.cancel)
        view.setButton(1, _('Supervisor'), itg.ID_ADD, cb=self._onSupervisor)
        self.addView(view)
        # Count down like failMsg
        self.setTimeout(1)
        if (timeout == None):
            self.__timeout = getAppSetting('emp_fail_msg_sec')
                
    def _onSupervisor(self, btnID):
        resID = itg.msgbox(itg.MB_YES_NO, _('Create employee now?'))
        self.quit(resID)
        
    def onTimeout(self):
        self.__timeout -= 1
        self.getView().setButton(0, _('OK (%s)') % self.__timeout, itg.ID_OK, self.cancel)
        if (self.__timeout <= 0):
            self.quit(itg.ID_TIMEOUT)        





