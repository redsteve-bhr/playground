# -*- coding: utf-8 -*-
#
# Copyright 2023 Grosvenor Technology
#
#
import emps
import itg
from plugins.transfers import tblJobCodes, tblJobCategories
import log
import miscUtils
import webClient
from applib.gui import msg
from applib.utils import timeUtils
from engine import acceptMsgDlg
import xml.etree.cElementTree as ET


class TransferDialog(itg.WizardDialog):

    data = {}
    sharedData = {}


    def __init__(self):
        super(TransferDialog, self).__init__()
        self.__emp = None
        self.__promptLevels = None
        self.__isStandalone = None
        self.sharedData = {
            'Results': [],
        }


    def run(self):
        self.__emp = self.data['Emp']
        self.__promptLevels = self.data['PromptLevels']
        self.__isStandalone = self.data['IsStandalone']

        pages = []
        jobCategories = tblJobCategories.getAppJobCategories()

        if len(self.__promptLevels) == 0:
            allJobCategories = jobCategories.getAllJobCategories()

            # Get all unique levels
            self.__promptLevels = set(list(map(lambda jobCategory: jobCategory['Level'], allJobCategories)))

        # The list may be unsorted (level 4 could be before level 2 causing issues in the flow).
        sortedPromptLevels = sorted(self.__promptLevels, key=int)

        jobCats = list(map(lambda l: jobCategories.getJobCategoryByLevel(l), sortedPromptLevels))

        if len(jobCats) == 0:
            itg.msgbox(itg.MB_OK, _('No Job Categories found'))
            return itg.ID_CANCEL

        for jobCategory in jobCats:
            levelDiag = _TransferLevelDialog(self.__emp, jobCategory)
            pages.append(levelDiag)

        pages.append(_TransferConfirmDialog(self.__emp))

        for page in pages:
            page.sharedData = self.sharedData

        self._runWizard(pages)

        resID = self.getResultID()
        if resID == itg.ID_OK and self.__isStandalone:
            # not part of a clocking so just submit the transaction
            self.__doStandAloneTransfer()
        else:
            pass  # Results in punch restrictions will be obtained through the shared data Results entry.

        return self.getResultID()

    def __doStandAloneTransfer(self):
        try:
            transactions = webClient.getAppTransactions()
            if not transactions.hasSpace():
                raise Exception(_('Transaction buffer full!'))

            transactions.addTransaction(self.__getJobCodesClockingXml(), self.__emp)

        except Exception as e:
            msg.failMsg(_('Error confirming Transfer. %s') % e)
        else:
            acceptMsgDlg.acceptMsg(_('Your Transfer has been confirmed.'), acceptReader=True)

    def __getJobCodesClockingXml(self):
        clockingTag = ET.Element('clocking')

        ET.SubElement(clockingTag, 'time').text = timeUtils.getXMLTimestampNow()
        ET.SubElement(clockingTag, 'type').text = self.data['Type']

        jobCodeTag = self.getClockingXml()
        clockingTag.append(jobCodeTag)

        return clockingTag

    def getClockingXml(self):
        # Make sure at least one level has been completed
        if len(self.sharedData['Results']) > 0:
            jobCodesTag = ET.Element('jobCodes')

            for jobCode in self.sharedData['Results']:
                jobCodeTag = ET.SubElement(jobCodesTag, 'jobCode')
                ET.SubElement(jobCodeTag, 'jobCodeId').text = '%s' % jobCode['JobCodeID']
                ET.SubElement(jobCodeTag, 'jobCategoryId').text = '%s' % jobCode['JobCategoryID']

            return jobCodesTag


