# -*- coding: utf-8 -*-
#
# Copyright 2023 Grosvenor Technology
#

import threading
import random
import datetime
from datetime import timedelta

import log
from applib.db.tblSettings import getAppSettings, getAppSetting, SettingsSection, TextSetting, ListSetting, MultiListSetting, NumberSetting
from applib.utils import restartManager
import gtmetrics 

_monitor = None

def getSettings():
    sectionName = "Maintenance"
    # sectionComment = "These are settings for the terminal maintenance routines"
    maintenanceSection = SettingsSection(sectionName)

    s = ListSetting(maintenanceSection,
            name     = 'maintenance_schedule_event', 
            label    = 'Maintenance Schedule', 
            data     = 'reboot', 
            comment  = ('Define daily restart.'))
    s.addListOption('off', 'Off')
    s.addListOption('apprestart', 'Restart Application')
    s.addListOption('reboot', 'Reboot Terminal')

    s = MultiListSetting(maintenanceSection,
            name     = 'maintenance_schedule_dow',
            label    = 'Day of the Week',
            data     = 'sun',
            comment  = ('Day on which to run the Daily Restart' ))
    s.addListOption('mon', 'Mon')
    s.addListOption('tue', 'Tue')
    s.addListOption('wed', 'Wed')
    s.addListOption('thu', 'Thu')
    s.addListOption('fri', 'Fri')
    s.addListOption('sat', 'Sat')
    s.addListOption('sun', 'Sun')
    
    TextSetting(maintenanceSection,
            name     = 'maintenance_schedule_time', 
            label    = 'Restart Time', 
            data     = '03:15', 
            comment  =  ('Time of day at which to restart or reboot. Example: 03:00'))
    
    t = TextSetting(maintenanceSection,
            name     = 'maintenance_last_restart_time', 
            label    = 'Last Restart', 
            data     = '', 
            comment  =  ('Date of last restart'))
    t.setAllowEdit(False)
    t.setHideInEditor(True)

    NumberSetting(maintenanceSection,
            name     = 'maintenance_monitor_period', 
            label    = 'Maintenance Monitor Period', 
            data     = '30',
            units    = 'sec', 
            comment  = ('How often (in seconds) to check application health'))
    
    NumberSetting(maintenanceSection,
            name     = 'maintenance_reporting_period', 
            label    = 'Maintenance Reporting Period', 
            data     = '14400', # 4 hour
            units    = 'sec', 
            comment  = ('How often (in seconds) to report application health'))
    
    NumberSetting(maintenanceSection,
            name     = 'maintenance_allowed_uptime_days', 
            label    = 'Maintenance Allowed Uptime', 
            data     = '0', 
            units    = 'days', 
            comment  = ('How many days to allow between reboots of the device? Set this to 0 to ignore uptime days.'))
    
    return [maintenanceSection]
    
def getAppMonitor():
    global _monitor
    if (_monitor == None):
        _monitor = AppMonitor()
    return _monitor

def start():
    m = getAppMonitor()
    if (not m.isRunning()):
        m.start()
        
def stop():
    getAppMonitor().stop()

