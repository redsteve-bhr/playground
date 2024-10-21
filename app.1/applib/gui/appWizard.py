# -*- coding: utf-8 -*-
#
# Copyright 2011 Grosvenor Technology
#

"""
.. currentmodule:: applib.gui

:mod:`appWizard` --- Application Wizard Dialogs
===============================================

The :mod:`appWizard` module provides some dialogs to make writing and adding to a 
application wizard easy. It provides the wizard dialog itself, which is implemented
in :class:`appWizard.AppWizardDialog`. This dialog takes a list of pages to run
through. In addition it loads the system and application settings on startup and
writes back any changes done while going through the pages at the end. In case  
a system setting changed, the application wizard will reboot the terminal. If only application
settings were changed the wizard will restart the application. The application wizard will also 
set the application setting 'app_initialised' to **True** after all pages were run successfully.

The :mod:`appWizard` module also provides a base class for implementing pages and some ready-to-use
pages for setting up timezone, language and locale.

.. seealso::
    :ref:`howto-application`
    
.. versionchanged:: 3.0
    :class:`appWizard.AppWizardDialog` supports loading of the *default-itcfg.xml* file. See
    :ref:`howto-customisation` for details.

"""

import os
import itg
import cfg
import time
import log
import appit
import updateit
import uuid
import xml.etree.cElementTree
from applib.db.tblSettings import getAppSettings
from applib.utils import restartManager, countries


class AppWizardDialog(itg.WizardDialog):
    """ Create :class:`appWizard.AppWizardDialog`. *pages* is a list of
    dialog objects which should be derived from :class:`appWizard.AppWizardPage`.
    """
    
    def _runWizard(self, pages):
        settings = {'sys': {}, 'app': {}, 'tmp': {}}
        self.__loadSettings(settings)
        # apply settings dictionary to all pages
        for p in pages:
            p.setSettings(settings)
        itg.WizardDialog._runWizard(self, pages)
        resID = self.getResultID()
        if (resID == itg.ID_NEXT):
            itg.waitbox(_('Please wait while saving settings and configuring the terminal...'), self.__saveSettings, (settings,))
        return resID
    
    def __loadSettings(self, settings):
        appSettings = getAppSettings()
        settings['sys'] = cfg.getAll()
        settings['app'] = appSettings.getAllAsString()
        defaultItCfg = 'default-itcfg.xml'
        if (os.path.exists(defaultItCfg)):
            (sysCfg, unused, unused) = _parseItCfg(open(defaultItCfg, 'r').read())
            settings['sys'].update(sysCfg)

    def __saveSettings(self, settings):
        restartNeeded = False
        rebootNeeded  = False
        appSettings = getAppSettings()
        for (key,value) in settings['app'].iteritems():
            if (appSettings.getAsString(key) != value):
                appSettings.set(key, value, checkType=False)
                if (key != 'app_initialised'):
                    restartNeeded = True

        for (key, value) in settings['sys'].items():
            if (cfg.get(key) == value):
                del settings['sys'][key]
        if (settings['sys']):
            cfg.setMany(settings['sys'])
            # remove entries which do not need a reboot
            if ('it_timezone' in settings['sys']):
                os.system('sh /etc/init.d/S*tz.sh start')
            if ('it_language' in settings['sys'] or 'it_locale' in settings['sys']):
                os.system('sh /etc/init.d/S*locales.sh start')
                restartNeeded = True
            assistITsettings = ( 'it_service_assistit', 'it_assistit_domain', 'it_assistit_server', 'it_assistit_port', 'it_assistit_room', 'it_assistit_userfield', 'it_assistit_report_crash')
            for e in assistITsettings:
                if (e in settings['sys']):
                    os.system('sh /etc/init.d/S*assistitd.sh stop; sh /etc/init.d/S*assistitd.sh start')
                    break;
            for e in ('it_timezone', 'it_locale', 'it_language') + assistITsettings:
                if (e in settings['sys']):
                    del settings['sys'][e]
            # if still items in list, reboot is needed!
            if (settings['sys']):
                rebootNeeded = True
        # Restart/reboot app?
        if (rebootNeeded):
            restartManager.reboot(60, _('Terminal is now configured and will restart...'))
        elif (restartNeeded):
            restartManager.restart(60, _('Terminal is now configured and will restart the application...'))
        

