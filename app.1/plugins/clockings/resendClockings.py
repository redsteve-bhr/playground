# -*- coding: utf-8 -*-
#
# Copyright 2023 Grosvenor Technology
#
import datetime
import itg
import webClient
from engine import dynButtons
from applib.db.sqlTime import sqlTime2MyLocalTime, localTime2SqlTime
import miscUtils


class _TransactionsDialog(itg.Dialog):
    
    def onCreate(self):
        super(_TransactionsDialog, self).onCreate()
        view = itg.MenuView(_('Clockings'))
        self.__populateMenu(view)
        view.setBackButton(_('Back'), self.back)
        self.addView(view)
    
    def collectData(self):
        trans = webClient.getAppTransactions()
        trans.open()
        self.__total        = trans.count()
        self.__totalUnsent  = trans.getNumberUnsent()
        self.__oldestSent   = trans.getOldestSent()
        self.__lastSent     = trans.getLastSent()
        self.__oldestUnsent = trans.getOldestUnsent()
        self.__lastUnsent   = trans.getLastUnsent()
        timeFmt = "%Y-%m-%d %H:%M:%S%z"
        if (self.__oldestSent != None):
            self.__oldestSent = sqlTime2MyLocalTime(self.__oldestSent, timeFmt)
        if (self.__lastSent != None):
            self.__lastSent = sqlTime2MyLocalTime(self.__lastSent, timeFmt)
        if (self.__oldestUnsent != None):
            self.__oldestUnsent = sqlTime2MyLocalTime(self.__oldestUnsent, timeFmt)
        if (self.__lastUnsent != None):
            self.__lastUnsent = sqlTime2MyLocalTime(self.__lastUnsent, timeFmt)
    
    def __populateMenu(self, menu):
        if (not hasattr(self, '__total')):
            self.collectData()
        menu.removeAllRows()
        menu.appendRow(_('Total'),  self.__total, cb=self.__onDetails)
        menu.appendRow(_('Unsent'), self.__totalUnsent, cb=self.__onDetails)
        menu.appendRow(_('Oldest sent'), self.__oldestSent, cb=self.__onDetails)
        menu.appendRow(_('Last sent'), self.__lastSent, cb=self.__onDetails)
        menu.appendRow(_('Oldest unsent'), self.__oldestUnsent, cb=self.__onDetails)
        menu.appendRow(_('Last unsent'), self.__lastUnsent, cb=self.__onDetails)
        
        if self.__lastSent is not None:
            menu.appendRow(_('Re-send transactions'), cb=self.__onResendClockings, hasSubItems=True)
        else:
            menu.appendRow(_('No transactions to re-send'))
    
    def __onDetails(self, pos, row):
        itg.msgbox(itg.MB_OK, '%s: %s' % (row['label'], row['value']))
        
    def __onResendClockings(self, pos, row):
        dlg = _ResendClockingsDialog()
        resID = dlg.run()
        if (resID == itg.ID_NEXT or resID == itg.ID_OK):
            itg.waitbox(_('Collecting data...'), self.collectData)
            self.__populateMenu(self.getView())


class _ResendClockingsDialog(itg.WizardDialog):

    def run(self):
        pages = ( _WelcomeDialog(),
                  _SelectDateDialog(),
                  _SelectTimeDialog(),
                  _ConfirmDialog(),                  
                  _MarkAsSentDialog(),                  
                  _FinishDialog() )
        trans = webClient.getAppTransactions()
        trans.open()
        sharedData = { 'date': None,
                       'time': None,
                       'trans': trans}
        for p in pages:
            p.sharedData = sharedData
        self._runWizard(pages)
        return self.getResultID()


class _WelcomeDialog(itg.Dialog):

    def onCreate(self):
        super(_WelcomeDialog, self).onCreate()
        view = itg.MsgBoxView()
        view.setText(_('Please enter date and time from which all sent transactions will be marked as unsent.'))
        view.setButton(0, _('Next'), itg.ID_NEXT, self.quit)
        view.setButton(1, _('Cancel'), itg.ID_CANCEL, self.quit)
        self.addView(view)


