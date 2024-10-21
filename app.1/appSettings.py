# -*- coding: utf-8 -*-
#
#


import plugins
import clockserver
import appWizard
import webClient
import cloudStorage
import proxyServer
import emps
from engine import badge
from applib.db.tblSettings import settingsToDict, SettingsSection, TextSetting, NumberSetting
from applib import application
import appMonitor

    
def getDefaultSettings():
    """ Return dictionary with default settings. """
    defaultSettings = []
    defaultSettings.extend(plugins.getSettings())
    defaultSettings.extend(emps.getSettings())
    defaultSettings.extend(badge.getSettings())
    defaultSettings.append(clockserver.getClockserver1Settings())
    #defaultSettings.append(clockserver.getClockserver2Settings())
    defaultSettings.extend(cloudStorage.getSettings())
    defaultSettings.extend(webClient.getSettings())
    defaultSettings.extend(proxyServer.getSettings())
    defaultSettings.extend(appWizard.getSettings())
    defaultSettings.extend(application.getSettings())
    defaultSettings.extend(appMonitor.getSettings())
    defaultSettings.extend(getExtendedAppSettings())
    return settingsToDict(defaultSettings)

def getExtendedAppSettings():
    sectionName = 'App Settings'
    sectionComment = 'These are the settings for the generic terminal application parameters.'
    appSection = SettingsSection(sectionName, sectionComment)
    
    TextSetting(appSection,
            name='app_date_format',
            label='Date Format',
            data='',
            comment=(
                'Format to use for date entries. E.g. "%m/%d/%Y". If not set, the terminal\'s locale date format will be used'))
    
    NumberSetting(appSection,
            name='app_first_day_of_week',
            label='First Day of Week',
            data='-1',
            comment=('First day of week for Calendar display (-1=System default, 0=Monday, 6=Sunday)'))
    
    return [appSection]


if __name__ == '__main__':
    pass
    #from applib.db.tblSettings import compareSettingsDict
    #settingsDict = getDefaultSettings()
    #compareSettingsDict(settingsDict, settings)