def _parseItCfg(itCfgData):
    """ Parse itcfg.xml file and return tuple with system settings
        dictionary, application settings dictionary and project XML
        string (or None).
    """
    sysCfg = {}
    appCfg = {}
    projXml = None
    try:
        tType  = updateit.get_type()
        partNo = cfg.get(cfg.CFG_PARTNO)
        itcfg = xml.etree.cElementTree.fromstring(itCfgData)
        for c in itcfg.findall('sysCfg/cfg'):
            name  = c.get('name')
            if (c.get('terminal', tType) != tType):
                continue
            if (c.get('partNo', partNo) != partNo):
                continue            
            value = c.text
            if (value == None):
                value = ''
            sysCfg[name] = value
        for c in itcfg.findall('appCfg/cfg'):
            name  = c.get('name')
            value = c.text
            if (not name):
                continue
            if (c.get('terminal', tType) != tType):
                continue
            if (c.get('partNo', partNo) != partNo):
                continue            
            if (value == None):
                value = ''
            appCfg[name] = value
        # save project file if it got a project tag (and sub-elements)
        proj = itcfg.find('project')
        if (proj):
            projXml = xml.etree.cElementTree.tostring(proj, 'utf-8') 
    except Exception as e:
        log.warn('Something went wrong when reading itcfg: %s' % e)
    return (sysCfg, appCfg, projXml)



class AppWizardPage(object):
    """ Application wizard page base class. 
    
    When derived from this class and after being initialised by 
    :class:`appWizard.AppWizardDialog`, system and application settings 
    can be access via *self._settings*. *self._settings* is a dictionary 
    containing the keys 'sys', 'app' and 'tmp' to refer to further dictionaries 
    holding system, application and wizard temporary settings. All settings
    are stored as strings, so no type conversion took place.
    
    After the last page, all changes to system and application settings will
    be committed.
    
    Example::
     
        class ExamplePage(appWizard.AppWizardPage, itg.Dialog):
        
            def __init__(self):
                super(ExamplePage, self).__init__()
                view = itg.ListView(_('Select Setting'))
                view.appendRow('Green')
                view.appendRow('Red')
                view.appendRow('Blue')
                view.appendRow('White')
                view.setOkButton(_('Next'), self.__onOK)
                view.setBackButton(_('Back'), self.back)
                view.setCancelButton(_('Cancel'), self.cancel)        
                self.addView(view)
        
            def onRefreshData(self):
                if ('my_setting' not in self._settings['app']):
                    return
                view = self.getView()
                (pos, _row) = view.findRowBy('label', self._settings['app']['my_setting'])
                if (pos != None):
                    view.selectRow(pos)
                        
            def __onOK(self, btnID):
                row = self.getView().getSelectedRow()
                self._settings['app']['my_setting'] = row['label'] 
                self.quit(btnID)

        # [...]

        class Dialog(appWizard.AppWizardDialog):
            
            def run(self):
                pages = (appWizard.AutoConfigPage(),
                         appWizard.WelcomePage(), 
                         appWizard.PreCfgPage(),
                         ExamplePage(),                 
                         appWizard.FinishPage())
                return self._runWizard(pages)
                 
    The example above implements a wizard which:
     - Supports importing settings from a previous application automatically. 
     - Shows a welcome page.
     - Detects and imports a pre-cfg file if wanted.
     - Lets the user select a setting/color.
     - Shows a finish page, after which all changed settings will be commited.
     
    .. note:: Please note that for the example to work, *my_setting* needs to be
              in the default settings.
    """
    
    def setSettings(self, settings):
        self._settings = settings    


