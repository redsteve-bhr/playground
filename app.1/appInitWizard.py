# -*- coding: utf-8 -*-
#
# Copyright 2023 Grosvenor Technology
#
"""Support for non-interactive initialisation of the application on the first start-up

This is intended to replace appWizard.
"""

import os
import threading
import itg
import cfg
import log
import updateit
import uuid
import xml.etree.cElementTree
from applib.db.tblSettings import getAppSettings
from applib.utils import restartManager

class _BackgroundThread(threading.Thread):

    def __init__(self, dlg):
        super(_BackgroundThread, self).__init__()
        self.__dlg = dlg
        self.__event = threading.Event()

    def run(self):
        # Get dialog and remove it from instance so to not
        # have a circular reference
        dlg = self.__dlg
        del self.__dlg

        settings = {'sys': {}, 'app': {}, 'tmp': {}}
        self.__loadSettings(settings)

        # Run the setup routines
        PreConfigSetup().run(settings)        
        DeviceIDSetup().run(settings)

        if self.__event.isSet():
            itg.runLater(dlg.quit, (itg.ID_CANCEL,))
        else:
            settings['app']['app_initialised'] = True
            self.__saveSettings(settings)
            itg.runLater(dlg.quit, (itg.ID_OK,))

    def stop(self):
        self.__event.set()
        self.join(2)

    def __loadSettings(self, settings):
        """Copied from applib/gui/appWizard.py"""
        appSettings = getAppSettings()
        settings['sys'] = cfg.getAll()
        settings['app'] = appSettings.getAllAsString()
        defaultItCfg = 'default-itcfg.xml'
        if (os.path.exists(defaultItCfg)):
            (sysCfg, unused, unused) = _parseItCfg(open(defaultItCfg, 'r').read())
            settings['sys'].update(sysCfg)

    def __saveSettings(self, settings):
        """Copied from applib/gui/appWizard.py"""
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

        Copied from applib/gui/appWizard.py
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


class Dialog(itg.Dialog):

    def __init__(self):
        super(Dialog, self).__init__()
        view = itg.CancellableWaitBoxView()
        view.setText(_('Preparing Application'))
        view.setButton(0, _('Cancel'), itg.ID_CANCEL, self.__cancel)
        self.disableTimeout()
        self.addView(view)

    def onShow(self):
        super(Dialog, self).onShow()
        self.__thread = _BackgroundThread(self)
        self.__thread.start()

    def __cancel(self, btnID):
        self.getView().setText(_('Cancelling...'))
        self.__thread.stop()
    

class PreConfigSetup(object):
    """This will load an *itcfg.xml* file if one is found. The *itcfg.xml* file
    can be supplied via net install or USB install to initialise system and 
    application settings.
    
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
    """
    
    def run(self, settings):
        self.__settings = settings
        self.__itCfgFilename = '/mnt/user/db/itcfg.xml'
        if os.path.exists(self.__itCfgFilename):
            self.__applyConfig
        
    def __applyConfig(self):
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

        
class DeviceIDSetup(object):
    """Class to handle the set-up of the Device ID
    
    Because this is non-interactive, it does not cover the Device ID Creation 
    options that require user input (if one of these options has been specified
    it will be ignored, but a warning message will be logged).
    """
    
    def run(self, settings, cfgPrefix='clksrv'):
        self.__settings = settings
        self.__prefix = cfgPrefix

        meth = self.__getDeviceIDCreationMethod()
        if (meth == 'same'):
            self.__setDeviceID(self.__settings['app']['clksrv_id'])
        # Amended for GT-Connect, which can send a blank clksrv_id which should be treated as 'None'
        elif (self.__getDeviceID() is not None and self.__getDeviceID().strip != ''):
            pass # DeviceID already entered, do not reapply
        elif (meth == 'default'):
            self.__setDeviceID(self.__settings['app']['%s_id_default' % self.__prefix])
        elif (meth == 'systemid'):
            self.__setDeviceID(self.__settings['sys']['systemid'])
        elif (meth == 'ethaddr'):
            self.__setDeviceID(self.__settings['sys']['ethaddr'].replace(':', '').upper())
        elif (meth == 'partno'):
            self.__setDeviceID(self.__settings['sys']['partno'])
        elif (meth == 'uuid'):
            self.__setDeviceID(uuid.uuid1())
        else:
            log.warn('Unsupported Device ID creation method (%s)' % meth)

    def __setDeviceID(self, clksrvID):
        self.__settings['app']['%s_id' % self.__prefix] = clksrvID

    def __getDeviceID(self):
        return self.__settings['app']['%s_id' % self.__prefix]

    def __getDeviceIDCreationMethod(self):
        idCreationCfgName = '%s_id_creation' % self.__prefix
        if (idCreationCfgName not in self.__settings['app']):
            return None
        return self.__settings['app']['%s_id_creation' % self.__prefix]
