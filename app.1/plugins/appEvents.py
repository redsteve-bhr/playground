# -*- coding: utf-8 -*-

from engine import fileHandler
from applib.db import tblAppEvents 
from applib.db.tblSettings import getAppSetting, SettingsSection, MultiListSetting, NumberSetting



class AppEventExportFileHandler(fileHandler.CsvExportFileHandler):

    def __init__(self, filename):
        super(AppEventExportFileHandler, self).__init__(filename, None)
        
    def fileExport(self, name):
        self.dataTbl = tblAppEvents.getAppEvents()
        return super(AppEventExportFileHandler, self).fileExport(name)

    def getHelp(self):
        return """
        Application events can be collected for diagnostic purposes. This file handler allows the appEvents table 
        to be exported to a CSV file for analysis. File import is not supported. Collection of application 
        events is controlled by the settings :ref:`setting_app_events` and :ref:`setting_app_max_events`.
        """.replace('        ', '')

def loadPlugin():
    fh = AppEventExportFileHandler('tblAppEvents.csv')
    fileHandler.register('^tblAppEvents.csv$', fh , 'AppEvents')

def startPlugin():
    tblAppEvents.enableAppEvents(getAppSetting('app_events') or [], getAppSetting('app_max_events'))
    tblAppEvents.addSystemEvent('app.started')

def getSettings():
    sectionName = 'App Settings'
    sectionComment = 'These are the settings for the generic terminal application parameters.'
    appSection = SettingsSection(sectionName, sectionComment)
    s = MultiListSetting(appSection,
            name     = 'app_events',
            label    = 'Events',
            data     = '',
            comment  = ('Application event logging for analysis' ))
    s.addListOption('employee', 'Employee', )
    s.addListOption('bio', 'Biometric')
    s.addListOption('system', 'System')
    s.addListOption('comms', 'Comms')
    NumberSetting(appSection,
            name     = 'app_max_events', 
            label    = 'Max Events',
            data     = '1000',
            comment  = ('Maximum application events to hold, when limit reached the oldest 20%% are automatically deleted'))
    return [appSection,]