class WelcomePage(AppWizardPage, itg.Dialog):
    """ Simple welcome page which could be used as first page. It only 
    shows a message like::
    
        Application setup wizard
        YOUR_APP_NAME(APP_VERSION)
    
    
    """
    
    def __init__(self):
        super(WelcomePage, self).__init__()
        view = itg.MsgBoxView()
        view.setText(_('Application setup wizard\n%(appName)s(%(appVersion)s)') % { 
                'appName': appit.AppInfo().name(), 
                'appVersion': appit.AppInfo().version() } )
        view.setButton(0, _('Next'), itg.ID_NEXT, self.quit)
        view.setButton(1, _('Cancel'), itg.ID_CANCEL, self.cancel)
        self.addView(view)
        self.disableTimeout()


class WelcomePageNonInteractive(AppWizardPage, itg.PseudoDialog):
    """ Non-interactive version of :class:`appWizard.WelcomePage`. The same text will
    be shown but instead of using a message box a waitbox is used.
    
    .. versionadded:: 1.2
    """
    
    def run(self):
        itg.waitbox(_('Configuring %(appName)s(%(appVersion)s)\nPlease wait...') % { 
                'appName': appit.AppInfo().name(), 
                'appVersion': appit.AppInfo().version() }, time.sleep, (4,))
        self.setResultID(itg.ID_NEXT)
        return self.getResultID()


class NetworkPage(AppWizardPage, itg.Dialog):
    
    def __init__(self):
        super(NetworkPage, self).__init__()
        view = itg.MsgBoxView()
        view.setText(_('Configure network settings?'))
        view.setButton(0, _('Skip'), itg.ID_NEXT, self.quit)
        view.setButton(1, _('Yes'), 1)
        view.setButton(2, _('Back'), itg.ID_BACK, self.back)        
        view.setButton(3, _('Cancel'), itg.ID_CANCEL, self.cancel)
        self.addView(view)


class PreCfgPageNonInteractive(AppWizardPage, itg.PseudoDialog):
    """ This page will load an *itcfg.xml* file if one is found. The 
    *itcfg.xml* file can be supplied via net install or USB install to
    initialise system and application settings.
    
    An *itcfg.xml* file looks like the following:

    .. code-block:: xml
    
        ﻿<itcfg>
            <sysCfg>
                <cfg name="it_reader_type">auto</cfg>
            </sysCfg>
            <appCfg>
                <cfg name="app_log">dbg</cfg>
            </appCfg>
        </itcfg>

    .. versionchanged:: 2.1
        Project information found in the itcfg.xml file is stored as self._settings['project']
        and can be saved as file by :class:`appWizard.SaveProjectPage`. 
        
    .. versionchanged:: 3.0
        *itcfg.xml* files are not loaded directly from a USB memory device anymore.

    """

    def __init__(self):
        super(PreCfgPageNonInteractive, self).__init__()
        self.__itCfgFilename = '/mnt/user/db/itcfg.xml'
        self.__itCfgExists = os.path.exists(self.__itCfgFilename)
        
    def skip(self):
        return (self.__itCfgExists == False)
    
    def run(self):
        if (self.__itCfgExists):
            itg.waitbox(_('Applying settings...'), self.__applyPreCfg)
        self.__itCfgExists = False
        self.setResultID(itg.ID_NEXT)
        return itg.ID_NEXT

    def __applyPreCfg(self):
        try:
            # check DB folder for itcfg file
            itcfg = open(self.__itCfgFilename).read()
            (sysCfg, appCfg, projXml) = _parseItCfg(itcfg)
            self._settings['sys'].update(sysCfg)
            self._settings['app'].update(appCfg)
            if (projXml):
                self._settings['project'] = projXml
        except Exception as e:
            log.warn('Something went wrong when loading itcfg.xml: %s' % e)


class PreCfgPage(PreCfgPageNonInteractive):
    """ This page is now deprecated and should not be used anymore. Please 
        use :class:`appWizard.PreCfgPageNonInteractive`.
        
        .. versionchanged:: 3.0
            Page is deprecated.

    """
    pass

    
