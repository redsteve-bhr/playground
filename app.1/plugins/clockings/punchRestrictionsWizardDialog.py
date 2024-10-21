# -*- coding: utf-8 -*-
#
# Copyright 2023 Grosvenor Technology
#

import itg
import log
import datetime
from applib.utils import timeUtils
from applib.db.tblSettings import getAppSetting
from plugins.transfers import TransferDialog
from webClient import serverAction, transaction
from plugins.schedules.tblSchedules import getAppSchedules
import onlineState
from plugins.timecards import TimecardDialog
import xml.etree.cElementTree as ET


class _WizardDialog(itg.WizardDialog):
    """Descendant of the WizardDialog in the firmware, amended to call the
    onRefreshData method (if it exists) when navigating back through the 
    dialog pages as well as when navigating forward.
    """
    
    def _runWizard(self, pages):
        self.clearResultID()
        cur = 0
        lastID = itg.ID_NEXT
        
        while True:
            page = pages[cur]
            if (hasattr(page, 'skip') and page.skip()):
                pass
            else:
                # if ((lastID == itg.ID_NEXT or lastID == itg.ID_OK) and hasattr(page, 'onRefreshData')):
                if (lastID in [itg.ID_NEXT, itg.ID_OK, itg.ID_BACK]):
                    if hasattr(page, 'onCreate') and (page.getView() == None):
                        page.onCreate()
                    if hasattr(page, 'onRefreshData'):
                        page.onRefreshData()
                lastID = page.run()
                self.setResultID(lastID)

            if (lastID == itg.ID_CANCEL or lastID == itg.ID_TIMEOUT or lastID == itg.ID_ABORT):
                break
            elif (lastID == itg.ID_BACK):
                cur -= 1
                if (cur < 0):
                    break
            else:
                cur += 1
                if (cur >= len(pages)):
                    break

def isSameDay(datetime1, datetime2):
    if (datetime1.day == datetime2.day) and (datetime1.month == datetime2.month) and (datetime1.year == datetime2.year):
        return True
    else:
        return False

class PunchRestrictionsWizardDialog(_WizardDialog):
    
    def __init__(self, emp, clocking):
        super(PunchRestrictionsWizardDialog, self).__init__()
        self.__emp = emp
        self.__clocking = clocking
        self.__addPunchDate = datetime.datetime.today().date()
        self.__addPunchTime = datetime.datetime.today().time().replace(second=0)

        self.data = { 
                        'Emp'                     : self.__emp,
                        'Clocking'                : self.__clocking,
                        'ShiftEndStatus'          : False,
                        'OnlineSchedulesCompleted': False,
                        'IsStandalone'            : False,
                        'PromptLevels'            : self.__clocking.getPromptLevels(),
                        'SendAttestationResponse' : False
                    }
        self.pages = []

    def run(self):
        
        if self.__clocking is None:
            # This should never be the case, and the rest of this module 
            # assumes that self.__clocking is valid.
            log.err('No Clocking found for Punch Restrictions')
            return itg.ID_OK
    
        self.pages = []
        
        restrictions = self.__clocking.getRestrictions()
        if restrictions.onlineOnly and not onlineState.isOnline():
            itg.msgbox(itg.MB_OK, 'Server not available. Please try again later.')
            return itg.ID_CANCEL

        if restrictions.checkSchedules or (self.__clocking.requireTimecardApproval() and onlineState.isOnline()):
            self.pages.append(_ShiftEndDialog())

        if restrictions.checkSchedules:
            self.pages.append(_OnlineSchedulesDialog())
            self.pages.append(_OfflineSchedulesDialog())

        self.pages.append(_QuestionnaireDialog())

        if self.__clocking.requireTransfer():
            self.pages.append(TransferDialog())

        if self.__clocking.requireTimecardApproval():
            self.pages.append(TimecardDialog())

        self.pages = tuple(self.pages)
    
        # apply shared dictionary
        for p in self.pages:
            p.data = self.data

        # run wizard
        self._runWizard(self.pages)
        resID = self.getResultID()

        # Check result, including ID_UNKNOWN (this will be returned if ALL the pages were skipped)
        if (resID in (itg.ID_OK, itg.ID_NEXT, itg.ID_UNKNOWN)):
            self.__buildClockingXml()
            resID = itg.ID_OK

        if self.data['SendAttestationResponse']:
            # The Send Attestation Response flag has been set, so we should send it and set clocking as sent.
            self.__sendAttestationResponse()
            self.__clocking.setIsSent(True)

        return resID
    
    def __buildClockingXml(self):
        """Builds the XML for the 'data' element of a transaction, collating
        the selections that have been made by the user. Returns an XML element in
        the following format:

            <clocking>
                <type>in</type>
                <time>2023-08-25T10:40:48+0100</time>
                <jobCodes>
                    <jobCode>
                        <jobCodeId>1</jobCodeId>
                        <jobCategoryId>1</jobCategoryId>
                    </jobCode>
                    <jobCode>
                        <jobCodeId>2</jobCodeId>
                        <jobCategoryId>2</jobCategoryId>
                    </jobCode>
                </jobCodes>
                <timecards/>
            </clocking>

        Assumes that the existing clocking tag is already set up and valid.
        """
        clockingTag = self.__clocking.getClockingTag()

        for page in self.pages:
            if hasattr(page, 'getClockingXml'):
                pageClockingXml = page.getClockingXml()
                if pageClockingXml is not None:
                    clockingTag.append(pageClockingXml)


    def __sendAttestationResponse(self):
        transactionXmlStr = self.__clocking.getTransaction(self.data['Emp'])

        xmlStr = serverAction.buildSendAttestationResponseXml(transactionXmlStr, self.data['Emp'].getEmpID())
        serverResponse = serverAction.makeRequest(serverAction.ACTION_SENDATTESTATIONRESPONSE, xmlStr)

        if serverResponse.status != serverAction.SERVERSTATUS_SUCCESS:
            log.err('No response returned')
            onlineState.setIsOnline(False)
            self.setResultID(itg.ID_OK)


