# -*- coding: utf-8 -*-
#
# Copyright 2013 Grosvenor Technology
#
import itg
import log
from applib.utils import healthMonitor, mediaDownload
from applib.db.tblSettings import getAppSetting, SettingsSection, ListSetting


def loadPlugin():
    pass

def startPlugin():
    try:
        storage = getAppSetting('app_media_storage') 
        mediaDownload.setMediaStorage(storage)
    except Exception as e:
        log.err('Failed to configure media storage location: %s' % e)
        return
    media = {}
    if (hasattr(itg, 'ScreensaverView')):            
        media['screensaver'] = getAppSetting('scrnsvr_mediaurl')
    mediaDownload.startUpdateThread(media)
    hm = healthMonitor.getAppHealthMonitor()
    hm.add(mediaDownload.getHealthObject())


def getSettings():
    sectionName = 'App Settings'
    sectionComment = 'These are the settings for the generic terminal application parameters.'
    appSection = SettingsSection(sectionName, sectionComment)
    s = ListSetting(appSection,
            name     = 'app_media_storage',
            label    = 'Media storage',
            data     = 'internal',
            comment  = ('Specifies where to store files download by media downloader (e.g. '
                        'screensaver files). If USB is selected, files are stored inside the '
                        '"IT-Media" directory.' ))
    s.addListOption('internal', 'Internal')
    s.addListOption('usb', 'USB')
    return [appSection,]