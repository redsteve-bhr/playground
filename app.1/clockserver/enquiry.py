# -*- coding: utf-8 -*-
#
# Copyright 2011 Grosvenor Technology
#

import log
import xml.etree.cElementTree

from applib.db import tblSettings, sqlTime
from applib.utils import jobs
from clockserver import getAppHeartbeatForEnquiries, getCommForFunction

_enqJobQueue = None
_enqTimeout  = None

def getAppEnquiryQueue(create=True):
    global _enqJobQueue
    if (_enqJobQueue == None and create):
        _enqJobQueue = jobs.JobQueue('Enquiry Job Queue')
    return _enqJobQueue

def getEnquiryTimeout():
    global _enqTimeout
    if (_enqTimeout == None):
        clksrv1Functions = tblSettings.getAppSetting('clksrv_functions')
        clksrv2Functions = tblSettings.getAppSetting('clksrv2_functions')
        if (clksrv1Functions != None and 'enq' in clksrv1Functions):
            log.dbg('Using primary clockserver for enquiries')
            prefix = 'clksrv'
        elif (clksrv2Functions != None and 'enq' in clksrv2Functions):
            log.dbg('Using secondary clockserver for enquiries')            
            prefix = 'clksrv2'
        else:
            log.warn('No clockserver configured for enquiries, using primary one!')
            prefix = 'clksrv'

        _enqTimeout = tblSettings.getAppSetting('%s_enq_timeout' % prefix)        
    return _enqTimeout

    

#-------------------------------------------------------------------------------
class EnquiryJob(jobs.Job):
    """Enquiry class for sending enquiries."""

    def __init__(self, enqData, enqTimestamp):
        super(EnquiryJob, self).__init__(enqData)
        self._enqData = enqData
        self._enqTimestamp = enqTimestamp
        self._enqResponse = None

    #-----------------------------------------------------------------------
    def _sendEnqMsg(self):
        comm = getCommForFunction('enq')
        if (comm == None):
            raise Exception('No server configured for enquiries!')
        log.dbg('Sending enquiry request %s' % self.getName())
        localTime = sqlTime.sqlTime2MyLocalTime(self._enqTimestamp, '%Y-%m-%dT%H:%M:%S%z')
        if (not comm.useTimeZoneOffset()):
            localTime = localTime[0:19]
        rsp = comm.send("<enq><data>%s</data><time>%s</time></enq>" % (self._enqData, localTime), timeout=getEnquiryTimeout())
        # parse XML
        root = xml.etree.cElementTree.fromstring(rsp)
        enqRsp = {}
        for el in root.findall('enqRsp'):
            for line in el.getchildren():
                text = line.text if line.text else ''
                enqRsp[line.tag] = text
        self._enqResponse = enqRsp

    def _checkHeartbeat(self):
        hb = getAppHeartbeatForEnquiries()
        if (hb and hb.comm):
            log.dbg('Checking health of %s heartbeat before sending enquiry' % hb.comm.getName())
            if (hb.failed):
                log.err('Enquiry %s cancelled because %s heartbeat failed' % (self.getName(), hb.comm.getName()))
                raise Exception('Enquiries not available due to %s heartbeat errors.' % hb.comm.getName())
    
    def execute(self):
        self._checkHeartbeat()
        self._sendEnqMsg()
        log.dbg('Got response for enquiry request %s' % self.getName())

    def wait(self, timeout=None):
        if (timeout == None):
            timeout = getEnquiryTimeout()
        super(EnquiryJob, self).wait(timeout)

    def getResponse(self):
        return self._enqResponse
    