class _SelectDateDialog(itg.Dialog):
    
    def __init__(self):
        super(_SelectDateDialog, self).__init__()
        view = itg.CalendarView(_('Select punch date'), fmt=miscUtils.getDateFormat(), firstWeekDay=miscUtils.getFirstDayOfWeek())
        view.setButton(0, _('Next'), itg.ID_NEXT, self.__onNext)
        view.setButton(1, _('Cancel'), itg.ID_CANCEL, self.cancel)        
        self.addView(view)

    def __onNext(self, btnID):
        self.sharedData['date'] = self.getView().getDate()
        self.quit(btnID)
               

class _SelectTimeDialog(itg.Dialog):
    
    def __init__(self):
        super(_SelectTimeDialog, self).__init__()
        view = itg.TimeInputView(_('Enter Time'))
        view.setButton(0, _('Next'), itg.ID_NEXT, self.__onNext)
        view.setButton(1, _('Back'), itg.ID_BACK, self.back)        
        view.setButton(2, _('Cancel'), itg.ID_CANCEL, self.cancel)
        self.addView(view)
        
    def __onNext(self, btnID):
        self.sharedData['time'] = self.getView().getTime()
        self.quit(btnID)        
        

class _ConfirmDialog(itg.PseudoDialog):
    
    def run(self):
        trans = self.sharedData['trans']
        localTime = datetime.datetime.combine(self.sharedData['date'], self.sharedData['time'])
        sqlTime = localTime2SqlTime(localTime)
        
        (_resID, count) = itg.waitbox(_('Collecting data...'), trans.getNumberOfSentTransactionsAfter, (sqlTime,))
        self.sharedData['count'] = count
        self.sharedData['sqlTime'] = sqlTime
        if (count == 0):
            resID = itg.msgbox(itg.MB_OK_CANCEL, _('No sent transactions after %s.') % localTime)
            if (resID == itg.ID_OK):
                return itg.ID_BACK
            return resID
            
        resID = itg.msgbox(itg.MB_YES_NO_CANCEL, _('Mark transactions after %(date)s (%(numTrans)s transactions) as unsent?') % 
                           { 'date': localTime, 'numTrans': count })
        if (resID == itg.ID_YES):
            return itg.ID_NEXT
        elif (resID == itg.ID_NO):
            return itg.ID_BACK
        return resID


class _MarkAsSentDialog(itg.PseudoDialog):
    
    def run(self):
        trans = self.sharedData['trans']
        count = self.sharedData['count']
        sqlTime = self.sharedData['sqlTime']
        itg.waitbox(_('Marking %d transactions as unsent...') % count, trans.markAsUnsentAfter, (sqlTime,))
        return itg.ID_NEXT


class _FinishDialog(itg.Dialog):

    def onCreate(self):
        super(_FinishDialog, self).onCreate()
        count = self.sharedData['count']
        view = itg.MsgBoxView()
        view.setText(_('%s transactions have been marked as unsent and will be re-sent from within the application.') % count)
        view.setButton(0, _('OK'), itg.ID_NEXT, self.quit)
        self.addView(view)


class ResendClockingsDialog(itg.PseudoDialog):
    
    def run(self):
        dlg = _TransactionsDialog()
        itg.waitbox(_('Collecting data...'), dlg.collectData)
        resID = dlg.run()
        self.setResultID(resID)
        return resID


class ResendClockingsAction(dynButtons.Action):
    
    def getName(self):
        return 'resend.clockings'
    
    def getButtonText(self, actionParam, employee, languages):
        return _('Resend Clockings')
    
    def getDialog(self, actionParam, employee, languages):
        return ResendClockingsDialog()

    def getHelp(self):
        return """
        Replay sent transactions.

        This action brings up a dialog which lets the user re-send already
        sent transactions.
        
        This action is used by the application setup.
        
        .. important::
            This action is best used from within the application 
            setup because it may interfere with the transaction sending thread
            otherwise.
         
        """        

