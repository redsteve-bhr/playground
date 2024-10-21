# -*- coding: utf-8 -*-
#
#

import itg
import datetime
import locale
import relaySchedules
from applib.db.database import getAppDB
import updateit

def getDOWShortText(dow):
    if (updateit.get_type() == 'IT5100'):
        length = 2
    else:
        length = 1
    # in range 1..7        
    i = int(dow)
    if (i == 7):
        return unicode(locale.nl_langinfo(locale.DAY_1))[:length] #@UndefinedVariable
    elif (i >= 1 and i <= 6):
        return unicode(locale.nl_langinfo(locale.DAY_1+i))[:length] #@UndefinedVariable
    return '?'


def getDOWSummaryText(dows):
    weekdays = 0
    weekend = 0
    text = ''

    if (updateit.get_type() == 'IT5100'):
        sep = ','
        notused = ''
    else:
        sep = ''
        notused = '-'
        
    # Mon->Sat
    for i in range(1, 6):
        if (str(i) in dows):
            if text != '':
                text += sep
            text += getDOWShortText(i)
            weekdays+=1
        else:
            text += notused

    #Sat
    if ('6' in dows):
        if text != '':
            text += sep
        text += getDOWShortText(6)
        weekend+=1
    else:
        text += notused
    
    # Sun
    if ('7' in dows):
        if text != '':
            text += sep
        text += getDOWShortText(7)
        weekend +=1
    else:
        text += notused
        
    if ((weekdays + weekend) == 7):
        text = 'All days'
    else:
        if (weekend==2 and weekdays==0):
            text = 'Weekend'

    return text
            

def getDateDesc(ddmm):
    fields = ddmm.split('/')
    return '%s %s' % (locale.nl_langinfo(locale.MON_1+int(fields[0])-1), fields[1]) #@UndefinedVariable


def getSummaryDateDesc(ddmm):            
    fields = ddmm.split('/')
    return '%s %s' % (locale.nl_langinfo(locale.MON_1+int(fields[0])-1)[:3], fields[1]) #@UndefinedVariable


class Dialog(itg.Dialog):
    
    def __init__(self):
        super(Dialog, self).__init__()
        self.resultID = None
        self.__relayTimes = relaySchedules.RelaySchedules(getAppDB())
        self.__relayTimes.open()
        view = itg.MenuView(_('Configure relay schedules'))
        view.setBackButton(_('Back'),  cb=self.back)
        self.__updateScreen(view)
        self.addView(view)

    def __updateScreen(self, view):
        view.removeAllRows()
        numRelays = '(%s)' % self.__relayTimes.getNumberOfRelayTimes()
        numOverrides = '(%s)' % self.__relayTimes.getNumberOfOverrides()
        view.appendRow(_('Configure relay times'),     numRelays,   hasSubItems=True, cb=self.__onRelayTimes)
        view.appendRow(_('Configure override periods'), numOverrides,  hasSubItems=True, cb=self.__onRelayOverrides)
    
    def __onRelayTimes(self, pos, row):
        self.runDialog(RelayTimesDialog(), invokeCancel=False)
        self.__updateScreen(self.getView())

    def __onRelayOverrides(self, pos, row):
        self.runDialog(RelayOverridesDialog(), invokeCancel=False)
        self.__updateScreen(self.getView())


class RelayTimesDialog(itg.Dialog):
    
    def __init__(self):
        super(RelayTimesDialog, self).__init__()
        self.resultID = None
        self.__relayTimes = relaySchedules.RelaySchedules(getAppDB())
        self.__relayTimes.open()
        view = itg.MenuView(_('Configure relay times'))
        view.setBackButton(_('Back'),  cb=self.back)
        self.__updateScreen(view)
        self.addView(view)

    def __updateScreen(self, view):
        view.removeAllRows()
        view.appendRow(_('Add relay time'),     '', hasSubItems=True, cb=self.__onSelect)
        rt = self.__relayTimes.getAllRelayTimes()
        for i in rt:
            #view.appendRow(text, 'R%s-%s' % (i['IOBoard'], i['Relay']), text, data=i, cb=self.__onSelect)
            if (updateit.get_type() == 'IT5100'):
                text = '%s -> %s  %s' % (i['StartTime'], i['EndTime'], getDOWSummaryText(i['DOW']))
                view.appendRow(text, 'R%s-%s' % (i['IOBoard'], i['Relay']), data=i, cb=self.__onSelect)
            else:
                text = '%s-%s  %s' % (i['StartTime'], i['EndTime'], getDOWSummaryText(i['DOW']))
                text = text.replace(':', '')
                view.appendRow(text, '', data=i, cb=self.__onSelect)
    
    def __onSelect(self, pos, row):
        if (pos == 0):
            dlg = AddRelayTime(self.__relayTimes)
            self.runDialog(dlg)
            self.__updateScreen(self.getView())
        else:
            dlg = RelaySelectDialog(row['data'])
            if (dlg.run() == itg.ID_OK):
                self.__relayTimes.deleteRelayTimeByRecID(row['data']['RecID'])
                self.__updateScreen(self.getView())

         
