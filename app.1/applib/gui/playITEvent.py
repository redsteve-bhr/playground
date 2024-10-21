# -*- coding: utf-8 -*-
#
# Copyright 2010 Grosvenor Technology
#


import playit
import itg
import threading

class PlayITEventMixin(object):

    def __del__(self):
        self.playIT_EventListenerStop()
    
    def playIT_EventListenerStart(self):
        if (not hasattr(self, 'onPlayITEvent')):
            return
        if (hasattr(self, 'playIT_Thread') and self.playIT_Thread != None):
            return
        self.playIT_Thread = PlayITEventThread(self.onPlayITEvent)
        self.playIT_Thread.start()
    
    def playIT_EventListenerStop(self):
        if (hasattr(self, 'playIT_Thread') and self.playIT_Thread != None):
            self.playIT_Thread.stop()
            self.playIT_Thread.join(5)
            self.playIT_Thread = None


class PlayITEventThread(threading.Thread):
    
    def __init__(self, cb):
        super(PlayITEventThread, self).__init__()
        self.__eventCb = itg.WeakCb(cb)
        
    def start(self):
        self.isRunning = True
        super(PlayITEventThread, self).start()

    def run(self):
        p = playit.PlayIT()        
        while (self.isRunning):
            ev = p.getEvent()
            if (self.isRunning):
                itg.runLater(self.__eventCb, (ev,))
        
    def stop(self):
        self.isRunning = False
        playit.PlayIT().sendPingEvent()
