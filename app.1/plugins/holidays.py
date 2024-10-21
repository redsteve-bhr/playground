# -*- coding: utf-8 -*-

import itg
import datetime
import webClient
import xml.etree.cElementTree as ET
from engine import dynButtons, acceptMsgDlg
from applib.gui import msg
from applib.utils import timeUtils
import miscUtils


class BookHolidayDialog(itg.WizardDialog):
    
    def __init__(self, emp, maxDaysAllowed):
        super(BookHolidayDialog, self).__init__()
        self.__emp = emp
        self.__maxDaysAllowed = maxDaysAllowed
    
    def run(self):
        pages = ( _SelectDateDialog(),
                  _NumberOfDaysDialog(),
                  _FinishDialog())
    
        # apply shared dictionary
        wizDat = { 'Emp'            : self.__emp,
                   'Date'           : None, 
                   'Days'           : '1',
                   'MaxDaysAllowed' : self.__maxDaysAllowed }
        for p in pages:
            p.data = wizDat
        # run wizard
        return self._runWizard(pages)
    

class _SelectDateDialog(itg.Dialog):
    
    def onCreate(self):
        view = itg.CalendarView(_('Select holiday start date'), fmt=miscUtils.getDateFormat(), firstWeekDay=miscUtils.getFirstDayOfWeek())
        view.setButton(0, _('Next'), itg.ID_OK, cb=self.__onNext)
        view.setButton(1, _('Cancel'),     itg.ID_CANCEL, cb=self.cancel)
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


class _NumberOfDaysDialog(itg.Dialog):
    
    def onCreate(self):
        view = itg.NumberInputView(_('Enter number of days'))
        view.setButton(0, _('Next'),    itg.ID_NEXT,   cb=self.__onNext)
        view.setButton(1, _('Back'),    itg.ID_BACK,   cb=self.quit)
        view.setButton(2, _('Cancel'),  itg.ID_CANCEL, cb=self.cancel)
        view.setValue('')
        self.addView(view)

    def __onNext(self, btnID):
        try:
            days = int(self.getView().getValue())
        except:
            days = 0

        if (days < 1 or days > self.data['MaxDaysAllowed']):
            itg.msgbox(itg.MB_OK, _('Number of days entered must be in the range 1.. %d!') % self.data['MaxDaysAllowed'])
        else:
            self.data['Days'] = days 
            self.quit(btnID)


        
class _FinishDialog(itg.Dialog):
    
    def __init__(self):
        """ Create dialog."""
        super(_FinishDialog, self).__init__()
        view = itg.MsgBoxView()
        view.setText('Uh, now how did that happened?!?!?')
        view.setButton(0, _('OK'), itg.ID_OK,   cb=self.onOK)
        view.setButton(1, _('Back'),    itg.ID_BACK,   cb=self.quit)
        view.setButton(2, _('Cancel'),  itg.ID_CANCEL, cb=self.cancel)
        self.addView(view)
        self.disableTimeout()

    def onRefreshData(self):
        formatData = { 'days': self.data['Days'], 'date': self.data['Date'].strftime('%x') }
        self.getView().setText(_('Book %(days)s days holiday starting on %(date)s?') % formatData)
        
    def onOK(self, btnID):
        self.__bookHoliday()
        self.quit(btnID)
        
    def __bookHoliday(self):
        try:
            transactions  = webClient.getAppTransactions()
            # check transaction buffer
            if (not transactions.hasSpace()):
                raise Exception(_('Transaction buffer full!'))
            # create XML
            holTag = ET.Element('holidayRequest')
            ET.SubElement(holTag, 'time').text = timeUtils.getXMLTimestampNow()
            ET.SubElement(holTag, 'startDate').text = '%s' % self.data['Date']
            ET.SubElement(holTag, 'numberOfDays').text = '%s' % self.data['Days']
            transactions.addTransaction(holTag, self.data['Emp'])
        except Exception as e:
            msg.failMsg(_('Error booking holiday. %s') % e)
        else:
            acceptMsgDlg.acceptMsg(_('Your holiday has been booked.'), acceptReader=True)

#
#
# Support functions for dynamic buttons
#
#
class BookHolidayAction(dynButtons.Action):
    
    def getName(self):
        return 'ws.holiday.book'
    
    def getButtonText(self, actionParam, employee, languages):
        return _('Holiday')
    
    def getDialog(self, actionParam, employee, languages):
        if (hasattr(actionParam, 'getInteger')):
            maxDaysAllowed = actionParam.getInteger('maxDaysAllowed', 21)
        else:
            maxDaysAllowed = 21
        return BookHolidayDialog(employee, maxDaysAllowed)

    def isEmployeeRequired(self, actionParam):
        return True

    def getXsd(self):
        return """
            <xs:complexType>
                <xs:all>
                    <xs:element name="maxDaysAllowed" minOccurs="0" type="xs:integer" />
                </xs:all>
            </xs:complexType>
        """

    def getHelp(self):
        return """
        Book holiday.

        This action sends a holiday booking request after prompting for 
        a start-date and number of days. The holiday request is sent as 
        a transaction to the configured Custom Exchange server.
        Optionally, the maximum number of days allowed to book can be 
        configured with the *maxDaysAllowed* element.  
        
        Example::
        
            <button>
                <pos>1</pos>
                <action>
                    <ws.holiday.book>
                        <maxDaysAllowed>5</maxDaysAllowed>
                    </ws.holiday.book>
                </action>
            </button>

        """        




def loadPlugin():
    dynButtons.registerAction(BookHolidayAction())






