# -*- coding: utf-8 -*-
#
# Copyright 2023 Grosvenor Technology
#
import subprocess

import itg
import log
from engine import dynButtons, fileHandler
from applib.db.tblSettings import getAppSetting

class TraceRouteDialog(itg.Dialog):
    
    def onCreate(self):
        super(TraceRouteDialog, self).onCreate()
        self.data = {'url': 'example.com'}
        view = itg.MenuView('TraceRoute')
        view.setBackButton(_('Exit'), self.back)
        ceHost = getAppSetting('clksrv_host')
        wcHost = getAppSetting('webclient_host')
        if ceHost:        
            view.appendRow(ceHost, data=ceHost, cb=self.__onSelect)
        if wcHost and (wcHost != ceHost):
            view.appendRow(wcHost, data=wcHost, cb=self.__onSelect)
        view.appendRow("Example", data="example.com", cb=self.__onSelect)
        view.appendRow("Other", hasSubItems=True, data="other", cb=self.__onNeedInput)
        self.addView(view)
        
    def __onSelect(self, pos, row):
        view = self.getView()
        row = view.getSelectedRow()
        self.data['url'] = row['data']
        if self.__checkLocal(self.data['url']):
            itg.waitbox(_('Running TraceRoute. Please wait'), self.__runTraceRoute)
            self.__showOutput()

    def __onNeedInput(self, pos, row):
        dlg = _InputURLDialog()
        dlg.data = self.data
        if dlg.run() == itg.ID_OK:
            if self.__checkLocal(self.data['url']):
                itg.waitbox(_('Running TraceRoute. Please wait'), self.__runTraceRoute)
                self.__showOutput()
            
    def __checkLocal(self, address):
        # See RFC 1918 (https://datatracker.ietf.org/doc/html/rfc1918#section-3)
        if address.startswith('192.168.') or address.startswith('172.16.') or address.startswith('10.0.'):
            resID = itg.msgbox(itg.MB_YES_NO, '{} appears to be a local address, which probably cannot be traced. Are you sure you want to continue?'.format(address))
            if resID == itg.ID_NO:
                return False
        return True
    
    def __runTraceRoute(self):
        try:
            output = subprocess.check_output(["traceroute", self.data['url']])
        except Exception as e:
            log.err("Failed to run TraceRoute:\n" + str(e))
            output = "Failed to run TraceRoute:\n" + str(e)
        self.data['output'] = output
        
    def __showOutput(self):
        dlg = _OutputDialog()
        dlg.data = self.data
        dlg.run()

class _InputURLDialog(itg.Dialog):
    
    def onCreate(self):
        super(_InputURLDialog, self).onCreate()
        view = itg.TextInputView('Enter URL')
        view.setButton(0, _('OK'),     itg.ID_OK,     cb=self.quit)
        view.setButton(1, _('Cancel'), itg.ID_CANCEL, cb=self.cancel)
        view.setValue(self.data['url'])
        view.setValueChangedCb(self.__onValueChanged)
        self.addView(view)

    def __onValueChanged(self, newValue):
        self.data['url'] = newValue
        
class _OutputDialog(itg.Dialog): 

    def onCreate(self):
        super(_OutputDialog, self).onCreate()
        text = self.data['output']
        view = itg.TextView(_('TraceRoute'), text, 'text/plain')
        view.setButton("Ok", itg.ID_OK, self.quit)
        self.addView(view)

#
#
# Support functions for dynamic buttons
#
#
class TraceRouteAction(dynButtons.Action):
    
    def getName(self):
        return 'trace.route'
    
    def getButtonText(self, actionParam, employee, languages):
        return _('TraceRoute')
    
    def getDialog(self, actionParam, employee, languages):
        return TraceRouteDialog()

    def isEmployeeRequired(self, actionParam):
        return False

    def getXsd(self):
        return """
        """

    def getHelp(self):
        return """
        TraceRoute Action.
        
        Runs traceroute and displays the returned details.

        Example::
        
            <button>
                <pos>1</pos>
                <action>
                    <trace.route />
                </action>
            </button>

        """        

class TraceRouteFileHandler(object):
    
    def __init__(self):
        self.url = 'example.com'

    def getHelp(self):
        return """Runs traceroute and exports the text results."""
        
    def fileExport(self, name):
        try:
            if self.url:
                export = subprocess.check_output(["traceroute", self.url])
            else:
                log.err("Invalid URL for TraceRoute")
        except Exception as e:
            log.err("Failed to run TraceRoute:\n" + str(e))
            export = "Failed to run TraceRoute:\n" + str(e)
        return export
    
    def fileParams(self, params):
        self.url = params['targetUrl']

def loadPlugin():
    dynButtons.registerAction(TraceRouteAction())
    fileHandler.register('^traceRoute\.txt$', TraceRouteFileHandler(), 'TraceRoute Report')