class RelaySelectDialog(itg.Dialog):
    
    def __init__(self, rowData):
        super(RelaySelectDialog, self).__init__()
        desc = _('IO board %(board)s relay %(relay)s') % {'board': rowData['IOBoard'], 'relay': rowData['Relay'] }
        desc += '\n%s -> %s\n%s\n' % (rowData['StartTime'], rowData['EndTime'], getDOWSummaryText(rowData['DOW']))
        view = itg.MsgBoxView()
        view.setText(desc)
        view.setButton(0, _('Delete'), itg.ID_OK, self.__onDelete)
        view.setButton(1, _('Back'), itg.ID_BACK, self.back)
        self.addView(view)
        self.disableTimeout()    
        
    def __onDelete(self, btnID):
        self.quit(btnID)

    
class RelayOverridesDialog(itg.Dialog):
    
    def __init__(self):
        super(RelayOverridesDialog, self).__init__()
        self.resultID = None
        self.__relayTimes = relaySchedules.RelaySchedules(getAppDB())
        self.__relayTimes.open()
        view = itg.MenuView(_('Configure override periods'))
        view.setBackButton(_('Back'),  cb=self.back)
        self.__updateScreen(view)
        self.addView(view)

    def __updateScreen(self, view):
        view.removeAllRows()
        view.appendRow(_('Add override period'), '', hasSubItems=True, cb=self.__onSelect)
        ov = self.__relayTimes.getAllOverrides()
        for i in ov:
            text = '%s -> %s' % (getSummaryDateDesc(i['StartDate']), getSummaryDateDesc(i['EndDate']))
            #view.appendRow(text, _('Override period'), text, data=text, cb=self.__onSelect)
            view.appendRow(text, '', data=i, cb=self.__onSelect)

    def __onSelect(self, pos, row):
        if (pos == 0):
            dlg = AddOverrideTime(self.__relayTimes)
            self.runDialog(dlg)
            self.__updateScreen(self.getView())
        else:
            dlg = OverrideSelectDialog(row['data'])
            if (dlg.run() == itg.ID_OK):
                self.__relayTimes.deleteOverrideByRecID(row['data']['RecID'])
                self.__updateScreen(self.getView())

                    
class OverrideSelectDialog(itg.Dialog):
    
    def __init__(self, rowData):
        super(OverrideSelectDialog, self).__init__()
        desc = _('Override period\n%(startDate)s to %(endDate)s') % { 'startDate': rowData['StartDate'], 'endDate': rowData['EndDate'] }
        view = itg.MsgBoxView()
        view.setText(desc)
        view.setButton(0, _('Delete'), itg.ID_OK, self.__onDelete)
        view.setButton(1, _('Back'), itg.ID_BACK, self.back)
        self.addView(view)
        self.disableTimeout()    
        
    def __onDelete(self, btnID):
        self.quit(btnID)
                    
    
class AddRelayTime(itg.WizardDialog):
    
    def __init__(self, relayTimes):
        super(AddRelayTime, self).__init__()
        self.__relayTimes = relayTimes
    
    def run(self):
        pages = ( _StartTimeDialog(),
                  _EndTimeDialog(),
                  _DOWDialog(),
                  _RelayDialog(),
                  _ConfirmDialog())
        # apply shared dictionary
        wizDat = { 'RelaySchedules'   : '',
                   'StartTime'    : '09:00:00', 
                   'EndTime'      : '',
                   'DOW'          : '1,2,3,4,5',      # Mon=1 Sun=7
                   'IOBoard'      : '1',
                   'Relay'        : '1'
         }
        wizDat['RelaySchedules'] = self.__relayTimes
        for p in pages:
            p.data = wizDat
        # run wizard
        self._runWizard(pages)
        return self.getResultID()
    
    
