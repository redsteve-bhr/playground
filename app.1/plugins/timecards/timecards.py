# -*- coding: utf-8 -*-
#
# Copyright 2023 Grosvenor Technology
#
import xml.etree.cElementTree as ET

import itg
import log
import miscUtils
import attestation
import webClient
from applib.gui import msg
from applib.utils import timeUtils
from engine import acceptMsgDlg
from webClient import serverAction

class TimecardStatus:
    """Pseudo-enumeration of timecard status values"""
    ACCEPTED = 'accepted'
    DECLINED = 'declined'
    CLEARED  = 'cleared'
    CANCEL   = 'none'
    SKIP     = 'skipped'
    
class Timecard:
    """Simple class for holding timecard data"""
    
    def __init__(self, empID, cardID, title='Timecard', lines=[]):
        self.empID = empID
        self.cardID = cardID
        self.title = title
        self.status = None
        self.lines = lines
        self.reasons = [] # Must be populated if Timecard is declined

class TimecardDialog(itg.WizardDialog):
    """Allows the user to approve their timecards"""

    data = {}

    def __init__(self):
        super(TimecardDialog, self).__init__()
        self.cards = []

    def run(self):
        if self.data['IsStandalone']:
            itg.waitbox(_('Retrieving Timecards. Please wait'), self.__getTimecardsStandalone)

        pages = []
        for card in self.cards:
            pages.append(_TimecardDisplayDialog(card, self.data))
            pages.append(_TimecardApprovalDialog(card, self.data))
            pages.append(_TimecardReasonsDialog(card, self.data))

        self._runWizard(pages)
        resID = self.getResultID()

        if self.data['IsStandalone']:
            # not part of a clocking so just submit the transaction
            self.__doStandAloneTimecard()
        else:
            # Flag the clocking process to send the attestation response.
            self.data['SendAttestationResponse'] = True

        return resID

    def __getTimecardsStandalone(self):
        # Retrieve the Timecards from the server
        employeeID = self.data['Emp'].getEmpID()

        xmlStr = serverAction.buildCatchupTimecardsRequestXml(employeeID)
        serverResponse = serverAction.makeRequest(serverAction.ACTION_FINDCATCHUPTIMECARDS, xmlStr)

        if serverResponse is not None:
            self.__parseTimecardsFromServerAction(serverResponse)

    def __getTimecards(self):
        """Retrieves the timecards from the server. Note that this is called 
        from the `skip()` method"""

        # Build the transaction XML from the clocking tag
        clocking = self.data['Clocking']
        transactionXmlStr = clocking.getTransaction(self.data['Emp'])

        # Retrieve the Timecards from the server
        employeeID = self.data['Emp'].getEmpID()

        xmlStr = serverAction.buildStartAttestationRequestXml(transactionXmlStr, employeeID)
        serverResponse = serverAction.makeRequest(serverAction.ACTION_STARTATTESTATION, xmlStr)

        if serverResponse is not None:
            self.__parseTimecardsFromServerAction(serverResponse)


    def __parseTimecardsFromServerAction(self, serverResponse):
        # Parse the response and store any time cards in the self.cards list
        cardElements = serverResponse.resultElement.findall('timecards/timecard')

        if len(cardElements) == 0:
            log.warn("No timecards found in server response")
        empID = serverResponse.resultElement.find('timecards/empID')
        if empID is None:
            log.err("No EmpID found in server response")

        self.cards = []
        employeeID = self.data['Emp'].getEmpID()
        employeeLanguage = self.data['Emp'].getLanguage()

        for card in cardElements:
            cardID = miscUtils.getElementText(card, 'id')
            title = miscUtils.getElementText(card, 'title', language=employeeLanguage)
            lines = card.find('lines')
            if lines is None:
                log.err("No lines found in timecard")
            else:
                self.cards.append(Timecard(employeeID, cardID, title, [
                    miscUtils.getOptionForLanguage(line, language=employeeLanguage) for line in lines
                ]))
        if len(self.cards) > 0:
            self.setResultID(itg.ID_OK)
        else:
            self.setResultID(itg.ID_NEXT)


    def skip(self):
        # Only show this dialog at the end of a shift
        if self.data['ShiftEndStatus'] == False:
            return True
        # Retrieve the timecards. Skip this dialog if none can be found
        clocking = self.data['Clocking']
        if clocking.requireTimecardApproval():
            itg.waitbox(_('Retrieving Timecards. Please wait'), self.__getTimecards)
            if self.getResultID() == itg.ID_OK:
                return False
            return True
        else:
            return True

    def __doStandAloneTimecard(self):
        try:
            transactions = webClient.getAppTransactions()
            if not transactions.hasSpace():
                raise Exception(_('Transaction buffer full!'))

            timecardsClockingXml = self.__getTimecardsClockingXml()

            if timecardsClockingXml is not None:
                transactions.addTransaction(timecardsClockingXml, self.data['Emp'])
                acceptMsgDlg.acceptMsg(_('Your Timecard Catchup has been confirmed.'), acceptReader=True)

        except Exception as e:
            msg.failMsg(_('Error confirming Timecard Catchup. %s') % e)

    def __getTimecardsClockingXml(self):
        clockingTag = ET.Element('clocking')

        ET.SubElement(clockingTag, 'time').text = timeUtils.getXMLTimestampNow()
        ET.SubElement(clockingTag, 'type')

        timecardTag = self.getClockingXml()
        if timecardTag is not None:
            clockingTag.append(timecardTag)
            return clockingTag

    def getClockingXml(self):
        """
            <timecards>
                <timecard>
                    <id type="accepted">3</id>
                </timecard>
            </timecards>
        """
        # Make sure at least one timecard has been filled out
        filledCards = list(filter(lambda t: t.status is TimecardStatus.ACCEPTED or t.status is TimecardStatus.DECLINED, self.cards))

        if len(filledCards) > 0:
            tag = ET.Element('timecards')
            for card in filledCards:
                cardElement = ET.SubElement(tag, 'timecard')
                idElement = ET.SubElement(cardElement, 'id')
                idElement.text = '%s' % card.cardID
                idElement.set('type', card.status)
                if len(card.reasons) > 0:
                    reasonElement = ET.SubElement(cardElement, 'reasons')
                    for reason in card.reasons:
                        ET.SubElement(reasonElement, 'reason').text = str(reason)
            return tag

