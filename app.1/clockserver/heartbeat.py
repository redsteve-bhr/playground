# -*- coding: utf-8 -*-
#
# Copyright 2011 Grosvenor Technology
#

import threading
import datetime
import log
import xml.etree.cElementTree as ET
import time
import os
import re
import base64
import appit
import updateit
import cfg
import netinfo
import calendar

from clockserver import xmlTime, comm
from engine import fileHandler
from engine.actionRequestParams import ActionRequestParams
from cloudStorage import csComm

from applib.utils import busyIndicator, restartManager, timeUtils
from applib.db import tblSettings, sqlTime

_hb1 = None
_hb2 = None

def getAppPrimaryHeartbeat():
    global _hb1
    if (_hb1 == None):
        _hb1 = _createAppHeartbeat('clksrv')
    return _hb1

def getAppSecondaryHeartbeat():
    global _hb2
    if (_hb2 == None):
        _hb2 = _createAppHeartbeat('clksrv2')
        if (_hb2 != None):
            _hb2.setStartDelay(2)
    return _hb2

def getAppHeartbeatForEnquiries():
    clksrv1Functions = tblSettings.getAppSetting('clksrv_functions')
    clksrv2Functions = tblSettings.getAppSetting('clksrv2_functions')
    if (clksrv1Functions != None and 'enq' in clksrv1Functions):
        if ('hb' in clksrv1Functions):
            return getAppPrimaryHeartbeat()
    elif (clksrv2Functions != None and 'enq' in clksrv2Functions):
        if ('hb' in clksrv2Functions):
            return getAppSecondaryHeartbeat()
    return None
    

def _createAppHeartbeat(prefix):
    hbFunctions = tblSettings.getAppSetting('%s_functions' % prefix)
    if (hbFunctions == None or 'hb' not in hbFunctions):
        return None
    timeout   = tblSettings.getAppSetting('%s_hb_period' % prefix)
    warnlevel = tblSettings.getAppSetting('%s_hb_warn_level' % prefix)
    appInfo   = appit.AppInfo()
    version   = "%s,%s,%s" % (appInfo.version(),
                    updateit.get_version(),
                    updateit.get_build_date())
    
    # Note, the time sync from the heartbeat can occur even if the NTP server is running
    updateTime = tblSettings.getAppSetting('%s_set_time_via_hb' % prefix)
    keepAliveEnabled = tblSettings.getAppSetting('%s_hb_keep_alive' % prefix)    
    printStatistics  = tblSettings.getAppSetting('%s_hb_show_stats' % prefix)
    heartbeat = Heartbeat(timeout, version, warnlevel, updateTime, keepAliveEnabled, printStatistics)
    return heartbeat


def testConnection(proto, host, port, path, psk, skip):
    try:
        term = updateit.get_type()
        mac  = cfg.get(cfg.CFG_NET_ETHADDR).replace(":", "").upper()
        com  = comm.Comm(proto, host, path, port, psk, skipCC=skip)
        com.setup(None, term, mac)
        appInfo   = appit.AppInfo()
        version   = "%s,%s,%s" % (appInfo.version(),
                        updateit.get_version(),
                        updateit.get_build_date())
        hb = Heartbeat(120, version, updateTime=False)
        hb.comm = com
        hb.sendHeartbeat()
    except Exception as e:
        return str(e)
    return None

def testConfiguredConnection():
    for (prefix, name) in ( ('clksrv', 'primary clockserver') , ('clksrv2', 'secondary clockserver')):
        hbFunctions = tblSettings.getAppSetting('%s_functions' % prefix)
        if (hbFunctions == None or 'hb' not in hbFunctions):
            continue
        log.dbg('Testing heartbeat connection for %s' % name)
        proto = tblSettings.getAppSetting('%s_proto' % prefix)    
        host  = tblSettings.getAppSetting('%s_host' % prefix)
        port  = tblSettings.getAppSetting('%s_port' % prefix)
        path  = tblSettings.getAppSetting('%s_resource' % prefix)
        psk   = tblSettings.getAppSetting('%s_psk' % prefix)
        skip  = tblSettings.getAppSetting('%s_skip_https_certificate_checking' % prefix)
        result = testConnection(proto, host, port, path, psk, skip)
        if result:
            return '%s failed: %s' % (name, result)
    return None


