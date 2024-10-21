# -*- coding: utf-8 -*-

import datetime
import xml.etree.cElementTree as ET

import itg
import webClient
from applib.gui import msg
from applib.utils import timeUtils
from engine import dynButtons, acceptMsgDlg
import miscUtils


class TipsDialog(itg.WizardDialog):

    def __init__(self, emp, maxAmount, selectDate):
        super(TipsDialog, self).__init__()
        self.__emp = emp
        self.__maxAmount = maxAmount
        self.__selectDate = selectDate

    def run(self):
        if self.__selectDate:
            pages = (_SelectDateDialog(),
                     _TipAmountDialog(),
                     _FinishDialog())
        else:
            pages = (_TipAmountDialog(),
                     _FinishDialog())

        # apply shared dictionary
        data = {
            'Emp': self.__emp,
            'Date': None,
            'Amount': '1',
            'MaxAmount': self.__maxAmount,
            'SelectDate': self.__selectDate
        }
        for p in pages:
            p.data = data
        # run wizard
        return self._runWizard(pages)


class _SelectDateDialog(itg.Dialog):
    data = {}

    def onCreate(self):
        view = itg.CalendarView(_('Select Tip date'), fmt=miscUtils.getDateFormat(), firstWeekDay=miscUtils.getFirstDayOfWeek())
        view.setButton(0, _('Next'), itg.ID_OK, cb=self.__onNext)
        view.setButton(1, _('Cancel'), itg.ID_CANCEL, cb=self.cancel)
        self.addView(view)

    def __onNext(self, btnID):
        selDate = self.getView().getDate()
        today = datetime.datetime.today().date()
        if (selDate < today):
            itg.msgbox(itg.MB_OK, _('Please select a date in the future!'))
            self.getView().setDate(datetime.datetime.today())
        else:
            self.data['Date'] = selDate
            self.quit(btnID)


class _TipAmountDialog(itg.Dialog):
    data = {}

    def onCreate(self):
        view = itg.NumberInputView(_('Enter tip amount'))
        view.setButton(0, _('Next'), itg.ID_NEXT, cb=self.__onNext)
        view.setButton(1, _('Back'), itg.ID_BACK, cb=self.quit)
        view.setButton(2, _('Cancel'), itg.ID_CANCEL, cb=self.cancel)
        view.setValue('')
        self.addView(view)

    def __onNext(self, btnID):
        try:
            amount = int(self.getView().getValue())
        except:
            amount = 0

        if amount < 1 or (0 < self.data['MaxAmount'] < amount):
            itg.msgbox(itg.MB_OK,
                       _('Tip amount entered must be in the range 1.. %d!') % self.data['MaxAmount'])
        else:
            self.data['Amount'] = amount
            self.quit(btnID)


class _FinishDialog(itg.Dialog):
    data = {}

    def __init__(self):
        """ Create dialog."""
        super(_FinishDialog, self).__init__()
        view = itg.MsgBoxView()
        view.setText('Uh, now how did that happened?!?!?')
        view.setButton(0, _('OK'), itg.ID_OK, cb=self.onOK)
        view.setButton(1, _('Back'), itg.ID_BACK, cb=self.quit)
        view.setButton(2, _('Cancel'), itg.ID_CANCEL, cb=self.cancel)
        self.addView(view)
        self.disableTimeout()

    def onRefreshData(self):
        if self.data["SelectDate"]:
            formatData = {'amount': self.data['Amount'], 'date': self.data['Date'].strftime('%x')}
            self.getView().setText(_('Tip %(amount)s on %(date)s?') % formatData)
        else:
            formatData = {'amount': self.data['Amount']}
            self.getView().setText(_('Tip %(amount)s') % formatData)

    def onOK(self, btnID):
        self.__sendTip()
        self.quit(btnID)

    def __sendTip(self):
        try:
            transactions = webClient.getAppTransactions()
            # check transaction buffer
            if not transactions.hasSpace():
                raise Exception(_('Transaction buffer full!'))
            # create XML
            tipTag = ET.Element('tips')

            ET.SubElement(tipTag, 'time').text = timeUtils.getXMLTimestampNow()
            if self.data["SelectDate"]:
                ET.SubElement(tipTag, 'tipsDate').text = '%s' % self.data['Date']
            ET.SubElement(tipTag, 'amount').text = '%s' % self.data['Amount']

            transactions.addTransaction(tipTag, self.data['Emp'])
        except Exception as e:
            msg.failMsg(_('Error sending tip. %s') % e)
        else:
            acceptMsgDlg.acceptMsg(_('Your Tip has been accepted.'), acceptReader=True)


#
#
# Support functions for dynamic buttons
#
#
class TipsAction(dynButtons.Action):

    def getName(self):
        return 'tips'

    def getButtonText(self, actionParam, employee, languages):
        return _('Tips')

    def getDialog(self, actionParam, employee, languages):
        if (hasattr(actionParam, 'getInteger')):
            maxAmount = actionParam.getInteger('maxAmount', 0)
        else:
            maxAmount = 0

        if (hasattr(actionParam, 'getInteger')):
            selectDate = actionParam.getXMLElement('selectDate') is not None
        else:
            selectDate = False

        return TipsDialog(employee, maxAmount, selectDate)

    def isEmployeeRequired(self, actionParam):
        return True

    def getXsd(self):
        return """
            <xs:complexType>
                <xs:all>
                    <xs:element name="selectDate" minOccurs="0" />
                    <xs:element name="maxAmount" minOccurs="0" type="xs:integer" />
                </xs:all>
            </xs:complexType>
        """

    def getHelp(self):
        return """
        Tip.

        This action sends a tip request after prompting for 
        a start-date and tip amount. The tip request is sent as 
        a transaction to the configured Custom Exchange server.
        Optionally, the maximum tip allowed to accepted can be 
        configured with the *maxAmount* element.  

        Example::

            <button>
                <pos>1</pos>
                <action>
                    <tips>
                        <selectDate/>
                        <maxAmount>5</maxAmount>
                    </tips>
                </action>
            </button>

        """


def loadPlugin():
    dynButtons.registerAction(TipsAction())