class AppMonitor(threading.Thread):

    def __init__(self):
        super(AppMonitor, self).__init__(name="AppMonitor")
        self.__cond      = threading.Condition()
        self.__running   = False
        self.__lastRun   = datetime.datetime.now()
        self.__period    = getAppSetting('maintenance_monitor_period')
        self.__reportingPeriod = getAppSetting('maintenance_reporting_period')
        self.__restartThreshold = 60 * 60
        self.__watchedThreads = []
        self.__startTime  = datetime.datetime.now()
        # Select a random offset (in seconds) for the restart/reboot time
        self.__scheduleOffsetDelta = timedelta(seconds=random.randint(-300, 300))
        
    def isRunning(self):
        return self.__running

    def start(self):
        log.dbg("Starting Application Monitor")
        self.__running = True
        super(AppMonitor, self).start()

    def stop(self):
        log.dbg("Stopping Application Monitor")
        with self.__cond:
            self.__running = False

    def __beforeToday(self, dateStr):
        """Returns True if the supplied date string is previous to today's 
        date"""
        if (dateStr.strip() == ""):
            return True
        
        todayStr = datetime.datetime.strftime(datetime.datetime.now(), "%Y-%m-%d")
        return (dateStr < todayStr)

    def uptime(self):
        """Returns the application uptime, in seconds"""
        timeNow = datetime.datetime.now()
        return (timeNow - self.__startTime).seconds
 
    def __getRestartDows(self):
        mapDow = {
            'mon': '1',
            'tue': '2',
            'wed': '3',
            'thu': '4',
            'fri': '5',
            'sat': '6',
            'sun': '7'
        }
        restartDows = getAppSetting('maintenance_schedule_dow')
        isoDows = []
        for dow in restartDows:
            try:
                isoDows.append(mapDow[dow])
            except:
                log.err('Invalid Maintenance Schedule DoW setting: "%s". Resetting to default' % dow)
                getAppSettings().set('maintenance_schedule_dow', 'sun')
                break
        return isoDows

    def __secondsUntilRestart(self, restartTimeStr):
        todayStr = datetime.datetime.strftime(datetime.datetime.now(), "%Y-%m-%d")
        restartTime = datetime.datetime.strptime("%s %s" % (todayStr, restartTimeStr), "%Y-%m-%d %H:%M") 
        waitDelta = restartTime - (datetime.datetime.now() + self.__scheduleOffsetDelta)
        return round(waitDelta.total_seconds())
                               
    def __monitor(self):
        log.dbg("Checking application health: %d thread(s) monitored:" % len(self.__watchedThreads))
        self.__lastRun = datetime.datetime.now()
        valid = True

        if getAppSetting('maintenance_schedule_event') in ['apprestart', 'reboot']:
            # Check for restart time
            restartTimeStr = getAppSetting('maintenance_schedule_time')
            if restartTimeStr is not None and restartTimeStr.strip() != "":
                log.dbg("Checking maintenance restart time")
                # Was the last restart earlier than today?
                if self.__beforeToday(getAppSetting('maintenance_last_restart_time')):
                    days = int(getAppSetting('maintenance_allowed_uptime_days'))
                    if days > 0:
                        seconds, valid = getSysUptime()
                        if valid and (seconds < (days * 86400)):
                            log.dbg("-- Threshold of %d uptime days not yet reached" % days)
                            return
                        elif not valid:
                            log.err("Error reading system up-time. Forcing reboot.")
                        else:
                            log.dbg("-- Threshold of %d uptime days (%d seconds) reached after %d second uptime" % (days, days * 86400, seconds))
                    # Have we reached the restart day?
                    dowToday = str(datetime.datetime.now().isoweekday())
                    restartDows = self.__getRestartDows()
                    # self.__validateDowSetting()
                    # restartDows = getAppSetting('maintenance_schedule_dow')
                    if dowToday in restartDows:
                        log.dbg("-- Restart/reboot required today")
                        # Have we reached or gone past the restart time for today?
                        waitSeconds = self.__secondsUntilRestart(restartTimeStr)
                        if (waitSeconds <= 0):
                            # Store the restart date
                            getAppSettings().set('maintenance_last_restart_time', datetime.datetime.strftime(datetime.datetime.now(), "%Y-%m-%d"))
                            # Time to restart
                            if (getAppSetting('maintenance_schedule_event') == 'reboot') or not valid:
                                log.dbg("-- Rebooting device")
                                gtmetrics.gtLog(gtmetrics.EVT_APP_SCHEDULED_REBOOT)
                                restartManager.reboot(300, 'Scheduled Restart')
                            else:
                                log.dbg("-- Restarting application")
                                gtmetrics.gtEvent(gtmetrics.EVT_APP_SCHEDULED_RESTART)
                                restartManager.restart(300, 'Scheduled Reboot')
                        else:
                            if abs(waitSeconds) < self.__period:
                                log.dbg("-- Restart/reboot on next check")
                            else:
                                log.dbg("-- Restart/reboot in %s" % str(datetime.timedelta(seconds=abs(waitSeconds))))
                else:
                    log.dbg("-- Already restarted or rebooted today")

    def run(self):
        log.dbg('Application Monitor started')
        while (self.__running):
            # get next time
            with self.__cond:
                try:
                    # calculate time till next metrics report is due
                    nextTime = self.__lastRun + timedelta(seconds=self.__reportingPeriod)
                    waitDelta = nextTime - datetime.datetime.now()
                    if (waitDelta.total_seconds() <= 0):
                        gtmetrics.mtxReport()
                    # calculate time till next check is due
                    nextTime = self.__lastRun + timedelta(seconds=self.__period)
                    waitDelta = nextTime - datetime.datetime.now()
                    if (waitDelta.total_seconds() <= 0):
                        self.__monitor()
                    else:
                        log.dbg('Waiting %ds for next check' % waitDelta.total_seconds())
                        self.__cond.wait(waitDelta.total_seconds())
                except Exception as e:
                    log.err("Application Monitor error: %s: " % str(e))
                    self.__cond.wait(300)
        log.dbg('Application Monitor ended')

# Utility functions
def getMemFree():
    """Returns (as a tuple) the total memory and the memory free,  along with
    a boolean to indicate whether or not the values were successfully read."""
    memTotal = -1
    memFree = - 1
    valid = True
    try:
        with open("/proc/meminfo", "r") as f:
            for line in f:
                key, value = line.split(":")
                key = key.strip()
                value = value.strip()
                if key == "MemTotal":
                    memTotal = int(value.split(" ")[0])
                elif key == "MemFree":
                    memFree = int(value.split(" ")[0])
    except Exception as e:
        log.err("Unable to read /proc/meminfo: %s" % e)

    if memTotal == -1:
        log.warn("Unable to read MemTotal from /proc/meminfo")
        valid = False
    
    if memFree == -1:
        log.warn("Unable to read MemFree from /proc/meminfo")
        valid = False
        
    return (memTotal, memFree, valid)

def getSysUptime():
    """Returns (as a tuple) the system uptime in seconds and a boolean to 
    indicate whether or not the value was successfully read."""
    uptime = -1
    valid = True
    try:
        with open("/proc/uptime", "r") as f:
            data = f.read()
            if data.strip() != "":
                uptime = float(data.split(" ")[0])
    except Exception as e:
        log.err("Unable to read /proc/uptime: %s" % e)

    if uptime == -1:
        log.warn("Unable to read data from /proc/uptime")
        valid = False

    return (uptime, valid)

def getAppUptime():
    """Returns the uptime for the application"""
    monitor = getAppMonitor()
    uptime = monitor.uptime()
    uptimeStr = str(datetime.timedelta(seconds=uptime))
    return uptimeStr