class _StartTimeDialog(itg.Dialog):
    
    def onCreate(self):
        super(_StartTimeDialog, self).onCreate()        
        view = itg.TimeInputView(_('Enter relay on time'))
        view.setButton(0, _('Next'),    itg.ID_NEXT,   cb=self.__onNext)
        view.setButton(1, _('Back'),    itg.ID_BACK,   cb=self.quit)
        view.setButton(2, _('Cancel'),  itg.ID_CANCEL, cb=self.cancel)
        val = datetime.datetime.strptime(self.data['StartTime'], '%H:%M:%S')
        view.setTime(val)
        self.addView(view)
        
    def __onNext(self, btnID):
        startTime = self.getView().getTime()
        self.data['StartTime'] = startTime.strftime('%H:%M:%S') 
        self.quit(btnID)


class _EndTimeDialog(itg.Dialog):
    
    def onCreate(self):
        super(_EndTimeDialog, self).onCreate()
        view = itg.TimeInputView(_('Enter relay off time'))
        view.setButton(0, _('Next'),    itg.ID_NEXT,   cb=self.__onNext)
        view.setButton(1, _('Back'),    itg.ID_BACK,   cb=self.quit)
        view.setButton(2, _('Cancel'),  itg.ID_CANCEL, cb=self.cancel)
        endTime = self.data['EndTime']
        if (endTime == ''):
            endTime = self.data['StartTime']
        val = datetime.datetime.strptime(endTime,'%H:%M:%S')
        view.setTime(val)
        self.addView(view)
        
    def __onNext(self, btnID):
        startTime = self.getView().getTime()
        self.data['EndTime'] = startTime.strftime('%H:%M:%S') 
        self.quit(btnID)
    

class _DOWDialog(itg.Dialog):
    
    def onCreate(self):
        super(_DOWDialog, self).onCreate()
        view = itg.CheckListView(_('Select the day(s) of week'))
        view.setOkButton(_('Next'), self.__onNext)
        view.setBackButton(_('Back'),  cb=self.back)
        view.setCancelButton(_('Cancel'),  cb=self.cancel)
        for i in range (6):
            view.appendRow(locale.nl_langinfo(locale.DAY_2+i), checked=self.isChecked(i+1), data=i+1) #@UndefinedVariable
        view.appendRow(locale.nl_langinfo(locale.DAY_1), checked=self.isChecked('7'), data=7) #@UndefinedVariable
        self.addView(view)

    def isChecked(self, dow):
        if (str(dow) in self.data['DOW']):
            return True
        return False

    def __onNext(self, btnID):
        rows = self.getView().getSelectedRows()
        if (not rows):
            itg.msgbox(itg.MB_OK, _('No day selected.'))
        else:
            #selection = [ locale.nl_langinfo(locale.ABDAY_1+r['data']) for r in rows ]
            selection = [ str(r['data']) for r in rows ]
            #text = '%s' % ','.join(selection)
            self.data['DOW'] = ','.join(selection)
            self.quit(btnID)        


class _RelayDialog(itg.Dialog):
    
    def onCreate(self):
        super(_RelayDialog, self).onCreate()
        view = itg.ListView(_('Select the relay to control'))
        view.setOkButton(_('Next'), cb=self.__onNext)
        view.setBackButton(_('Back'), cb=self.quit)
        view.setCancelButton(_('Cancel'), cb=self.cancel)
        #TODO:Read from actual IOboards?
#        for idx,b in enumerate(ioboard.getIOBoards()):
#            view.appendRow('IO Board #%d' % (idx+1), hasSubItems=True, data=b, cb=self.__onIOBoard)
        for (b,r) in ( (1,1), (1,2), (2,1), (2,2)):
            view.appendRow(_('IO board %(board)s relay %(relay)s') % { 'board': b, 'relay': r }, data=('%s-%s' % (b,r)))
        self.addView(view)
        
    def __onNext(self, btnID):
        row = self.getView().getSelectedRow()
        self.data['IOBoard'] = row['data'][0:1] 
        self.data['Relay'] = row['data'][2:3]
        self.quit(itg.ID_NEXT)


