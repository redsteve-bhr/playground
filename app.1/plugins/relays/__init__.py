# -*- coding: utf-8 -*-
#
# Copyright 2011 Grosvenor Technology
#

from engine import dynButtons, fileHandler
import relaySchedules
import relaySchedulesEditor
import relaySchedulesHandler

from plugins import assistitService
from applib.utils import relayManager

class RelayEditorAction(dynButtons.Action):
    
    def getName(self):
        return 'relay.editor'
    
    def getButtonText(self, actionParam, employee, languages):
        return _('Relay Schedules')

    def getDialog(self, actionParam, employee, languages):
        return relaySchedulesEditor.Dialog()

    def getHelp(self):
        return """
        Configure relay schedules.

        This action brings up the relay schedule editor. The action is used
        by the application setup.
        
        """        

def _cmdRelay(params):
    if (len(params) == 3 and params[0] in ('on', 'off')):
        (state, ioBoard, relay) = params
        if (state == 'on'):
            relayManager.setRelayAlwaysOn(int(ioBoard)-1, int(relay)-1)
        else:
            relayManager.clearRelayAlwaysOn(int(ioBoard)-1, int(relay)-1)
    elif (len(params) == 4 and params[0] in ('on', 'off')):
        (state, ioBoard, relay, duration) = params
        if (state == 'on'):
            relayManager.setRelayOn(int(ioBoard)-1, int(relay)-1, float(duration))
        else:
            return 'Wrong syntax, duration not supported for turning relay off'
    else:
        return '\n'.join(("",
                          "Syntax error, wrong number of arguments, use: ",
                          "",
                          "relay on|off IOBOARD RELAY [DURATION] ",
                          "",
                          "e.g.: relay on 1 1 5",
                          ""))
    return 'ok'

def loadPlugin():
    dynButtons.registerAction(RelayEditorAction())
    fileHandler.register('^relays.*\.xml$', relaySchedulesHandler.RelaySchedulesHandler(), 'Relay schedule')
    assistitService.registerCommand('relay', _cmdRelay)

def startPlugin():
    relaySchedules.startRelayThreads()

def stopPlugin():
    relaySchedules.stopRelayThreads()

