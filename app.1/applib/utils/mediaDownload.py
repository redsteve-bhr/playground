# -*- coding: utf-8 -*-
#
# Copyright 2011 Grosvenor Technology
#
# 

"""
:mod:`mediaDownload` --- Media download
=======================================

.. versionadded:: 1.2
    
This module contains functions and classes to easily
download additional data. Downloading data via Clockserver
or CustomExchange is preferable but sometimes not possible.

This module implements a background thread which downloads 
and extracts ZIP files. It also checks for updates (e.g. new versions)
by using HTTP caching and local MD5 checksums.

.. note:: Please note that all files must be ZIP files! 

The background thread will perform the following actions periodically
for each configured URL:

    1. Send download (HTTP GET) request with E-Tag and Last-Modified-Date if available.
    2. Skip to next URL if HTTP response is "NOT MODIFIED" (304).
    3. Download file if HTTP response is "OK" (200).
    4. Save E-Tag and Last-Modified-Date.
    5. Create MD5 checksum of downloaded file.
    6. Skip to next URL if checksum is same as last one.
    7. Delete old extracted files.
    8. Extract all files from downloaded ZIP file.
    9. Call notification callbacks.

 
The following protocols are supported:
    - HTTP (e.g. http://host/file.zip)
    - HTTPS (e.g. https://host/file.zip)
    - File (e.g. file:///mnt/user/app/file.zip)
    
"""

import os
import log
import httplib
import urlparse
import thread
import time
import base64
import hashlib
import busyIndicator
import restartManager
import itg

from applib.utils import usbAccess

_mediaPathInternal = '/mnt/user/db'
_mediaPath = _mediaPathInternal
_mediaUsbAccess = None
_mediaList = {}
_changeLog = set()
_changeNotifier = {}
_health = None

def isChanged(mediaName):
    """ Returns **True** if the media *mediaName* changed.
    
    .. note:: This call also clears the changed flag, which means it
              should not be called from different parts of software
              for the same media.
    """
    if (mediaName in _changeLog):
        _changeLog.remove(mediaName)
        return True
    return False

def addChangeNotification(mediaName, cb):
    """ Add callback *cb* to notification list. The callback
    will be called when the media *mediaName* got updated. Only one callback per
    media is allowed and setting a second callback will replace the first one.
    
    All callbacks are stored as weak references.
    
    .. note:: The callback will be executed by :func:`itg.runLater` so 
              it runs within the UI thread. Which means that calls
              to UI functions are possible.
    
    Example::
    
        class IdleDialog(screensaver.ScreensaverMixin, itg.Dialog):
        
            def __init__(self):
                super(IdleDialog, self).__init__()
                # ...
                media = {}
                if (hasattr(itg, 'ScreensaverView')):            
                    media['screensaver'] = getAppSetting('scrnsvr_mediaurl')
                mediaDownload.startUpdateThread(media)                
                mediaDownload.addChangeNotification('screensaver', self.stopScreensaver)
                # ...
                self.enableScreensaver( getAppSetting('scrnsvr_timeout'), 
                                        getAppSetting('scrnsvr_time_per_image'))          

    The example above stops the screensaver when it is updated.

    """
    
    _changeNotifier[mediaName] = itg.WeakCb(cb)

def _notifyChange(mediaName):
    _changeLog.add(mediaName)
    if (mediaName not in _changeNotifier):
        return
    cbRef = _changeNotifier[mediaName]
    if (cbRef == None):
        return
    itg.runLater(cbRef)

def getFilename(mediaName, filename=None):
    """ Returns the absolute filename of a file *filename* 
    within media download *mediaName* or the directory name
    if *filename* is not given.
    
    Example::
    
        fn = mediaDownload.getFilename('screensaver', 'Slide1.png')
        # fn will most likely be '/mnt/user/db/screensaver/Slide1.png

    .. note:: Please note that no check will be performed whether the file
              actually exists. 
 
    .. versionchanged:: 2.4
      *filename* can be **None** or left off
    
    .. versionchanged:: 2.4
      For media with URLs starting with **usb://**, the first working USB memory device
      is mounted and the returned path points to the file on the USB device.
    
    """
    global _mediaUsbAccess
    if (mediaName in _mediaList):
        mediaUrl = _mediaList[mediaName]
        if (mediaUrl != None and mediaUrl.startswith('usb://')):
            if (_mediaUsbAccess == None):
                # try to mount if not done already
                try:
                    _mediaUsbAccess = usbAccess.USBAccess()
                except usbAccess.NoWorkingUSBDeviceFoundException:
                    log.warn('No working USB device found for %s.' % mediaName)
            usbPath = _mediaUsbAccess.getPath() if _mediaUsbAccess != None else '/mnt/no-usb'
            if (filename == None):
                return os.path.join(usbPath, mediaUrl[6:])
            return os.path.join(usbPath, mediaUrl[6:], filename)
    if (filename == None):
        return os.path.join(_mediaPath, mediaName)
    return os.path.join(_mediaPath, mediaName, filename)