class AutoConfigPage(AppWizardPage, itg.PseudoDialog):
    """ Detects and applies *itcfg-auto.xml* file. If such a file
    exists in the DB folder of the application, all settings are applied
    and the application is restarted.
    
    This can be used when installing a new application which should take over
    the settings from the previous one. When installing the new application, 
    all settings need to be exported into the new DB folder (as *itcfg-auto.xml*). 
    This page in the new application would then import these settings and start 
    the application again. Because *app_initialised* was exported as **True** in 
    the auto setup, the wizard would not start again. All this would work without
    any user-interaction.
    
    .. note:: This page should be the first in the wizard.
    
    .. versionadded:: 1.2

    """
    
    def getFileName(self):
        return '/mnt/user/db/itcfg-auto.xml'

    def run(self):
        log.info('Applying itcfg-auto.xml')        
        (_resID, success) = itg.waitbox(_('Configuring application...'), self.__applyAutoConfig)
        if (success):
            self.setResultID(itg.ID_CANCEL)
        else:
            self.setResultID(itg.ID_NEXT)
        return self.getResultID()
        
    def __applyAutoConfig(self):
        try:
            appSettings = getAppSettings()
            itcfg  = xml.etree.cElementTree.fromstring(open(self.getFileName(), 'r').read())
            for c in itcfg.findall('appCfg/cfg'):
                name  = c.get('name')
                value = c.text
                if (value == None):
                    value = ''
                if (appSettings.getAsString(name) != value):
                    appSettings.set(name, value, checkType=False)
            os.unlink(self.getFileName())
            time.sleep(4)
            return True
        except Exception as e:
            log.err('Applying itcfg-auto.xml failed: %s' % e)
        return False
    
    def skip(self):
        return (not os.path.exists(self.getFileName()))


class RegionPage(AppWizardPage, itg.Dialog):
    """ Wizard page to select region. The list of supported countries can be
    customised by specifying the application setting **wiz_supported_countries**.
    This page is skipped if the list of regions/continents only contains one entry.
    This page sets a temporary setting (self._settings['tmp']['countries']),
    which is used by :class:`appWizard.CountryPage`.
    
    .. seealso::
        :ref:`howto-application`

    .. versionchanged:: 1.8
        Currently used region is pre-selected based on locale setting.

    .. versionadded:: 1.5

    """

    def onCreate(self):
        super(RegionPage, self).onCreate()
        view = itg.ListView(_('Select region'))
        view.setOkButton(_('Next'), self.__onOK)
        view.setBackButton(_('Back'), self.back)
        view.setCancelButton(_('Cancel'), self.cancel)
        countryCodes = self.__getSupportedCountryCodes()
        continents   = self.__getContinentsForCountryCodes(countryCodes)
        continents.sort()
        for c in continents:
            view.appendRow(c, c)
        country = countries.getByLocale(self._settings['sys']['it_locale'])
        if (country):
            (pos, _row) = view.findRowBy('data', country.getContinent())
            view.selectRow(pos)
        self.addView(view)
        
    def __getSupportedCountryCodes(self):
        allCountryCodes = countries.getAllCountryCodes()
        if ('wiz_supported_countries' in self._settings['app'] and self._settings['app']['wiz_supported_countries']):
            filterCodes = [ f.strip() for f in self._settings['app']['wiz_supported_countries'].split(',')]
            return countries.filterCountryCodes(allCountryCodes, filterCodes)
        else:
            return allCountryCodes

    def __getContinentsForCountryCodes(self, countryCodes):
        continents = set()
        for c in countryCodes:
            continents.add(countries.getByCountryCode(c).getContinent())
        return list(continents)

    def skip(self):
        countryCodes = self.__getSupportedCountryCodes()
        continents   = self.__getContinentsForCountryCodes(countryCodes)
        if (len(continents) != 1):
            return False
        self._settings['tmp']['countries'] = countryCodes
        return True
        
    def __onOK(self, btnID):
        row = self.getView().getSelectedRow()
        filterCodes = countries.getAllCountryCodesForContinent(row['data'])
        self._settings['tmp']['countries'] = countries.filterCountryCodes(self.__getSupportedCountryCodes(), filterCodes)   
        self.quit(btnID)
        