class _ConfirmDialog(itg.Dialog):

    def onCreate(self):
        super(_ConfirmDialog, self).onCreate()        
        view = itg.MsgBoxView()
        view.setButton(0, _('Next'),    itg.ID_NEXT,   cb=self.__onNext)
        view.setButton(1, _('Back'),    itg.ID_BACK,   cb=self.quit)
        view.setButton(2, _('Cancel'),  itg.ID_CANCEL, cb=self.cancel)

        dow = getDOWSummaryText(self.data['DOW'])
        text = _('Switch relay %(relay)s on %(days)s from %(startTime)s to %(endTime)s?') % { 
                 'relay': '%s-%s' % (self.data['IOBoard'], self.data['Relay']),
                 'days' : dow,
                 'startTime': self.data['StartTime'],
                 'endTime'  : self.data['EndTime']}
        view.setText(text)
        self.addView(view)
        
    def __onNext(self, btnID):
        rt = self.data['RelaySchedules']
        rt.setRelayTime(self.data['StartTime'], self.data['EndTime'], self.data['DOW'], self.data['IOBoard'], self.data['Relay'])
        self.quit(btnID)
    
    
class AddOverrideTime(itg.WizardDialog):
    
    def __init__(self, relayTimes):
        super(AddOverrideTime, self).__init__()
        self.__relayTimes = relayTimes
    
    def run(self):
        pages = ( _OverrideStartDateDialog(),
                  _OverrideEndDateDialog(),
                  _OverrideConfirmDialog())
        # apply shared dictionary
        wizDat = { 'RelaySchedules'   : '',
                   'StartDate'    : '01/01',
                   'EndDate'      : '' 
         }
        wizDat['RelaySchedules'] = self.__relayTimes
        for p in pages:
            p.data = wizDat
        # run wizard
        self._runWizard(pages)
        return self.getResultID()


class _OverrideStartDateDialog(itg.Dialog):
    
    def onCreate(self):
        super(_OverrideStartDateDialog, self).onCreate()        
        view = itg.MaskedTextInputView('##_##', self.data['StartDate'], _('Enter start date MM/DD'))
        view.setButton(0, _('Next'),    itg.ID_NEXT,   cb=self.__onNext)
        view.setButton(1, _('Back'),    itg.ID_BACK,   cb=self.quit)
        view.setButton(2, _('Cancel'),  itg.ID_CANCEL, cb=self.cancel)
        self.addView(view)

    def __onNext(self, btnID):
        self.data['StartDate'] = self.getView().getValue() 
        self.quit(btnID)


class _OverrideEndDateDialog(itg.Dialog):
    
    def onCreate(self):
        super(_OverrideEndDateDialog, self).onCreate()        
        enddate = self.data['EndDate']
        if (enddate == ''):
            enddate = self.data['StartDate']
        view = itg.MaskedTextInputView('##_##', enddate, _('Enter end date MM/DD'))
        view.setButton(0, _('Next'),    itg.ID_NEXT,   cb=self.__onNext)
        view.setButton(1, _('Back'),    itg.ID_BACK,   cb=self.quit)
        view.setButton(2, _('Cancel'),  itg.ID_CANCEL, cb=self.cancel)
        self.addView(view)

    def __onNext(self, btnID):
        self.data['EndDate'] = self.getView().getValue() 
        self.quit(btnID)
    

class _OverrideConfirmDialog(itg.Dialog):

    def onCreate(self):
        super(_OverrideConfirmDialog, self).onCreate()
        view = itg.MsgBoxView()
        view.setButton(0, _('Next'),    itg.ID_NEXT,   cb=self.__onNext)
        view.setButton(1, _('Back'),    itg.ID_BACK,   cb=self.quit)
        view.setButton(2, _('Cancel'),  itg.ID_CANCEL, cb=self.cancel)
        text = _('Override the relay times on\n%(startDate)s to %(endDate)s?') % { 
                    'startDate': getDateDesc(self.data['StartDate']), 
                    'endDate': getDateDesc(self.data['EndDate'])}
        view.setText(text)
        self.addView(view)
        
    def __onNext(self, btnID):
        ov = self.data['RelaySchedules']
        ov.setOverride(self.data['StartDate'], self.data['EndDate'])
        self.quit(btnID)
    
    