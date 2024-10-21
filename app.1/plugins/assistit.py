# -*- coding: utf-8 -*-
#
# Copyright 2013 Grosvenor Technology
#

import itg
import os
import cfg
from applib.db.tblSettings import getAppSetting
from engine import dynButtons

class Dialog(itg.PseudoDialog):
    """ Pseudo dialog running through turning on remote support."""
    
    def run(self):
        if (itg.msgbox(itg.MB_YES_NO, _('Turn on remote support?')) != itg.ID_YES):
            return
        if (TestAssistITDialog().run() != itg.ID_OK):
            return
        dlg = _EnterSupportRefDialog()
        if (dlg.run() != itg.ID_OK):
            return 
        ref = dlg.getReference()
        _EnableAssistITDialog(ref).run()
        


class TestAssistITDialog(itg.PseudoDialog):
    """ Test whether the assistIT connection is working"""

    def __init__(self, reportOnSuccess=False):
        self.__reportOnSuccess = reportOnSuccess

    def run(self):
        self.msg = ''
        self.__success = False
        itg.waitbox(_('Testing connection to AssistIT...'), self.__test)
        if (self.__success):
            if (self.__reportOnSuccess):
                itg.msgbox(itg.MB_OK, self.msg)
            return itg.ID_OK
        else:
            itg.msgbox(itg.MB_OK, self.msg)
            return itg.ID_CANCEL

    def __test(self):
        res = os.system('/usr/sbin/assistitd -T')
        if (res == 0):
            self.msg = _('AssistIT connected successfully.')
            self.__success = True
        else:
            error = open('/var/log/assistit.error', 'r').read()
            self.msg = _('AssistIT failed to connect (%s)') % error

        

class _EnterSupportRefDialog(itg.Dialog):

    def onCreate(self):
        super(_EnterSupportRefDialog, self).onCreate()
        view = itg.TextInputView( _('Enter support reference'))
        view.setValue('')
        view.setButton(0, _('Next'), itg.ID_OK, self.__onOK)
        view.setButton(1, _('Cancel'), itg.ID_CANCEL, self.cancel)
        self.addView(view)
        
    def __onOK(self, btnID):
        self.quit(btnID)
    
    def getReference(self):
        return self.getView().getValue()



class _EnableAssistITDialog(itg.PseudoDialog):

    def __init__(self, ref):
        super(_EnableAssistITDialog, self).__init__()
        self.__ref = ref

    def run(self):
        self.__msg = ''
        itg.waitbox(_('Turning on AssistIT...'), self.__enableAssistIT)
        itg.msgbox(itg.MB_OK, self.__msg)
        return itg.ID_OK
        
    def __enableAssistIT(self):
        """ Enable the service in the settings, set up reference in the user field
        and actually start the service"""
        
        text = '%s/%s' % (getAppSetting('clksrv_id'), self.__ref)
        cfg.set(cfg.CFG_ASSISTIT_USERFIELD, text)
        cfg.set(cfg.CFG_SRVC_ASSISTIT, cfg.CFG_TRUE)
        os.system('sh /etc/init.d/S*assistitd.sh restart')
        self.__msg = _('Remote support has been enabled')
        
        

class AssistITEnableAction(dynButtons.Action):
    
    def getName(self):
        return 'assistit.enable'
    
    def getButtonText(self, actionParam, employee, languages):
        return _('Assistance')

    def getDialog(self, actionParam, employee, languages):
        return Dialog()

    def getHelp(self):
        return """
        Enable AssistIT. The user has the option to enter a support
        reference text.
                
        Example::
        
            <button>
                <pos>1</pos>
                <action>
                    <assistit.enable />
                </action>
            </button>

        """

class AssistITTestAction(dynButtons.Action):

    def getName(self):
        return 'assistit.test'
    
    def getButtonText(self, actionParam, employee, languages):
        return _('Test AssistIT')

    def getDialog(self, actionParam, employee, languages):
        return TestAssistITDialog(True)

    def getHelp(self):
        return """
        Test connection to AssistIT server.
                
        Example::
        
            <button>
                <pos>1</pos>
                <action>
                    <assistit.test />
                </action>
            </button>

        """


def loadPlugin():
    dynButtons.registerAction(AssistITEnableAction())
    dynButtons.registerAction(AssistITTestAction())
