# -*- coding: utf-8 -*-
#
# Copyright 2023 Grosvenor Technology
#
import itg
import datetime
import miscUtils
from webClient import getAppTransactions
from miscUtils import userFriendlyDate
import xml.etree.cElementTree as ET

class ScheduleOverrideDialog(itg.Dialog):
    
    def __init__(self, actionParam, emp, languages):
        super(ScheduleOverrideDialog, self).__init__()
        self.__actionParam = actionParam
        self.__emp = emp
        self.__languages = languages

        view = itg.MsgBoxView()
        expiry = self.__getDisplayExpiryTime()
        view.setText(_('Lift restriction on next punch for {name}?\n\nIf the user does not punch, the restriction will automatically expire on {expiry}.').format(name=self.__emp.getName(), expiry=expiry))
        view.setButton(0, _('OK'), itg.ID_OK, self.__onOK)
        view.setButton(1, _('Cancel'), itg.ID_CANCEL, self.quit)
        self.addView(view)

    def __getExpiryMinutes(self):
        """Reads and returns the Expiry Minutes setting from the buttons 
        file. Defaults to 60 if no entry is found."""
        expiryMinutes = self.__actionParam.getInteger('expiryMinutes', 60)
        return expiryMinutes

    def __getDisplayExpiryTime(self):
        """Returns the expiry time in local time and user-friendly format"""
        # Time now
        now = datetime.datetime.now()
        
        # Expiry time
        delta = datetime.timedelta(minutes=self.__getExpiryMinutes())
        expiry = now + delta
        
        # Format
        expiryStr = userFriendlyDate(expiry)
        
        # Return formatted string
        return expiryStr
                
    def __onOK(self, btnId):
        # Time now
        now = datetime.datetime.now()
        timeStr = miscUtils.timestampWithUTCOffset(now)
        
        # Time of override expiry
        delta = datetime.timedelta(minutes=self.__getExpiryMinutes())
        expiryTime = now + delta 
        expiryTimeStr = miscUtils.timestampWithUTCOffset(expiryTime)
        
        empId = self.__emp.getEmpID()
        template = """
            <scheduleOverride>
              <time>{timeStr}</time>
              <empID>{empId}</empID>
              <expiryTime>{expiryTimeStr}</expiryTime>
            </scheduleOverride>
        """.format(timeStr=timeStr, empId=empId, expiryTimeStr=expiryTimeStr)
        data = ET.fromstring(template)
        transactions = getAppTransactions()
        if (not transactions.hasSpace()):
            raise Exception(_('Transaction buffer full!'))

        # Send transaction as supervisor
        supervisor = self.__emp.getManager(self.__emp)        
        transactions.addTransaction(data, supervisor)

        self.quit(btnId)
