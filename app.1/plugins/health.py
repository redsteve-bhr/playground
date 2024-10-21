# -*- coding: utf-8 -*-
#
# Copyright 2013 Grosvenor Technology
#
import itg
from engine import dynButtons
from applib.gui import health
from applib.utils import restartManager, healthMonitor
from applib.db.tblSettings import getAppSettings

class ExitDialog(itg.PseudoDialog):
    
    def run(self):
        restartManager.restartFromUI(60, _('Exiting application, please wait...'))


class AppWizardRestartDialog(itg.PseudoDialog):
    
    def run(self):
        
        res = itg.msgbox(itg.MB_YES_NO, _('Restart application and run wizard?'))
        if (res != itg.ID_YES):
            return
        getAppSettings().set('app_initialised', 'False')
        restartManager.restartFromUI(60, _('Restarting application wizard, please wait...'))



class HealthMenuAction(dynButtons.Action):
    
    def getName(self):
        return 'app.health'
    
    def getButtonText(self, actionParam, employee, languages):
        return _('Health')

    def getDialog(self, actionParam, employee, languages):
        return health.HealthMonitorDialog()

    def getHelp(self):
        return """
        Show health monitor.
                
        Example::
        
            <button>
                <pos>1</pos>
                <action>
                    <app.health />
                </action>
            </button>

        """


class ExitAppAction(dynButtons.Action):

    def getName(self):
        return 'app.exit'
    
    def getButtonText(self, actionParam, employee, languages):
        return _('Exit App')
    
    def getDialog(self, actionParam, employee, languages):
        return ExitDialog()

    def getHelp(self):
        return """
        Exit application.
                
        This action can be used to exit the application (e.g. to get to the 
        terminal setup). The "RestartManager" is used to make sure 
        ongoing tasks using the "PreventRestartLock" can finish first. 
        
        Example::
        
            <button>
                <pos>1</pos>
                <action>
                    <app.exit />
                </action>
            </button>

        """


class AppWizardRestartAction(dynButtons.Action):

    def getName(self):
        return 'app.wizard.restart'
    
    def getButtonText(self, actionParam, employee, languages):
        return _('Restart wizard')
    
    def getDialog(self, actionParam, employee, languages):
        return AppWizardRestartDialog()

    def getHelp(self):
        return """
        Application wizard restart.
                
        This action can be used to re-run the application setup wizard. 
        The "RestartManager" is used to makes sure ongoing tasks using 
        the "PreventRestartLock" can finish first. 
        
        Example::
        
            <button>
                <pos>1</pos>
                <action>
                    <app.wizard.restart />
                </action>
            </button>

        """


def loadPlugin():
    dynButtons.registerAction(HealthMenuAction())
    dynButtons.registerAction(ExitAppAction())
    dynButtons.registerAction(AppWizardRestartAction())

def startPlugin():
    healthMonitor.getAppHealthMonitor().start()

def stopPlugin():
    healthMonitor.getAppHealthMonitor().stop()
    