class CountryPage(AppWizardPage, itg.Dialog):
    """ Wizard page to select country. The list of supported countries can be
    customised by specifying the application setting **wiz_supported_countries**.
    If the list only contains one country, this page is skipped.
    This page only sets a temporary setting (self._settings['tmp']['country']),
    which is used by :class:`appWizard.LanguagePage` and :class:`appWizard.TimezonePage`.
    
    .. seealso::
        :ref:`howto-application`
        
    .. versionchanged:: 1.5
        Using internal country list instead of dictionary containing countries. Also supporting
        'wiz_supported_countries' setting and :class:`appWizard.RegionPage`.

    """

    def __init__(self):
        super(CountryPage, self).__init__()
        view = itg.ListView(_('Select country'))
        view.setOkButton(_('Next'), self.__onOK)
        view.setBackButton(_('Back'), self.back)
        view.setCancelButton(_('Cancel'), self.cancel)        
        self.addView(view)
        self.__lastCountries = None
        
    def __getSupportedCountryCodes(self):
        if ('countries' not in self._settings['tmp']):
            allCountryCodes = countries.getAllCountryCodes()
            if ('wiz_supported_countries' in self._settings['app'] and self._settings['app']['wiz_supported_countries']):
                filterCodes = [ f.strip() for f in self._settings['app']['wiz_supported_countries'].upper().split(',')]
                self._settings['tmp']['countries'] = countries.filterCountryCodes(allCountryCodes, filterCodes)
            else:
                self._settings['tmp']['countries'] = allCountryCodes
        return self._settings['tmp']['countries']            

    def skip(self):
        countryCodes = self.__getSupportedCountryCodes()
        if (len(countryCodes) != 1):
            return False
        # Only one country available, set and skip        
        self._settings['tmp']['country'] = countryCodes[0]
        return True
        
    def onRefreshData(self):
        countryCodes = self.__getSupportedCountryCodes()
        if (self.__lastCountries == countryCodes):
            return
        self.__lastCountries = countryCodes
        view = self.getView()
        view.removeAllRows()
        countryCodes.sort(key=lambda c: countries.getByCountryCode(c).getCountry())
        for code in countryCodes:
            view.appendRow(countries.getByCountryCode(code).getCountry(), code)
        country = countries.getByLocale(self._settings['sys']['it_locale'])
        if (country != None):        
            (pos, _row) = view.findRowBy('data', country.getCountryCode())
            view.selectRow(pos)
                
    def __onOK(self, btnID):
        row = self.getView().getSelectedRow()
        self._settings['tmp']['country'] = row['data'] 
        self.quit(btnID)

        
class LanguagePage(AppWizardPage, itg.Dialog):
    """ Wizard page for selecting the system language. This page
    depends on :class:`appWizard.CountryPage` and needs the same list of countries 
    in *countries*. This page will skip, if only one language is defined 
    for the selected country.
    This page will change _settings['sys']['it_locale'] and _settings['sys']['it_language'].
    
    .. seealso::
        :ref:`howto-application`

    .. versionchanged:: 1.5
        Using internal country list for languages and locales instead of dictionary containing countries.

    """

    def __init__(self):
        super(LanguagePage, self).__init__()
        view = itg.ListView(_('Select language'))
        view.setOkButton(_('Next'), self.__onOK)
        view.setBackButton(_('Back'), self.back)
        view.setCancelButton(_('Cancel'), self.cancel)        
        self.addView(view)
        self.__lastCountry = None
                
    def skip(self):
        if (self._settings['app'].get('wiz_prompt_language') == 'False'):
            return True
        country   = countries.getByCountryCode(self._settings['tmp']['country'])
        languages = country.getLanguages()
        if (len(languages) != 1):
            return False
        # Only one language available, set and skip
        self._settings['sys']['it_language'] = languages[0].getCode()
        self._settings['sys']['it_locale']   = languages[0].getLocale()
        return True
        
    def onRefreshData(self):
        country = countries.getByCountryCode(self._settings['tmp']['country'])
        if (self.__lastCountry == country.getCountryCode()):
            return
        self.__lastCountry = country.getCountryCode()        
        view = self.getView()
        view.removeAllRows()
        for l in country.getLanguages():
            view.appendRow(l.getName(), l)
        (pos, _row) = view.findRowBy('data', lambda l: l.getCode() == self._settings['sys']['it_language'])
        view.selectRow(pos)            
        
    def __onOK(self, btnID):
        row = self.getView().getSelectedRow()
        language  = row['data']
        self._settings['sys']['it_language'] = language.getCode()
        self._settings['sys']['it_locale']   = language.getLocale()
        self.quit(btnID)

        
