# -*- coding: utf-8 -*-
#
# Copyright 2011 Grosvenor Technology
#

import itg
import emps
import badge
import led
import autoEnrolDlg


from applib import bio
from applib.db.tblSettings import getAppSetting
from applib.gui import msg


def getIdentifiedEmpByCardRead(valid, reader, decoder, data, manager=None, allowAutoEnrol=True):
    if (not valid):
        msg.failMsg(_('Invalid card'))
        return None
    try:
        (siteCode, badgeCode) = badge.decodeBadgeData(data)
    except Exception as e:
        msg.failMsg(str(e))    
        return None
    if (not badge.isSiteCodeValid(siteCode)):    
        msg.failMsg(_('Wrong card!'))
        return None
    # get employee out of database
    emp = emps.getEmpByBadgeCode(badgeCode)
    if (emp != None):
        itg.tickSound()
        return emp
    # employee not in database, check other means
    empLimitBy = getAppSetting('emp_limit_by')
    if (empLimitBy == 'none'):
        # just create new employee
        emp = emps.createEmployeeFromBadgeCode(badgeCode)
        if (emp != None):
            itg.tickSound()
            return emp
    elif (empLimitBy == 'supervisor'):
        # create employee but check for valid distribution data
        emp = emps.createEmployeeFromBadgeCode(badgeCode)
        if (hasattr(emp, 'getUserValid') and emp.getUserValid()!=None):
            itg.tickSound()
            return emp
        elif (allowAutoEnrol and hasattr(emp, 'setUserValid')):
            # give option to create new employee
            dlg = autoEnrolDlg.Dialog(emp, manager)
            dlg.run()
            return None
    msg.failMsg(_('No employee for that badge code!'))
    return None


def getIdentifiedEmpByBiometric(templID, manager=None, allowAutoEnrol=True):
    if (templID == None):
        msg.failMsg(_('Could not identify finger!'))
        return None
    # get employee out of database
    emp = emps.getEmpByTmplID(templID)
    if (emp != None):
        return emp
    # employee not in database, check other means
    empLimitBy = getAppSetting('emp_limit_by')
    if (empLimitBy == 'none'):
        # just create new employee
        emp = emps.createEmployeeFromTmplID(templID)
        if (emp != None):
            return emp
    elif (empLimitBy == 'supervisor'):
        # create employee but check for valid distribution data
        emp = emps.createEmployeeFromTmplID(templID)
        if (hasattr(emp, 'getUserValid') and emp.getUserValid()!=None):
            return emp
        elif (allowAutoEnrol and hasattr(emp, 'setUserValid')):
            # give option to create new employee
            dlg = autoEnrolDlg.Dialog(emp, manager)
            dlg.run()
            return None
    msg.failMsg(_('No employee for this template!'))
    return None


def getIdentifiedEmpByKeypadID(keypadID, manager=None, allowAutoEnrol=True):
    if (not keypadID):
        return None
    padKeypad = getAppSetting('pad_keypad')
    if (padKeypad):
        keypadID = keypadID.zfill(padKeypad)
    # check for local supervisor
    try:
        # NOTE: The supervisor id is numeric, so we convert the keypadID 
        # to a numeric value to get rid of leading zeros etc.
        if (getAppSetting('local_supervisor_enabled') and int(keypadID) == getAppSetting('local_supervisor_id')):
            return emps.createEmployeeFromKeypadID(keypadID, isLocalSupervisor=True)
    except ValueError:
        pass
    # get employee out of database
    emp = emps.getEmpByKeypadID(keypadID)
    if (emp != None):
        return emp
    # if employee needs creating, badge length must match keypadID length
    badgeLength = getAppSetting('badge_length')
    if (badgeLength and len(keypadID) != badgeLength):
        msg.failMsg(_('Wrong ID!'))
        return None
    # employee not in database, check other means
    empLimitBy = getAppSetting('emp_limit_by')
    if (empLimitBy == 'none'):
        # just create new employee
        emp = emps.createEmployeeFromKeypadID(keypadID)
        if (emp != None):
            return emp
    elif (empLimitBy == 'supervisor'):
        # create employee but check for valid distribution data
        emp = emps.createEmployeeFromKeypadID(keypadID)
        if (hasattr(emp, 'getUserValid') and emp.getUserValid()!=None):
            return emp
        elif (allowAutoEnrol and hasattr(emp, 'setUserValid')):
            # give option to create new employee
            dlg = autoEnrolDlg.Dialog(emp, manager)
            dlg.run()
            return None
    msg.failMsg(_('No employee with that ID!'))
    return None



