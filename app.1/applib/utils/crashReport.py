# -*- coding: utf-8 -*-
#
# Copyright 2011 Grosvenor Technology
#


import sys
import log
import traceback
import updateit
import appit
import cfg
import os
import subprocess
import time
from applib.db.tblSettings import getAppSetting
from applib.db import sqlTime

_crashReportFilename = '/mnt/user/db/crash.report'
_origExcepthook = None

def start():
    global _origExcepthook                                            
    if (sys.excepthook != excepthook):
        _origExcepthook = sys.excepthook
    sys.excepthook = excepthook
    if (os.path.exists(_crashReportFilename)):
        log.info('Crash report found!')
    # remove old crash reports
    _removeOldCrashReports()
    # keep up to 10 crash reports
    _backupCrashReport()

def _removeOldCrashReports():
    """ Remove crash report and backups that are older than 90 days. """
    crashFiles = [ '%s-%d' % (_crashReportFilename, i) for i in xrange(10) ]
    crashFiles.append(_crashReportFilename)
    for cr in crashFiles:
        try:
            if (not os.path.exists(cr)):
                continue
            # get date of crash report
            t = time.time() - os.path.getmtime(cr)
            t /= 60*60*24
            log.dbg('Crash report %s is %s days old' % (cr, int(t)))
            if (t > 90):
                log.info('Deleting old crash report %s' % cr)
                os.unlink(cr)
        except Exception as e:
            log.warn('Error while checking %s: %s' % (cr, e))

def _backupCrashReport():
    """ Create backup of crash report and remove original. Only
        10 backups are kept.
    """
    if (not os.path.exists(_crashReportFilename)):
        return
    try:
        crashFiles = [ '%s-%d' % (_crashReportFilename, i) for i in xrange(10) ]
        for cr in crashFiles:
            if (not os.path.exists(cr)):
                log.info('Renaming crash report to %s' % cr)
                os.rename(_crashReportFilename, cr)
                return
        log.dbg('Already got %s crash report backups' % len(crashFiles))
    except Exception as e:
        log.warn('Failed to backup crash report: %s' % e)

def excepthook(exctype, value, tb):
    try:
        createCrashReport(exctype, value, tb)
    except Exception as e:
        log.err('Error creating crash report (%s)' % e)
    _origExcepthook(exctype, value, tb)

def createCrashReportFromException():
    (exc_type, exc_value, exc_tb) = sys.exc_info()
    createCrashReport(exc_type, exc_value, exc_tb)

def createCrashReport(exctype, value, tb):
    if (os.path.exists(_crashReportFilename)):
        log.warn('Unable to save crash report (already exists)!')
        return
    log.info('Creating crash report...')
    formattedException = traceback.format_exception(exctype, value, tb)
    timestamp = sqlTime.getSqlTimestampNow()
    appInfo = appit.AppInfo()
    msg = """
Crash Report
============

Firmware     : %s (%s)
Application  : %s (%s)
SystemID     : %s
MAC address  : %s
PartNo       : %s
PCB Revision : %s
HW Tested    : %s
DeviceID     : %s
Timestamp    : %s


Filesystem Info
---------------

%s

Memory Info
-----------

%s

Exception Details
-----------------

%s

System Log
----------

%s

""" % (updateit.get_version(),
       updateit.get_build_date(),
       appInfo.name(),
       appInfo.version(),
       cfg.get(cfg.CFG_SYSTEM_ID),
       cfg.get(cfg.CFG_NET_ETHADDR),       
       cfg.get(cfg.CFG_PARTNO).decode('iso8859-1'),
       cfg.get(cfg.CFG_PCB_REVISION),
       cfg.get(cfg.CFG_HW_TESTED),
       getAppSetting('clksrv_id'),
       timestamp,
       subprocess.Popen(['/bin/df', '-h'], stdout=subprocess.PIPE).communicate()[0],
       subprocess.Popen(['/usr/bin/free'], stdout=subprocess.PIPE).communicate()[0],
       ''.join(formattedException),
       '\n'.join(subprocess.Popen(['/sbin/logread'], stdout=subprocess.PIPE).communicate()[0].splitlines()[-25:]))
    path = os.path.dirname(_crashReportFilename)
    if (not os.path.exists(path)):
        os.makedirs(path)
    open(_crashReportFilename, 'w').write(msg)