def setMediaStorage(storage):
    """ Configure where the media download should store the loaded
    files. *storage* is a **String** and can be *internal* or *usb*. If *internal*
    is selected, files are stored in '/mnt/user/db/'. Files are stored on a 
    USB device in the directory 'IT-Media' if *storage* is set to *usb*.
    
    .. versionadded:: 2.4
    
    """
    global _mediaPath, _mediaUsbAccess
    if (storage == 'usb'):
        if (_mediaUsbAccess == None):
            _mediaUsbAccess = usbAccess.USBAccess()
        _mediaPath = os.path.join(_mediaUsbAccess.getPath(), 'IT-Media')
        if (not os.path.exists(_mediaPath)):
            os.makedirs(_mediaPath)
    else:
        _mediaUsbAccess = None
        _mediaPath = _mediaPathInternal
    

def getHealthObject():
    """ Returns health object for media downloader, which can be used
    with :mod:`applib.utils.healthMonitor`.
    """
    global _health
    if (_health == None):
        _health = Health()
    return _health 


class Health(object):
    
    def __init__(self):
        self.__medias = {}
    
    def getWarnings(self):
        if any(self.__medias.values()):
            return [{ 'msg': _('Download problems!') }]
        return []
        
    def getHealth(self):
        items = []
        for (k,v) in self.__medias.items():
            if (v == None):
                items.append((k, _('Good')))
            else:
                items.append((k, v))
        return (_('Media Downloads'), not any(self.__medias.values()), items)
    
    def reportError(self, mediaName, errMsg):
        self.__medias[mediaName] = errMsg
    
    def reportSuccess(self, mediaName):
        self.__medias[mediaName] = None


class _FileConnection(object):
    
    def request(self, method, url, body=None, header=None):
        self._method = method
        self._url    = url
        self._header = header
    
    def getresponse(self):
        return _FileResponse(self._url, self._header)


class _FileResponse(object):
    
    def __init__(self, url, header):
        self._header = {}
        try:
            self._header['last-modified'] = str(os.path.getmtime(url))
            if (header and ('If-Modified-Since' in header) and header['If-Modified-Since'] == self._header['last-modified']):
                self.status = 304
            else:
                self._file = open(url, 'rb')
                self.status = 200
        except Exception as e:
            log.warn('Error opening file %s: %s' % (url, e))
            self.status = 404
   
    def getheader(self, name, default=None):
        if (name in self._header):
            return self._header[name]
        return default
    
    def read(self, size):
        return self._file.read(size)


def _delete(name, mediaPath=None):
    if (mediaPath == None):
        mediaPath = _mediaPath
    path = os.path.join(mediaPath, name)
    log.dbg('Deleting %s media' % name)
    os.system("rm -rf '%s' " % path)
    for ftype in ('etag', 'date', 'md5', 'url'):
        fileName = '%s.%s' % (path, ftype)
        if (os.path.exists(fileName)):
            os.unlink(fileName)

def _getValue(mediaName, valueName):
    filename = os.path.join(_mediaPath, '%s.%s' % (mediaName, valueName))
    if (os.path.exists(filename)):
        return open(filename, 'r').read()
    return None

def _setValue(mediaName, valueName, value):
    log.dbg('Saving %s value for %s' % (valueName, mediaName))
    if (_getValue(mediaName, valueName) == value):
        log.dbg('Skip rewriting value %s of %s because it has not changed.' % (valueName, mediaName))
        return
    filename = os.path.join(_mediaPath, '%s.%s' % (mediaName,valueName))
    f = open(filename, 'w')
    if (value != None):
        f.write(value)
    f.close()

def _saveFile(destFilename, source):
    try:
        md5 = hashlib.md5()
        dst = open(destFilename, 'wb')
        log.dbg('Downloading media to %s' % destFilename)
        byteCounter = 0
        while True:
            data = source.read(10240)
            md5.update(data)
            byteCounter += len(data)
            if (not data):
                break
            dst.write(data)
        md5digest = md5.hexdigest() 
        log.dbg('Download of %s complete (%s bytes, MD5: %s)' % (destFilename, byteCounter, md5digest))
        return md5digest 
    except Exception as e:
        log.err('Failed to download file: %s' % (e,))
        os.unlink(destFilename)
        raise