class _TransferLevelDialog(itg.Dialog):

    sharedData = {}

    def __init__(self, emp, jobCategory):
        super(_TransferLevelDialog, self).__init__()
        self.__emp = emp
        self.__jobCategory = jobCategory

    def onCreate(self):
        super(_TransferLevelDialog, self).onCreate()

        jobCategoryNameTag = ET.fromstring(self.__jobCategory['Name'])
        jobCategoryName = miscUtils.getOptionForLanguage(jobCategoryNameTag, language=self.__emp.getLanguage())

        view = itg.ListView(_('Transfer %s' % jobCategoryName))
        view.setOkButton(_('OK'), self.__onOK)
        view.setBackButton('Back', cb=self.quit)
        view.setCancelButton('Cancel', cb=self.quit)

        # get the job codes for this level and add them to view
        jobCodes = tblJobCodes.getAppJobCodes()

        # if there are home job codes on the employee for this level then put them first in the list
        homeJobCodes = emps.getAppEmpHomeJobCodes().parseToDictList(self.__emp.getEmpID())

        level = self.__jobCategory['Level']

        homeJobCodesForLevel = [j for j in homeJobCodes if j['level'] == level]

        log.dbg('Found %s home job codes for level %s: %s' % (len(homeJobCodesForLevel), level, homeJobCodesForLevel))

        # Try to get the job code from the home job codes and report and errors and remove any Nones (invalid home job code)
        jobCodesForLevel = [j for j in [self.__getJobCodeForHomeJobCode(jobCodes, j) for j in homeJobCodesForLevel] if j is not None]

        for jobCode in jobCodesForLevel:
            # sort out language text
            jobCodeNameTag = ET.fromstring(jobCode['Name'])
            jobCodeName = miscUtils.getOptionForLanguage(jobCodeNameTag, self.__emp.getLanguage())

            jobCode['Name'] = '%s (⌂)' % jobCodeName

        # ensure no duplicates while getting the rest of the job codes from the table
        jobCodeIDsForLevel = [j['JobCodeID'] for j in jobCodesForLevel]

        for jobCode in [dict(jc) for jc in jobCodes.getJobCodesByJobCategoryID(self.__jobCategory['JobCategoryID'])]:
            if jobCode['JobCodeID'] not in jobCodeIDsForLevel:
                # sort out language text
                jobCodeNameTag = ET.fromstring(jobCode['Name'])
                jobCodeName = miscUtils.getOptionForLanguage(jobCodeNameTag, self.__emp.getLanguage())
                jobCode['Name'] = jobCodeName

                jobCodesForLevel.append(jobCode)

        log.dbg('Found %s job codes for level: %s' % (len(jobCodesForLevel), jobCodesForLevel))

        for jobCode in jobCodesForLevel:
            view.appendRow('%s %s' % (jobCode['Code'], jobCode['Name']), jobCode)

        self.addView(view)

    def __getJobCodeForHomeJobCode(self, jobCodes, homeJobCode):
        try:
            if homeJobCode is not None:
                jobCodeId = homeJobCode['jobCodeId']
                jobCode = jobCodes.getJobCode(jobCodeId)
                if jobCode is not None:
                    return dict(jobCode)
                else:
                    raise Exception("No job code found for %s" % jobCodeId)
            else:
                raise Exception("Home job code is None!")
        except Exception as e:
            log.warn("Could not get home job code for employee: %s" % e)
            return None

    def __onOK(self, btnID):
        newJobCode = self.getView().getSelectedRow()['data']
        self.sharedData['Results'].append(newJobCode)
        self.quit(btnID)


class _TransferConfirmDialog(itg.Dialog):

    sharedData = {}

    def __init__(self, emp):
        super(_TransferConfirmDialog, self).__init__()
        self.__emp = emp


    def onCreate(self):
        view = itg.MenuView(_('Transfer Confirm'))
        view.setBackButton('Back',  cb=self.back)
        view.setCancelButton('Cancel',  cb=self.cancel)

        log.dbg('Selected transfer job codes: %s' % str(self.sharedData['Results']))

        # Set the confirm row as a job code with code and name as confirm.
        view.appendRow(_('Confirm'), data={'Code': 'Confirm', 'Name': 'Confirm'}, cb=self.__onMenuItemSelected)

        for jobCode in self.sharedData['Results']:
            view.appendRow('%s %s' % (jobCode['Code'], jobCode['Name']), data=jobCode, cb=self.__onMenuItemSelected)

        self.addView(view)

    def __onMenuItemSelected(self, pos, row):
        # If Confirm is click then continue.
        if row['data']['Code'] == 'Confirm' and row['data']['Name'] == 'Confirm':
            self.quit(itg.ID_OK)
        else:
            pass