class _ShiftEndDialog(itg.Dialog):
    """Checks whether the user is ending their shift""" 

    def onCreate(self):
        super(_ShiftEndDialog, self).onCreate()
        view = itg.MsgBoxView()
        view.setText(_('Are you ending your shift?'))
        view.setButton(0, _('YES'), itg.ID_YES, self.onClick)
        view.setButton(1, _('NO'), itg.ID_NO, self.onClick)
        view.setButton(2, _('Cancel'), itg.ID_CANCEL, self.cancel)
        self.addView(view)

    def skip(self):
        # Skip this dialog if the clocking does not include Timecards
        param = self.data['Clocking']
        if param.requireTimecardApproval():
            return False
        else:
            self.data['ShiftEndStatus'] = False
            return True
        
    def onClick(self, btnID):
        # ShiftEndStatus will determine whether or not Timecards should be
        # displayed at the end of the Punch process
        if btnID == itg.ID_YES:
            self.data['ShiftEndStatus'] = True
        else:
            self.data['ShiftEndStatus'] = False
        self.quit(itg.ID_OK)

class _OnlineSchedulesDialog(itg.Dialog):
    """Verifies that the user is within their shift time""" 

    def __init__(self):
        super(_OnlineSchedulesDialog, self).__init__()
        view = itg.MsgBoxView()
        view.setText(_('No active online schedule found'))
        view.setButton(0, _('Exit'), itg.ID_CANCEL, self.quit)
        self.addView(view)

    def __checkLastPunchType(self, clocking, scheduleData):
        """Returns True if the Last Punch Type matches any of the clocking types specified
        in the restrictions and therefore the Last Punch should be checked"""
        punchType = scheduleData.lastPunch.punchType
        restrictedPunchTypesStr = clocking.getRestrictions().lastClockingType.lower()
        restrictedPunchTypes = restrictedPunchTypesStr.split(',')
        log.dbg('Check Last Punch: Punch Types checked for Last Punch: "%s"' % restrictedPunchTypesStr)
        if punchType in restrictedPunchTypes or ('*' in restrictedPunchTypes):
            log.dbg('Check Last Punch: Punch type of "%s" must be checked' % punchType)
            return True
        else:
            log.dbg('Check Last Punch: Punch type of "%s" does not need to be checked' % punchType)
            return False
        
    def __checkLastPunch(self, clocking, clockingTime, scheduleData):
        """Checks that there has been enough time since the employee's last punch"""
        if scheduleData.lastPunch is None:
            log.dbg('Check Last Punch: No Last Punch found in Punch Restrictions response')
            return True
        if not clocking.checkLastPunch():
            log.dbg('Check Last Punch: Last Punch check not specified in buttons.xml')
            return True
        if not self.__checkLastPunchType(clocking, scheduleData):
            return True
        minMinutes = clocking.getMinimumElapsedMinutes()
        # Convert the clocking date/time and the last punch date/time to actual datetime instances
        # Assume that both are in 'yyyy-mm-ddThh:ss:mm' format (they had better be!)
        actualClockTime = datetime.datetime.strptime(clockingTime[:19], '%Y-%m-%dT%H:%M:%S')
        actualLastPunchTime = datetime.datetime.strptime(scheduleData.lastPunch.punchTime[:19], '%Y-%m-%dT%H:%M:%S')
        delta = actualClockTime - actualLastPunchTime
        seconds_in_day = 24 * 60 * 60
        (minutes, seconds) = divmod(delta.days * seconds_in_day + delta.seconds, 60)
        log.dbg('Check Last Punch: Last Punch was %d minutes %d seconds ago' % (minutes, seconds))
        if minutes < minMinutes:
            view = self.getView()
            if minutes == 0:
                view.setText('Last punch was only %d seconds ago' % seconds)
            else:
                view.setText('Last punch was only %d minutes ago' % minutes)
            return False
        else:
            return True

    def __isEmployeeAllowedToClock(self, scheduleResultData, clocking, clockingTimeStr):
        view = self.getView()

        # Check for Supervisor Override
        if scheduleResultData.supervisorOverrideActive:
            log.dbg('Punch Restrictions: Supervisor Schedule Override is active')
            return True

        # Check for Health Attest
        if clocking.getRestrictions().checkHealthAttest:
            if scheduleResultData.hasPositiveHealthAttest:
                log.dbg('Health Attest check passed')
            else:
                log.dbg('Health Attest failed')
                view.setText(_('Health Attest failed'))
                return False

        # Check Last Punch
        if not self.__checkLastPunch(clocking, clockingTimeStr, scheduleResultData):
            return False

        # If Schedule is ok
        if not self.__isScheduleOK(scheduleResultData, clocking, clockingTimeStr):
            view.setText(_('No active online schedule found'))
            return False

        return True

    def __isScheduleOK(self, scheduleResultData, clocking, clockingTimeStr):
        earlyMins = datetime.timedelta(minutes=clocking.getEarlyStartMins())
        lateMins = datetime.timedelta(minutes=clocking.getLateEndMins())
        scheduleConfiguredOnSameDay = 0
        for schedule in scheduleResultData.schedules:
            startTime = datetime.datetime.strptime(schedule.startDateTime[:19], '%Y-%m-%dT%H:%M:%S')
            endTime = datetime.datetime.strptime(schedule.endDateTime[:19], '%Y-%m-%dT%H:%M:%S')
            clockingTime = datetime.datetime.strptime(clockingTimeStr[:19], '%Y-%m-%dT%H:%M:%S')
            # Adjust for early start/late end
            startTime = startTime - earlyMins
            endTime = endTime + lateMins
            if (clockingTime >= startTime and clockingTime <= endTime):
                return True
            if not clocking.getRestrictions().strictOnlineScheduleCheck:
                if (isSameDay(clockingTime, startTime) or isSameDay(clockingTime, endTime)):
                    scheduleConfiguredOnSameDay += 1

        if not clocking.getRestrictions().strictOnlineScheduleCheck and scheduleConfiguredOnSameDay == 0:
            return True
        else:
            return False

    def __checkSchedule(self):
        log.dbg('Checking Online Schedules')
        clocking = self.data['Clocking']

        # Build the transaction XML from the clocking tag
        clockingTag = clocking.getClockingTag()
        actionType = clocking.getActionType()
        clockingTimeStr = timeUtils.getXMLTimestampNow()
        if actionType is not None:
            ET.SubElement(clockingTag, 'actionType').text = actionType
        if not clocking.isOnlineClocking():
            ET.SubElement(clockingTag, 'offline');
        ET.SubElement(clockingTag, 'time').text = clockingTimeStr
        transactionXmlStr = transaction.createTransactionData(getAppSetting('clksrv_id'), clocking.getClockingTag(), self.data['Emp'])

        # Retrieve the Punch Restrictions from the server
        employeeID = self.data['Emp'].getEmpID()
        xmlStr = serverAction.buildPunchRestrictionsRequestXml(transactionXmlStr, employeeID)
        serverResponse = serverAction.makeRequest(serverAction.ACTION_GETPUNCHRESTRICTIONS, xmlStr)

        if serverResponse is not None and serverResponse.status == serverAction.SERVERSTATUS_SUCCESS:
            scheduleResultData = serverAction.ScheduleResultData(serverResponse.resultElement, 'en')
            if self.__isEmployeeAllowedToClock(scheduleResultData, clocking, clockingTimeStr):
                self.setResultID(itg.ID_OK)
            else:
                self.setResultID(itg.ID_CANCEL)
        else:
            log.err('No response returned from server')
            onlineState.setIsOnline(False)
            restrictions = clocking.getRestrictions()
            if restrictions.onlineOnly:
                log.err('Server not available. Please try again later')
                self.setResultID(itg.ID_OK)
            else:
                log.err('Server not available. By-passing schedule check.')
                self.setResultID(itg.ID_OK)

    def skip(self):
        clocking = self.data['Clocking']
        restrictions = clocking.getRestrictions()
        if restrictions.enabled and restrictions.hasOnlineElement and onlineState.isOnline():
            itg.waitbox(_('Checking Schedules. Please wait'), self.__checkSchedule)
            if self.getResultID() == itg.ID_OK:
                self.data['OnlineSchedulesCompleted'] = True
                return True
            return False
        else:
            return True

