# -*- coding: utf-8 -*-
#
# Copyright 2011 Grosvenor Technology
#
import os
import log
import locale
import gettext
import itg
import appit
import time

from applib.db.tblSettings import initAppSettings, getAppSetting, SettingsSection, ListSetting, MultiListSetting, BoolSetting, NumberSetting
from applib.gui.themes import setupTheme
from applib.gui import setupLTR_RTL
from applib.utils import resourceManager    
from applib.utils import restartManager
from applib.utils import crashReport
from applib.bio import load as bioLoad


class Application(object):
    """ Create :class:`Application` instance. *IdleDialogClass* is the application's
    main dialog class. Because it gets created within :class:`Application` it must
    not take any arguments in its constructor.
    
    Example::
    
        class MainDialog(itg.Dialog):
        
            def __init__(self):
                view = itg.IdleMenuView()
                # [...]
        
        app = applib.Application(MainDialog)
        app.run()
    
    .. important::
        Please note that MainDialog takes no arguments in its constructor and that the
        MainDialog class is passed to :class:`Application` rather than an instance of it.
        
    If *defaultSettings* is given application settings are initialised by it and can be
    accessed by :func:`applib.db.tblSettings.getAppSettings` and :func:`applib.db.tblSettings.getAppSetting`. 
    :class:`Application` supports few application settings already, like:
    
     - app_log
     - app_initialised (only if *WizardDialogClass* is not **None**)
     - theme_name (only on IT51, to initialise a theme, see :func:`applib.gui.themes.setupTheme()`)

    Useful settings::

        appSettings = (
                        # Used for appWizard
                        {'name'          : 'app_initialised',
                         'displayName'   : 'Initialised',
                         'allowEdit'     : True,
                         'format'        : 'bool',
                         'options'       : '',
                         'data'          : 'False',
                         'comment'       : 'True if wizard was completed and application was initialised'},
        
                        # Used to initialise logging
                        {'name'         : 'app_log',
                         'displayName'  : 'Logging',
                         'allowEdit'    : True,
                         'format'       : 'multi',
                         'options'      : 'Debug=dbg|Net=net|SQL=sql', 
                         'data'         : '',
                         'comment'      : 'Enable/disable verbose logging' },
                
                    )
        
        securitySettings = (
                        # used in applib.gui.settingsEditor
                        {'name'         : 'cfg_pin_enable',
                         'displayName'  : 'Enable PIN',
                         'allowEdit'    : True,
                         'format'       : 'bool',
                         'options'      : '',
                         'data'         : 'False',
                         'comment'      : 'Enable/disable PIN check for application settings editor' },
        
                        {'name'         : 'cfg_pin',
                         'displayName'  : 'PIN',
                         'allowEdit'    : True,
                         'format'       : 'number',
                         'options'      : 'len=4',
                         'data'         : '1905',
                         'comment'      : 'PIN (unencrypted) to access application settings editor' },
                         )
        
        settings = ({ 'name': 'App Settings',        'settings': appSettings},
                    { 'name': 'Security',            'settings': securitySettings} )

    If *WizardDialogClass* is not **None** and "app_initialised" is **False**, :class:`Application`
    will run the wizard dialog before running the *IdleDialogClass*.
    
    *UpgradeDialogClass* is executed between running the wizard and the main dialog (if not **None**).
    This dialog should check for and execute any upgrades on tables or data structures, which may
    be needed after an application version change.
    
    .. seealso::
        :ref:`howto-application`

    """


    def __init__(self, IdleDialogClass, defaultSettings=None, WizardDialogClass=None, UpgradeDialogClass=None):
        self.__idleClass = IdleDialogClass
        self.__wizardClass = WizardDialogClass
        self.__upgradeDlgClass = UpgradeDialogClass
        self.__restartNeededAfterInit = False
        initAppSettings(defaultSettings)
        appName  = appit.AppInfo().name()
        logLevel = getAppSetting('app_log')
        if (logLevel == None):
            logLevel = []
        log.open(appName, 'dbg' in logLevel, False, 'sql' in logLevel, 'net' in logLevel)

    def __setupLocales(self):
        try:
            locale.setlocale(locale.LC_ALL, '')
            gettext.install('app', 'languages')
            setupLTR_RTL()
        except Exception as e:
            log.err('Error setting up locale! (%s)' % e)
            log.info('Using default locale (en_GB.UTF-8)!')
            locale.setlocale(locale.LC_ALL, 'en_GB.UTF-8')
            time.strptime("2010-09-14 17:30:00", "%Y-%m-%d %H:%M:%S")
            gettext.install('app', 'languages')

    def __setupTheme(self):
        restartNeeded = setupTheme(getAppSetting('theme_name'))
        if (restartNeeded):
            self.__restartNeededAfterInit = True
            
    def init(self):
        crashReport.start()
        self.__setupLocales()
        self.__setupTheme()
        restartManager.setupSignals()
        if (hasattr(itg, 'setRestartApplicationFunc') and hasattr(itg, 'setRestartTerminalFunc')):
            itg.setRestartApplicationFunc(restartManager.restartFromUI)
            itg.setRestartTerminalFunc(restartManager.rebootFromUI)
        os.system('killall bootsplashit > /dev/null 2>&1')
        resourceManager.addResourceDir('applib/icons')
        if (self.__restartNeededAfterInit):
            restartManager.restartFromUI(10, _('Terminal configuration changed. Application will restart now...'))
        bioLoad()            

    def run(self):
        """ Run application. This function returns if the application
        wizard was cancelled or the main dialog was quit.
        """
        self.init()
        if (self.__wizardClass != None):
            if (not getAppSetting('app_initialised')):
                wiz = self.__wizardClass()
                wiz.run()
                if (wiz.getResultID() not in (itg.ID_OK, itg.ID_NEXT)):
                    self.cleanup()
                    return
        if (self.__upgradeDlgClass != None):
            dlg = self.__upgradeDlgClass()
            dlg.run()
        idle = self.__idleClass()
        idle.run()
        del idle
        self.cleanup()
    
    def cleanup(self):
        pass