class Dialog(bio.BioIdentifyMixin, itg.Dialog):
    
    def __init__(self, title=None, useKeypadView=False, showKeypadOption=True, defaultData=None, allowReader=True, allowBio=True):
        super(Dialog, self).__init__()
        self.__emp = None
        self.__title = title
        self.__manager = None
        self.__allowAutoEnrol = True
        if (allowReader):
            self.setReaderCb(self.__onCardRead)
        if (allowBio and bio.isWorking() and bio.hasTemplateRepository()):
            self.bioIdentifyEnable()
        if (useKeypadView):
            self.__createKeypadView(defaultData)
        elif (allowBio and bio.isWorking() and bio.hasTemplateRepository()):
                self.__createBioView(showKeypadOption)
        elif (allowReader and hasattr(itg, 'getReaderType') and itg.getReaderType() == 'none'):
            self.__createKeypadView(defaultData)            
        else:
            self.__createReaderView(showKeypadOption)
        self.setTimeout(15)
    
    def setManager(self, manager):
        self.__manager = manager
        
    def allowAutoEnrol(self, allow=True):
        self.__allowAutoEnrol = allow

    def __createBioView(self, showKeypadOption):    
        view = itg.BioScanView(self.__title)
        if (showKeypadOption):
            view.setButton(0, _('Keypad'), itg.ID_KEYPAD, self.__onKeypad)
            view.setButton(1, _('Cancel'), itg.ID_CANCEL, self.cancel)
        else:
            view.setButton(0, _('Cancel'), itg.ID_CANCEL, self.cancel)
        self.addView(view)

    def __createReaderView(self, showKeypadOption):    
        view = itg.ReaderInputView(self.__title)
        if (showKeypadOption):
            view.setButton(0, _('Keypad'), itg.ID_KEYPAD, self.__onKeypad)
            view.setButton(1, _('Cancel'), itg.ID_CANCEL, self.cancel)
        else:
            view.setButton(0, _('Cancel'), itg.ID_CANCEL, self.cancel)
        self.addView(view)

    def __createKeypadView(self, defaultData=None):
        view = itg.NumberInputView(self.__title)
        view.setButton(0, _('OK'), itg.ID_OK, self.__onOK)
        view.setButton(1, _('Cancel'), itg.ID_CANCEL, self.cancel)
        if (defaultData):
            view.setValue(defaultData)
        self.addView(view)
        
    def __onKeypad(self, btnID):
        self.__createKeypadView()
        self.getView().show()
        
    def __onCardRead(self, valid, reader, decoder, data):
        self.__emp = getIdentifiedEmpByCardRead(valid, reader, decoder, data, self.__manager, self.__allowAutoEnrol)
        if (self.__emp):
            self.quit(itg.ID_OK)
        else:
            self.quit(itg.ID_CANCEL)
        
    def __onOK(self, btnID):
        keypadID = self.getView().getValue()
        if (not keypadID):
            return
        self.__emp = getIdentifiedEmpByKeypadID(keypadID, self.__manager, self.__allowAutoEnrol)
        if (self.__emp):
            self.quit(itg.ID_OK)
        else:
            self.quit(itg.ID_CANCEL)
        
    def getEmployee(self):
        return self.__emp

    def onBioScanComplete(self):
        itg.tickSound()
        view = self.getView()
        if (hasattr(view, 'indicateScanComplete')):
            view.indicateScanComplete()

    def __bioRestart(self):
        view = self.getView()
        if (hasattr(view, 'clearIndicator')):
            view.clearIndicator()
        view.setTitle(self.__title)
        self.bioIdentifyRestart()
    
    def onBioIdentify(self, templID):
        view = self.getView()
        if (templID == None and hasattr(view, 'indicateFailure') and hasattr(itg, 'runIn')):
            led.on(led.LED_ALL | led.LED_STATUS, led.RED, 2*1000)
            itg.failureSound()
            view.indicateFailure()
            view.setTitle(_('Could not identify finger!'))
            itg.runIn(1, self.__bioRestart)
            self.setTimeout(5)
        else:
            if (hasattr(view, 'clearIndicator')):            
                view.clearIndicator()
            self.__emp = getIdentifiedEmpByBiometric(templID, self.__manager, self.__allowAutoEnrol)
            if (self.__emp):
                if not self.__emp.checkConsent():
                    self.quit(itg.ID_CANCEL)
                self.quit(itg.ID_OK)
            else:
                if (hasattr(view, 'clearIndicator')):            
                    view.clearIndicator()