class TimezonePage(AppWizardPage, itg.Dialog):
    """ Wizard page for selecting the correct timezone. This page
    depends on :class:`appWizard.CountryPage` and needs the same list of countries 
    in *countries*. In addition it needs a timezone definition (see :ref:`howto-application`).
    This page will skip, if only one timezone is defined for the selected country.
    This page will change _settings['sys']['it_timezone'].
    
    .. seealso::
        :ref:`howto-application`
        
    .. versionchanged:: 1.5
        Using internal country list for timezones instead of dictionary containing countries.
        
    """

    def __init__(self):
        super(TimezonePage, self).__init__()
        view = itg.ListView(_('Select timezone'))
        view.setOkButton(_('Next'), self.__onOK)
        view.setBackButton(_('Back'), self.back)
        view.setCancelButton(_('Cancel'), self.cancel)        
        self.addView(view)
        self.__lastCountry = None

    def skip(self):
        if (self._settings['app'].get('wiz_prompt_timezone') == 'False'):
            return True
        country   = countries.getByCountryCode(self._settings['tmp']['country'])
        timezones = country.getTimezones()
        if (len(timezones) != 1):
            return False
        # Only one timezone available, set and skip
        self._settings['sys']['it_timezone'] = timezones[0].getRule()
        return True
        
    def onRefreshData(self):
        country = countries.getByCountryCode(self._settings['tmp']['country'])
        if (self.__lastCountry == country.getCountryCode()):
            return
        self.__lastCountry = country.getCountryCode()
        view = self.getView()
        view.removeAllRows()
        for t in country.getTimezones():
            view.appendRow(t.getName(), t.getRule())
        (pos, _row) = view.findRowBy('data', self._settings['sys']['it_timezone'])        
        view.selectRow(pos)            

    def __onOK(self, btnID):
        row = self.getView().getSelectedRow()
        self._settings['sys']['it_timezone'] = row['data'] 
        self.quit(btnID)

        
