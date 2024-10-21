# -*- coding: utf-8 -*-
#
# Copyright 2023 Grosvenor Technology
#
import subprocess
import re

import itg
import log
from applib.utils import timeUtils
from engine import dynButtons, fileHandler

def getLocalTimeStamp():
    timeStamp = re.sub('T', ' ', timeUtils.getXMLTimestampNow())[:19]
    return 'System Local Time: [%s]' % timeStamp
    
class NTPTestDialog(itg.Dialog):

    def onCreate(self):
        super(NTPTestDialog, self).onCreate()
        text = """
Running NTP Test
================
Please wait.
        """
        view = itg.TextView(_('Text View'), text, 'text/plain')
        view.setTitle("NTP Test")
        view.setButton(_('OK'), itg.ID_OK, self.quit)
        self.addView(view)
        itg.waitbox(_('Running NTP Test. Please wait'), self.runTest)

    def runTest(self):
        try:
            output = subprocess.check_output(["ntptest"])
            output = getLocalTimeStamp() + '\n' + output
        except Exception as e:
            log.err("Failed to run NTP Test:\n" + str(e))
            output = "Failed to run NTP Test:\n" + str(e)
        view = self.getView()
        view.setText(output, mimeType='text/plain')

#
#
# Support functions for dynamic buttons
#
#
class NTPTestAction(dynButtons.Action):
    
    def getName(self):
        return 'ntp.test'
    
    def getButtonText(self, actionParam, employee, languages):
        return _('NTP Test')
    
    def getDialog(self, actionParam, employee, languages):
        return NTPTestDialog()

    def isEmployeeRequired(self, actionParam):
        return False

    def getXsd(self):
        return """
        """

    def getHelp(self):
        return """
        NTP Test Action.
        
        Interrogates the NTP server and displays the returned details.

        Example::
        
            <button>
                <pos>1</pos>
                <action>
                    <ntp.test />
                </action>
            </button>

        """        

class NTPTestReportHandler(object):
    
    def getHelp(self):
        return """Runs ntptest and exports the text results."""
        
    def fileExport(self, name):
        try:
            export = subprocess.check_output(["ntptest"])
        except Exception as e:
            log.err("Failed to run NTP Test:\n" + str(e))
            export = "Failed to run NTP Test:\n" + str(e)
        export = getLocalTimeStamp() + '\n' + export
        return export
    

def loadPlugin():
    dynButtons.registerAction(NTPTestAction())
    fileHandler.register('^ntpTest\.txt$', NTPTestReportHandler(), 'NTP Test Report')
