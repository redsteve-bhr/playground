# -*- coding: utf-8 -*-
#
# Copyright 2011 Grosvenor Technology
#


import itg
import log
import tempfile
import playit

from applib.gui import playITEvent
import lastClockingsData
import tblLastClockings


class Dialog(itg.Dialog):
    
    def __init__(self, title, who, timeFormat=None, languages=None):
        super(Dialog, self).__init__()
        if (languages == None):
            languages = ['en',]
        view = itg.MenuView(title)
        view.setCancelButton(_('Cancel'), cb=self.cancel)
        if (timeFormat == None):
            timeFormat = '%x %X'
        lastClockings = tblLastClockings.getAppLastClocking()
        for l in lastClockings.selectLast(who, 20, timeFormat):
            reviewText = l['Type']
            if (l['Labels'] != None):
                labels = l['Labels']
                for lang in languages:
                    if (lang in labels):
                        reviewText = labels[lang]
                        break
            sub = True if l['Data'] else False
            view.appendRow(reviewText, l['LocalTime'], hasSubItems=sub, data=l, cb=self.__onSelect)
        self.addView(view)    

      
    def __onSelect(self, pos, row):
        row = self.getView().getSelectedRow()
        dataID = row['data']['Data']
        if (dataID == None):
            return
        (dataType, data) = lastClockingsData.readClockingDataFromUSB(dataID)
        if (dataType == None):
            log.warn('Got ID but no data on USB')
        elif (dataType == 'image/jpeg'):
            self.runDialog(_ReviewPhotoDlg(data))
        elif (dataType == 'audio/x-wav'):
            self.runDialog(_ReviewVoiceDlg(data))
        else:
            log.warn('Unsupported media type: %s' % dataType)
            

class _ReviewPhotoDlg(itg.Dialog):
    """ Dialog to display captured image whilst clocking"""
    
    def __init__(self, data):
        super(_ReviewPhotoDlg, self).__init__()
        view = itg.ImageView(title = _('Review photo...'))
        self.__file = tempfile.NamedTemporaryFile(suffix='.jpg')
        self.__file.write(data)
        self.__file.flush()        
        view.setImage(self.__file.name, True)
        view.setButton(0, _('OK'),   itg.ID_OK,     cb=self.quit)
        self.addView(view)
                

class _ReviewVoiceDlg(playITEvent.PlayITEventMixin, itg.Dialog):

    def __init__(self, data):
        super(_ReviewVoiceDlg, self).__init__()
        self.__player = playit.PlayIT()
        self.__file = tempfile.NamedTemporaryFile(suffix='.wav')
        self.__file.write(data)
        self.__file.flush()        
        view = itg.SpeakerView(_('Review voice...'))
        view.setButton(0, 'OK', itg.ID_OK, cb=self.quit)
        view.enableButton(itg.SpeakerView.BTN_PLAY, self.__onStart)
        self.addView(view)

    def onPlayITEvent(self, evMessage):
        if (evMessage.startswith('stopped')):
            self.getView().enableButton(itg.SpeakerView.BTN_PLAY, self.__onStart)

    def __onStart(self):
        self.playIT_EventListenerStart()        
        self.__player.play(self.__file.name)
        self.getView().enableButton(itg.SpeakerView.BTN_STOP, self.__onStop)

    def __onStop(self):
        self.__player.stop()
        self.getView().enableButton(itg.SpeakerView.BTN_PLAY, self.__onStart)