class DeviceIDPage(AppWizardPage, itg.Dialog):
    
    def __init__(self, title=None, cfgPrefix='clksrv', mask='__####_#', default='xx0000-0'):
        super(DeviceIDPage, self).__init__()
        self.__title = title if (title != None) else _('Enter device ID')
        self.__prefix = cfgPrefix
        self.__mask = mask
        self.__default = default
    
    def onCreate(self):
        super(DeviceIDPage, self).onCreate()
        meth = self.__getDeviceIDCreationMethod()
        if (meth in (None, 'promptCountryCode')):
            view = itg.MaskedTextInputView(self.__mask, self.__default, self.__title)
        else:
            view = itg.TextInputView(self.__title)
            view.setValue(self.__getDeviceID())
        view.setButton(0, _('Next'), itg.ID_NEXT, self.__onOK)
        view.setButton(1, _('Back'), itg.ID_BACK, self.back)        
        view.setButton(2, _('Cancel'), itg.ID_CANCEL, self.cancel)
        self.addView(view)
        
    def onRefreshData(self):
        view = self.getView()
        meth = self.__getDeviceIDCreationMethod()
        if (meth in (None, 'promptCountryCode')):
            countryCode = self._settings['tmp']['country']
            value = view.getValue()
            if (value == self.__default):
                # First time, use country code and default or last number
                deviceID = self.__getDeviceID()
                if (deviceID): # got DeviceID from last time? 
                    number = deviceID[2:]
                else: # DeviceID not set, default number to all zeros
                    number = self.__default[2:]
                view.setValue('%s%s' % (countryCode, number))
            elif (not value.startswith(countryCode)):
                # Country code changed, keep number but change country code
                view.setValue('%s%s' % (countryCode, value[2:]))

    def __setDeviceID(self, clksrvID):
        self._settings['app']['%s_id' % self.__prefix] = clksrvID

    def __getDeviceID(self):
        return self._settings['app']['%s_id' % self.__prefix]

    def __getDeviceIDCreationMethod(self):
        idCreationCfgName = '%s_id_creation' % self.__prefix
        if (idCreationCfgName not in self._settings['app']):
            return None
        return self._settings['app']['%s_id_creation' % self.__prefix]
        
    def __onOK(self, btnID):
        self.__setDeviceID(self.getView().getValue()) 
        self.quit(btnID)

    def skip(self):
        meth = self.__getDeviceIDCreationMethod()
        if (meth == None):
            return False # Setting not supported, do countryCode, don't skip
        elif (meth == 'prompt'):
            return False
        elif (meth == 'promptCountryCode'):
            return False
        elif (meth == 'same'):
            self.__setDeviceID(self._settings['app']['clksrv_id'])
        elif (self.__getDeviceID()):
            pass # DeviceID already entered, do not reapply
        elif (meth == 'default'):
            self.__setDeviceID(self._settings['app']['%s_id_default' % self.__prefix])  
        elif (meth == 'systemid'):
            self.__setDeviceID(self._settings['sys']['systemid'])            
        elif (meth == 'ethaddr'):
            self.__setDeviceID(self._settings['sys']['ethaddr'].replace(':', '').upper())        
        elif (meth == 'partno'):
            self.__setDeviceID(self._settings['sys']['partno'])            
        elif (meth == 'uuid'):
            self.__setDeviceID(uuid.uuid1())
        else:
            log.warn('Unsupported Device ID creation method (%s)' % meth)
            return False # Uh! Do not skip if method is unknown 
        return True

  
class StorePage(DeviceIDPage):
    
    def __init__(self):
        super(StorePage, self).__init__()
        log.warn('appWizard.StorePage is deprecated, please use appWizard.DeviceIDPage!')


class FinishPage(AppWizardPage, itg.Dialog):
    """ This wizard page only shows the message "Wizard completed" message. It should
    be used as last page in the application wizard.
    
    If exitted by pressing the 'Save' button _settings['app']['app_initialised'] will be 
    set to **True**.
    """

    def __init__(self):
        super(FinishPage, self).__init__()
        view = itg.MsgBoxView()
        view.setText(_('Wizard completed'))
        view.setButton(0, _('Save'), itg.ID_NEXT, self.__onOK)
        view.setButton(1, _('Back'), itg.ID_BACK, self.back)        
        view.setButton(2, _('Cancel'), itg.ID_CANCEL, self.cancel)
        self.addView(view)
        
    def __onOK(self, btnID):
        self._settings['app']['app_initialised'] = True
        self.quit(btnID)


class FinishPageNonInteractive(AppWizardPage, itg.PseudoDialog):
    """ Non-interactive version of :class:`appWizard.FinishPage`. No
    message is shown.
    
    .. versionadded:: 1.2
    """

    def run(self):
        self._settings['app']['app_initialised'] = True
        self.setResultID(itg.ID_NEXT)
        return itg.ID_NEXT


class SaveProjectPage(AppWizardPage, itg.PseudoDialog):
    """ This page has no UI elements, it only saves project information
    found in the itcfg.xml file to /mnt/user/db/startup-project.xml so 
    that it can be loaded by a file handler on next application start.
    
    .. versionadded:: 2.1
    """

    
    def run(self):
        try:
            if ('project' in self._settings):
                proj = self._settings['project']
                if (proj):
                    open('/mnt/user/db/startup-project.xml', 'w').write(proj)
        except Exception as e:
            log.warn('Failed to save start-up project: %s' % e)
        return itg.ID_NEXT