# -*- coding: utf-8 -*-
#
# Copyright 2023 Grosvenor Technology
#
"""Module to handle Online State and related web-service call

The OnlineState Thread regularly calls the 'onlinestate' end-point of the web-
service, and sets the global OnLineState value based on the response.

The expected response XML:

    <result>
        <isOnline>true</isOnline>
    </result>

The isOnline() function can be called to get the current state. 
"""
import threading
import httplib
from contextlib import closing
import xml.etree.cElementTree as ET

import log
from miscUtils import getElementText
# Wrapped to prevent circular reference issues. Issue occurs during manual/build_doc.py.
try:
    from webClient import commsHelper
except ImportError:
    log.dbg("Error while importing: {}".format(str(ImportError)))

_syncLock = threading.Lock()
_isOnline = False

def isOnline():
    return _isOnline

def setIsOnline(value):
    global _isOnline
    with _syncLock:
        log.dbg("isOnline: %s" % str(value))
        _isOnline = value

class OnlineState(threading.Thread):
    
    def __init__(self):
        super(OnlineState, self).__init__()
        self.__stopEvent = threading.Event()
        self.__lock = threading.Lock()
        self.__sleepTime = 120 * 1000 # Same as Android

    def run(self):
        log.dbg('OnlineState service started')
        self.__stopEvent.clear()
        while (not self.__stopEvent.isSet()):
            with self.__lock:
                try:
                    self.__update()
                except Exception as e:
                    log.err('Error while updating Online State (%s)' % e)
            self.__stopEvent.wait(self.__sleepTime)
        log.dbg('OnlineState service stopped')

    def start(self):
        if (not self.isAlive()):
            super(OnlineState, self).start()

    def stop(self):
        self.__stopEvent.set()
        self.join()

    def __update(self):
        try:
            with closing(commsHelper.openHttpConnection()) as conn:
                data = commsHelper.httpGet(conn, '/onlinestate')
        except httplib.HTTPException as e:
            log.err('Call to get online status failed: %s' % str(e))
    
        xml = ET.fromstring(data)
        value = getElementText(xml, 'isOnline', 'true').lower() == 'true'
        setIsOnline(value)
    
