# -*- coding: utf-8 -*-
#
# Copyright 2023 Grosvenor Technology
#

import appit
import log
try:
    import syslog #@UnresolvedImport
except:
    pass
import appMonitor

# Pseudo-enumeration of Event and Metric types
EVT_APP_STARTUP = "app_startup"
EVT_APP_SCHEDULED_RESTART = "app_event_scheduled_restart"
EVT_APP_SCHEDULED_REBOOT = "app_event_scheduled_reboot"
EVT_FINGER_CONSENT_EXPIRED = "finger_consent_expired"

MTX_APP_UPTIME = "app_uptime"
MTX_APP_UPTIME_SECONDS = "app_uptime_seconds"
MTX_SYS_UPTIME_SECONDS = "sys_uptime_seconds"
MTX_SYS_MEMORY_FREE = "sys_memory_free"
MTX_SYS_MEMORY_FREE_PERCENT = "sys_memory_free_percent"

def gtLog(mtxName, mtxValue, mtxType):
    """Adds a GtConnect-compatible metrics log entry"""
    if not mtxType in ["i", "d", "s"]:
        log.err("Invalid GtConnect MTX type: {}".format(mtxType))
        return
    logStr = 'MTX {"n":"%s","v":"%s","vt":"%s"}' % (mtxName, str(mtxValue), mtxType)
    syslog.syslog(syslog.LOG_INFO, logStr)

def gtEvent(event, properties=None):
    """Adds a GtConnect-compatible event log entry"""
    appInfo = appit.AppInfo()
    source = "app.%s" % appInfo.name().lower()
    if properties is not None:
        pString = "{"
        for prop in properties:
            pString += '"%s":"%s"' % (prop, properties[prop])
        pString += "}"
    else:
        pString = None

    if pString is not None:            
        logStr = 'EVT {e:"%s",t:"%s",p:%s}' % (source, event, pString)
    else:
        logStr = 'EVT {e:"%s",t:"%s"}' % (source, event)
    syslog.syslog(syslog.LOG_INFO, logStr)
    
def mtxReport():
    """Reports on various system metrics"""
    memTotal, memFree, valid = appMonitor.getMemFree()
    if valid:
        gtLog(MTX_SYS_MEMORY_FREE, memFree, "i")

        percent = (float(memFree) / float(memTotal)) * 100
        gtLog(MTX_SYS_MEMORY_FREE_PERCENT, percent, "d")
        
    uptime, valid = appMonitor.getSysUptime()
    if valid:
        gtLog(MTX_SYS_UPTIME_SECONDS, uptime, "d")
        
    appUptime = appMonitor.getAppUptime()
    gtLog(MTX_APP_UPTIME, appUptime, "s")
    gtLog(MTX_APP_UPTIME_SECONDS, appMonitor.getAppMonitor().uptime(), "i")