class _OfflineSchedulesDialog(itg.Dialog):
    """Verifies that the user is within their shift time""" 

    def __init__(self):
        super(_OfflineSchedulesDialog, self).__init__()
        view = itg.MsgBoxView()
        view.setText(_('No active offline schedule found'))
        view.setButton(0, _('Exit'), itg.ID_CANCEL, self.quit)
        self.addView(view)

    def __checkSchedule(self):
        log.dbg('Checking Offline Schedules')
        clocking = self.data['Clocking']
        
        empID = self.data['Emp'].getEmpID()
        clockingTimeStr = timeUtils.getXMLTimestampNow()
        tblSchedules = getAppSchedules()
        scheduleList = tblSchedules.getSchedulesByEmpID(empID)
        for schedule in scheduleList:
            # Adjust for early start/late end
            startTime = datetime.datetime.strptime(schedule['startDateTime'][:19], '%Y-%m-%dT%H:%M:%S')
            endTime = datetime.datetime.strptime(schedule['endDateTime'][:19], '%Y-%m-%dT%H:%M:%S')
            clockingTime = datetime.datetime.strptime(clockingTimeStr[:19], '%Y-%m-%dT%H:%M:%S')
            if (clockingTime >= startTime and clockingTime <= endTime):
                log.dbg('Schedule passed')
                self.setResultID(itg.ID_OK)
                return True
            if not clocking.getRestrictions().strictOnlineScheduleCheck:
                if (isSameDay(clockingTime, startTime) or isSameDay(clockingTime, endTime)):
                    self.setResultID(itg.ID_OK)
                    log.dbg('Schedule passed')
                    return True
        log.dbg('Schedule failed')
        return False
        
    def skip(self):
        restrictions = self.data['Clocking'].getRestrictions()
        if restrictions.enabled and restrictions.hasOfflineElement and not self.data['OnlineSchedulesCompleted']:
            return self.__checkSchedule()
        else:
            return True

class _QuestionnaireDialog(itg.Dialog):
    """Displays a questionnaire for the user"""
    
    def __init__(self):
        super(_QuestionnaireDialog, self).__init__()
        view = itg.MsgBoxView()
        view.setText(_('Questionnaire: Not yet implemented'))
        view.setButton(0, _('OK'), itg.ID_OK, self.quit)
        view.setButton(1, _('Cancel'), itg.ID_CANCEL, self.quit)
        self.addView(view)
        
    def skip(self):
        """Skip. Not yet implemented"""
        return True