def _unzipFiles(zipFile, destPath):
    log.dbg('Creating directory %s' % destPath)
    os.mkdir(destPath)
    log.dbg('Extracting files from %s' % zipFile)
    err = os.system("unzip -q '%s' -d '%s'" % (zipFile, destPath))
    log.dbg('Removing %s' % zipFile)    
    os.unlink(zipFile)
    if (err != 0):
        os.system("rm -rf '%s' " % destPath)
        raise Exception('Error unzipping %s (ERR:%s)' % (zipFile, err))

def _update(mediaName, urlstring):
    if (_mediaPath != _mediaPathInternal and os.path.exists(os.path.join(_mediaPathInternal, mediaName))):
        log.dbg('Deleting %s media from internal storage' % mediaName)
        _delete(mediaName, _mediaPathInternal)
    if (not urlstring or urlstring != _getValue(mediaName, 'url')):
        existed = os.path.exists(os.path.join(_mediaPath, mediaName))
        _delete(mediaName)
        if (existed):
            _notifyChange(mediaName)
        if (not urlstring):
            return
    url = urlparse.urlparse(urlstring)
    if (url.scheme == 'file'):
        c = _FileConnection()
    elif (url.scheme == 'https'):
        c = httplib.HTTPSConnection(url.hostname, url.port)
    elif (url.scheme == 'http'):
        c = httplib.HTTPConnection(url.hostname, url.port)
    else:
        raise Exception('Unsupported protocol (%s) for media download!' % (url.scheme,))
    headers = { 'Accept': '*/*'}
    etag = _getValue(mediaName, 'etag')
    date = _getValue(mediaName, 'date')
    if (etag):
        headers['If-None-Match'] = etag
    elif (date):
        headers['If-Modified-Since'] = date
    if (url.username):
        headers['Authorization'] = 'Basic %s' % (base64.encodestring('%s:%s' % (url.username, url.password))[:-1],)
    c.request('GET', url.path, None, headers)
    r = c.getresponse()
    if (r.status == httplib.NOT_MODIFIED):
        log.dbg('No updates for %s media' % mediaName)
    elif (r.status == httplib.OK):
        log.dbg('New %s media found, downloading...' % mediaName)
        etag = r.getheader('etag', None)
        date = r.getheader('last-modified', None)
        if (etag or date):
            with restartManager.PreventRestartLock():
                with (busyIndicator.BusyIndicator('Updating %s' % mediaName)):
                    zipFile = os.path.join(_mediaPath, '%s.zip' % mediaName)
                    zipDest = os.path.join(_mediaPath, mediaName)
                    md5sum = _saveFile(zipFile, r)
                    if (md5sum == _getValue(mediaName, 'md5')):
                        log.dbg('Downloaded %s but data has not changed' % mediaName)
                        os.unlink(zipFile)
                    else:
                        _delete(mediaName)
                        _unzipFiles(zipFile, zipDest)
                    _setValue(mediaName, 'url', urlstring)
                    _setValue(mediaName, 'etag', etag)
                    _setValue(mediaName, 'date', date)
                    _setValue(mediaName, 'md5', md5sum)
                    _notifyChange(mediaName)
        else:
            raise Exception('Server does not support ETAG or last-modified, not loading media!')
    else:
        raise Exception('Error loading %s media: HTTP %s' % (mediaName, r.status))


def updateMediaNow(mediaName, urlstring):
    try:
        _update(mediaName, urlstring)
        getHealthObject().reportSuccess(mediaName)
    except Exception as e:
        log.err('Failed to update media %s: %s' % (mediaName, e))
        getHealthObject().reportError(mediaName, str(e))        


def _updateThread(updateInterval):
    log.dbg('Media update thread started...')
    time.sleep(5)
    while True:
        for mediaName, url in _mediaList.items():
            if (not mediaName):
                continue
            elif (url.startswith('usb://')):
                continue
            log.dbg('Checking for updates in %s (%s)' % (mediaName, url))
            updateMediaNow(mediaName, url)
        time.sleep(updateInterval)
 
def startUpdateThread(mediaList, updateInverval=60*60):
    """ Start media download thread. *mediaList* is a **dictionary** which
    must contain all URLs. *updateInterval* is the time between checking for 
    updates in seconds.
    """
    global _mediaList
    _mediaList = mediaList
    if (not mediaList):
        return
    thread.start_new_thread(_updateThread, (updateInverval,))