class _TimecardDisplayDialog(itg.Dialog):
    """Displays the details of a single Timecard for the user to approve"""

    def __init__(self, card, data):
        super(_TimecardDisplayDialog, self).__init__()
        self.card = card
        self.data = data
        view = itg.MsgBoxView()
        view.setText(self.getTimecardText(card))
        view.setButton(0, _('Continue'), itg.ID_OK, self.__onOK)
        view.setButton(1, _('Back'), itg.ID_BACK, self.back)
        view.setButton(2, _('Skip'), itg.ID_IGNORE, self.__onSkip)
        
        self.addView(view)
        
    def getTimecardText(self, card):
        text = card.title + "\n\n"
        for line in card.lines:
            text += line + "\n"
        return text

    def __onOK(self, btnID):
        self.quit(itg.ID_NEXT)
        
    def __onSkip(self, btnID):
        self.card.status = TimecardStatus.SKIP
        self.quit(itg.ID_NEXT)
        
class _TimecardApprovalDialog(itg.Dialog):
    """Displays the details of a single Timecard for the user to approve"""

    def __init__(self, card, data):
        super(_TimecardApprovalDialog, self).__init__()
        self.card = card
        self.data = data
        self.attest = attestation.Attestation(self.data['Emp'])
        view = itg.MsgBoxView()
        view.setText(self.attest.prompt)
        view.setButton(0, self.attest.agreeButtonText, itg.ID_OK, self.__onAgree)
        view.setButton(1, self.attest.disagreeButtonText, itg.ID_NO, self.__onDisagree)
        view.setButton(2, _('Cancel'), itg.ID_CANCEL, self.back)
        self.addView(view)
        
    def __onAgree(self, btnID):
        self.card.status = TimecardStatus.ACCEPTED
        self.quit(itg.ID_NEXT)
        
    def __onDisagree(self, btnID):
        self.card.status = TimecardStatus.DECLINED
        self.quit(itg.ID_NEXT)
        
    def skip(self):
        if self.card.status == TimecardStatus.SKIP:
            return True
        else:
            return False
        
class _TimecardReasonsDialog(itg.Dialog):
    """Displays a list of reasons for the user to select from it they have
    declined the approval (see _TimecardApprovalDialog)
    """

    def __init__(self, card, data):
        super(_TimecardReasonsDialog, self).__init__()
        self.card = card
        self.reasons = set()
        self.data = data
        self.attest = attestation.Attestation(self.data['Emp'])
        view = itg.MenuView()
        for reason in self.attest.reasons:
            view.appendRow(reason.text, checked=False, data=reason, cb=self.__onToggleReason)
        view.appendRow(_('Confirm Selection'), cb=self.__onConfirm)
        self.addView(view)

    def __onToggleReason(self, pos, row):
        isChecked = not row['checked']
        reason = row['data']
        menu = self.getView()
        menu.changeRow(pos, 'checked', isChecked)
        if isChecked:
            self.reasons.add(reason.reasonID)
        else:
            self.reasons.discard(reason.reasonID)

    def __onConfirm(self, pos, row):
        for reason in self.reasons:
            self.card.reasons.append(reason)
        self.quit(itg.ID_OK)
        
    def skip(self):
        if self.card.status == TimecardStatus.DECLINED:
            return False
        else:
            return True