def getSettings():
    # App Settings
    sectionName = 'App Settings'
    sectionComment = 'These are the settings for the generic terminal application parameters.'
    appSection = SettingsSection(sectionName, sectionComment)
    BoolSetting(appSection,
            name     = 'app_initialised', 
            label    = 'Initialised', 
            data     = 'False',
            comment  = ('True if wizard was completed and application was initialised'))
    s = MultiListSetting(appSection,
            name     = 'app_log',
            label    = 'Logging',
            data     = '',
            comment  = ('Enable/disable verbose logging' ))
    s.addListOption('dbg', 'Debug')
    s.addListOption('net', 'Net')
    s.addListOption('sql', 'SQL')
    NumberSetting(appSection,
            name     = 'app_min_diskspace', 
            label    = 'Disk Space warning level (MB)', 
            data     = '2',
            minValue = None, 
            maxValue = None, 
            length   = '4',  
            units    = 'MB', 
            comment  = ('Triggers a health monitor warning if free disk-space drops below this value'))
    s = ListSetting(appSection,
            name     = 'app_bio_encrypt',
            label    = 'Bio Template Encryption',
            data     = 'none',
            comment  = ('Type of encryption for biometric templates' ))
    s.addListOption('none')
    s.addListOption('suprema-aes256')

    # Security Settings
    sectionName = 'Security'
    sectionComment = 'These are the settings for the Security features.'
    securitySection = SettingsSection(sectionName, sectionComment)
    BoolSetting(securitySection,
            name     = 'cfg_pin_enable', 
            label    = 'Enable settings PIN', 
            data     = 'False', 
            comment  = ('Enable/disable PIN check for application settings editor'))
    NumberSetting(securitySection,
            name     = 'cfg_pin', 
            label    = 'Settings PIN', 
            data     = '1905',
            minValue = None, 
            maxValue = None, 
            length   = '4',  
            units    = None, 
            comment  = ('PIN (unencrypted) to access application settings editor'))

    return [appSection, securitySection]