class Heartbeat(threading.Thread):
    """
    In order to create a heartbeat, a ClockServer Comm object is required 
    for sending the heartbeat. In addition to this a period and version
    string is needed. The period specifies how often the heartbeat is 
    sent. The version string holds a comma separated list of versions
    useful for the ClockServer.
    
    :param period:      is the period of the heartbeat in seconds
    :param verStr:      is a comma separated string containing version 
                        informations
    :param warnlevel:   is the number of seconds of continues heartbeat
                        failures after which to report a warning
    :param updateTime:  if true, the heartbeat will set the system time
                        from the time it gets via the heartbet
    """
    def __init__(self, period, verStr, warnlevel=1, updateTime=True, keepAliveEnabled=False, printStatistics=False):
        super(Heartbeat, self).__init__()
        self.running    = False
        self.cond       = threading.Condition()
        self.period     = int(period)
        self.delay      = 0
        self.version    = verStr
        self.heartbeatReq = False
        self.updateTime = updateTime

        self.warnLevel    = int(warnlevel)
        self.lastErrorMsg = None
        self.lastTry      = None
        self.lastError    = None
        self.lastSuccess  = None
        self.startupTime  = time.time()
        self.failed = False
        
        self.keepAliveConn    = None
        self.keepAliveEnabled = keepAliveEnabled
        self.printStatistics  = printStatistics

        
    def setStartDelay(self, delay):
        """ Delay in seconds before sending first heartbeat. """
        self.delay = delay
                
    def start(self, comm):
        """Start heartbeat thread.
        
        :param comm: is a ClockServer Comm object
        """
        self.comm = comm
        if (comm != None):
            super(Heartbeat, self).start()


    def stop(self, timeout=5):
        """Stop heartbeat thread.
        
         :param timeout: in seconds
        """
        log.dbg("Stopping thread...")
        with self.cond:
            self.running = False
            self.cond.notify()
        if (not self.isAlive()):
            log.dbg("Not stopping heartbeat, not running")
        elif (self.name == threading.currentThread().name):
            log.dbg("Not stopping heartbeat, can't stop myself")
        else:
            self.join(timeout)

        
    #-[private]-----------------------------------------------------------------
    def run(self):

        self.running = True
        with self.cond:
            self.cond.wait(self.delay)
        
        log.dbg("Heartbeat thread started, sending via %s" % self.comm.getName())
        
        # initial HB period
        hbPeriod = 15

        while (self.running):
            try:
                if (not self.heartbeatReq):
                    self.statisticsStart()
                    
                self.heartbeatReq = False
                self.lastTry = time.time()

                rsp = self.sendHeartbeat()
                with restartManager.PreventRestartLock():
                    self.handleResponse(rsp)

                self.failed = False
                self.lastSuccess = time.time()
                self.statHeartbeatCounter += 1

                if (self.heartbeatReq):
                    continue
                self.keepAliveConn = None
                self.statisticsStop()
                                
            except Exception as e:
                log.err("Sending heartbeat failed: %s" % str(e))
                self.lastError    = time.time()
                self.lastErrorMsg = str(e)
                self.failed = True
                self.keepAliveConn = None

            with self.cond:
                self.cond.wait(hbPeriod)
            hbPeriod = self.period

        log.dbg("Exiting thread")
        
    def sendHeartbeat(self):
        """ Send a heartbeat message

         This function sends a heartbeat and returns the response. This
         function is normally called by the heartbeat thread, but it can
         also be used to test the connection.
        """
        log.dbg("Sending heartbeat via %s" % self.comm.getName())

        time = xmlTime.getXMLTimestampNow()
        if (not self.comm.useTimeZoneOffset()):
            time = time[0:19]
            
        if (self.keepAliveEnabled and self.keepAliveConn == None):
            self.keepAliveConn = self.comm.getConnection()

        # convert from the padded format
        netIP = '.'.join( [ str(int(i,10)) for i in netinfo.get_info().ip4_addr.split(".") ] )
        
        rsp = self.comm.send('    <heartbeat>\n'
                             '      <time>%s</time>\n'
                             '      <verInfo>%s</verInfo>\n'
                             '      <infos>\n'
                             '        <info id="net.ip">\n'
                             '          <label>IP address</label>\n'
                             '         <value>%s</value>\n'
                             '        </info>\n'
                             '      </infos>\n'
                             '    </heartbeat>\n'
                        % (time, self.version, netIP), conn=self.keepAliveConn)
        return rsp

    #-[private]-----------------------------------------------------------------
    def handleResponse(self, rsp):
        # parse XML
        root = ET.fromstring(rsp)

        # check for time
        for el in root.findall('heartbeatRsp/time'):
            if (el.text):
                self.setTime(el.text)

        # check for download file from the server
        for el in root.findall('heartbeatRsp/downloadFile'):
            if (el.text):
                with busyIndicator.BusyIndicator(_('Downloading %s') % el.text):
                    self.downloadFileFromServer(el.text)
                    self.statFileDownloadCounter += 1

        # check for upload file from the server
        for el in root.findall('heartbeatRsp/uploadFile'):
            if (el.text):
                with busyIndicator.BusyIndicator(_('Uploading %s') % el.text):                
                    self.uploadFileToServer(el.text)
                    self.statFileUploadCounter += 1
                    
        # check for upload file to Cloud Storage from the server
        for el in root.findall('heartbeatRsp/uploadFileToCloud'):
            for child in list(el):
                with busyIndicator.BusyIndicator(_('Uploading %s') % child.tag):                
                    self.uploadFileToCloudStorage(child.tag)
                    self.statFileUploadCounter += 1
                    
        # check for Action Request from the server
        for el in root.findall('heartbeatRsp/actionRequest'):
            for child in list(el):
                with busyIndicator.BusyIndicator(_('Action %s') % child.tag):
                    params = ActionRequestParams()
                    params.read(el)
                    self.handleActionRequest(child.tag, params)
                    
        # check for delete file from the server
        for el in root.findall('heartbeatRsp/deleteFile'):
            if (el.text):
                self.deleteFile(el.text)
                self.statFileDeleteCounter += 1

        for el in root.findall('heartbeatReq'):
            if (el.text == '1'):
                self.heartbeatReq = True

    #-[private]-----------------------------------------------------------------

    def setTime(self, xmlTime):
        """ Set the time

        Set the time to the UTC time received in the heartbeat if it is more than
        10 minutes out of sync so as not to fight the NTP server.
         <heartbeatRsp>
           <time>2023-07-26T16:07:56</time>
         </heartbeatRsp>
        """
        if (not self.updateTime):
            return
        log.dbg("Heartbeat time is %s" % xmlTime)
        hbTime = timeUtils.getUTCDatetimeFromISO8601(xmlTime + 'Z').utctimetuple()
        # Convert to unix time seconds
        newTime = calendar.timegm(hbTime)
        curTime = time.time()
        difTime = abs(newTime - curTime)

        log.dbg("Time difference to server time is %s (currentTime = %s, serverTime = %s)" % (difTime, curTime, newTime))

        if (difTime > 600):
            newTime = time.strftime("%Y.%m.%d-%H:%M:%S", hbTime)
            log.info("Setting time from server (%s)" % newTime)
            os.system("date -s %s > /dev/null" % newTime)


    #-[private]-----------------------------------------------------------------
    def downloadFileFromServer(self, requestDownloadFile):
        try:
            # download file and process response
            startTime = time.time()
            rsp  = self.comm.send("    <requestDownloadFile>%s</requestDownloadFile>\n" % requestDownloadFile, False, conn=self.keepAliveConn)
            endTime = time.time()
            log.dbg('File %s downloaded in %.2f seconds.' % (requestDownloadFile, endTime - startTime))
            root = ET.fromstring(rsp)
            del rsp
            for payload in root.findall('downloadFile/payload'):
                payloadFileName = payload.find('fileName').text
                data = base64.decodestring(payload.find('data').text)
    
                handled = False
                restartReqManager = fileHandler.RestartRequestManager()
                for handler in fileHandler.getAllFileHandlersForFile(payloadFileName):
                    if not hasattr(handler, 'fileImport'):
                        continue
                    startTime = time.time()
                    handler.fileImport(payloadFileName, data, restartReqManager)
                    endTime = time.time()
                    log.dbg('File %s imported in %.2f seconds.' % (payloadFileName, endTime - startTime))
                    handled = True
                if (not handled):
                    log.err('No file handler for %s' % payloadFileName)
                elif (restartReqManager.isRebootRequested()):
                    restartManager.reboot(300, _('Rebooting terminal because system configuration has changed.'))
                elif (restartReqManager.isRestartRequested()):
                    restartManager.restart(300, _('Restarting application because settings changed'))
            for el in root.findall('heartbeatReq'):
                if (el.text == '1'):
                    self.heartbeatReq = True
        except Exception as e:
            log.err('Error while downloading and handling %s: %s' % (requestDownloadFile, e))

    #-[private]-----------------------------------------------------------------
    def sendUploadFileToServer(self, fileName, payload):
        log.dbg("Sending file (%s) to server" % fileName)
        
        data = '    <uploadFile>\n'     \
                '        <payload>\n'   \
                '            <fileName>%s</fileName>\n'    \
                '            <data>\n'    \
                '                <![CDATA[\n%s'    \
                '                ]]>\n'    \
                '            </data>\n'    \
                '        </payload>\n'    \
                '    </uploadFile>\n'   \
                % (fileName, base64.encodestring(payload))
        
        rsp = self.comm.send(data, True, conn=self.keepAliveConn)
        return rsp

    #-[private]-----------------------------------------------------------------
    def uploadFileToServer(self, fileName):
        try:

            for handler in fileHandler.getAllFileHandlersForFile(fileName):
                if not hasattr(handler, 'fileExport'):
                    continue
                payload = handler.fileExport(fileName)
                rsp = self.sendUploadFileToServer(fileName, payload)
                self.handleResponse(rsp)
        except Exception as e:
            log.err('Error while uploading %s: %s' % (fileName, e))

    #-[private]-----------------------------------------------------------------
    def getFilenameForTag(self, tag):
        tag = tag.strip()
        fileMap = {
            'buttons': 'buttons.xml',
            'dataCollection': 'dataCollection.xml',
            'employeesReport': 'employeesReport.csv',
            'relays': 'relays.xml',
            'resendClockings': 'resendClockings.xml',
            'clearClockings': 'clearClockings.xml',
            'restartApp': 'apprestart.xml',
            'reboot': 'reboot.xml',
            'ntpTest': 'ntpTest.txt',
            'traceRoute': 'traceRoute.txt'
        }
        if tag in fileMap:
            return fileMap[tag]
        else:
            return None
        
    #-[private]-----------------------------------------------------------------
    def requiresUpload(self, tag):
        tag = tag.strip()
        if tag in ['ntpTest', 'traceRoute']:
            return True
        else:
            return False

    #-[private]-----------------------------------------------------------------
    def uploadFileToCloudStorage(self, tag, params=None):
        try:
            supported = False
            fileName = self.getFilenameForTag(tag)
            if fileName is not None:
                baseFileName, ext = os.path.splitext(fileName)
                for handler in fileHandler.getAllFileHandlersForFile(fileName):
                    if not hasattr(handler, 'fileExport'):
                        continue
                    if hasattr(handler, 'fileParams'):
                        handler.fileParams(params)
                    supported = True
                    payload = handler.fileExport(fileName)
                    timestamp = re.sub(' ', 'T', sqlTime.localTime2SqlTime(datetime.datetime.now()))
                    completeFileName = baseFileName + "_" + re.sub(':', '-', timestamp[:19]) + ext
                    rsp = csComm.send(completeFileName, payload)
                    # We can't handle the response in the normal way, because it is
                    # coming from the Cloud Storage, not from Custom Exchange
                    # self.handleResponse(rsp)
            if not supported:
                log.warn('Unsupported file-type requested: "%s"' % tag)
        except Exception as e:
            log.err('Error while uploading %s: %s' % (fileName, e))

    #-[private]-----------------------------------------------------------------
    def handleActionRequest(self, tag, params):
        """Locate and run the file-handler associated with the action request
        identified by the supplied tag.
        """
        try:
            supported = False
            if self.requiresUpload(tag):
                self.uploadFileToCloudStorage(tag, params)
            else:
                fileName = self.getFilenameForTag(tag)
                if fileName is not None:
                    for handler in fileHandler.getAllFileHandlersForFile(fileName):
                        if not hasattr(handler, 'fileImport'):
                            continue
                        supported = True
                        restartReqManager = fileHandler.RestartRequestManager()
                        handler.fileImport('', params, restartReqManager)
                        if (restartReqManager.isRebootRequested()):
                            restartManager.reboot(300, _('Rebooting terminal because system configuration has changed.'))
                        elif (restartReqManager.isRestartRequested()):
                            restartManager.restart(300, _('Restarting application because settings changed'))
                if not supported:
                    log.warn('Unsupported action request: "%s"' % tag)
        except Exception as e:
            log.err('Error while processing action request "%s": %s' % (fileName, e))

    #-[private]-----------------------------------------------------------------
    def deleteFile(self, fileName):
        try:
            for handler in fileHandler.getAllFileHandlersForFile(fileName):
                if not hasattr(handler, 'fileDelete'):
                    continue
                handler.fileDelete(fileName)
                self.heartbeatReq = True
        except Exception as e:
            log.err('Error while handling delete request for %s: %s' % (fileName, e))

    #-[HealthMonitor]-----------------------------------------------------------------
    def getWarnings(self):
        """ Return current warnings. """
        if not self.failed:
            return []
        if (self.lastSuccess):
            diff = time.time() - self.lastSuccess
        else:
            diff = time.time() - self.startupTime
        if (diff < self.warnLevel):
            return []
        return [{ 'msg': _('Heartbeat failed') }]
        
    #-[HealthMonitor]-----------------------------------------------------------------
    def getHealth(self):
        """ Return current health status. """
        if (self.comm):
            name = _('Heartbeat (%s)') % self.comm.getName()
        else:
            name    = _('Heartbeat (unconfigured)')
        healthy = (len(self.getWarnings()) == 0)

        lastTry     = "None"
        lastError   = "None"
        lastSuccess = "None"

        if (self.lastTry):
            lastTry = time.strftime('%x %X', time.localtime(self.lastTry))

        if (self.lastError):
            lastError = time.strftime('%x %X', time.localtime(self.lastError))

        if (self.lastSuccess):
            lastSuccess = time.strftime('%x %X', time.localtime(self.lastSuccess))

        items   = ( (_('Device ID'),           self.comm.id if self.comm else 'not set'),
                    (_('Last error message'),  self.lastErrorMsg),
                    (_('Last try'),            lastTry),
                    (_('Last error'),          lastError),
                    (_('Last success'),        lastSuccess))

        return (name, healthy, items)

    #-[Statistics]--------------------------------------------------------------------
    def statisticsStart(self):
        self.statHeartbeatCounter    = 0
        self.statFileDownloadCounter = 0
        self.statFileUploadCounter   = 0
        self.statFileDeleteCounter   = 0
        self.statHBSessionStart = time.time()
        self.statHBSessionEnd   = 0

    #-[Statistics]--------------------------------------------------------------------
    def statisticsStop(self):
        self.statHBSessionEnd = time.time()
        if (self.printStatistics and self.statHeartbeatCounter > 1):
            name = self.comm.getName() if self.comm else 'unconfigured'
            totalTime  = self.statHBSessionEnd - self.statHBSessionStart
            totalFiles = self.statFileDeleteCounter + self.statFileUploadCounter + self.statFileDownloadCounter 
            log.info('Heartbeat (%s) session statistics:' % name)
            log.info('Files downloaded : %d' % self.statFileDownloadCounter)
            log.info('Files uploaded   : %d' % self.statFileUploadCounter)
            log.info('Files deleted    : %d' % self.statFileDeleteCounter)
            log.info('Total Time       : %.2f seconds' % totalTime)
            log.info('Time per HB+File : %.2f seconds' % (totalTime/totalFiles))

