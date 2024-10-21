# -*- coding: utf-8 -*-

import threading
import xml.etree.cElementTree as ET
import commsHelper
from plugins.transfers import jobCodesHandler, jobCategoriesHandler
from webConfig import getAppWebClientSetup
from contextlib import closing
from applib.utils import restartManager, timeUtils
import appit
import updateit
import syncConfig
import employees, employeeInfo, registerDevice
from applib.db.tblSettings import getAppSetting
from applib.utils import busyIndicator
from engine import fileHandler
from plugins.schedules import schedulesHandler
import log
import onlineState
import cfg

_syncLock = threading.Lock()

class RepeatRequests(object):
    """Class to check whether change requests have been repeated"""
    
    def __init__(self):
        self.requests = {
            'firmware': 0,
            'application': 0,
            'itcfg': 0,
            'buttons': 0,
            'certificates': 0,
            'dataCollection': 0,
            'employees': 0,
            'employeeInfo': 0,
            'schedules': 0,
            'jobCodes': 0,
            'jobCategories': 0
        }

    def update(self, request):
        if request in self.requests:
            self.requests[request] += 1
            self.__checkLog(request)

    def reset(self, request=None):
        """Resets the specified request. If request is None, all entries are cleared."""
        for key in self.requests:
            if request is None or request == key:
                self.requests[key] = 0

    def list(self):
        """Logs the status of all current entries"""
        for request in self.requests:
            log.dbg('Sync Repeats: %s: %s' % (request, self.__check(request)))

    def __check(self, request):
        """Returns the number of repeat requests that have been made for this request"""
        if request in self.requests:
            if self.requests[request] > 0:
                return self.requests[request] - 1
            else:
                return 0
    
    def __checkLog(self, request):
        """Logs a message if the specified request has been repeated"""
        repeats = self.__check(request)
        if repeats > 0:
            log.dbg('Sync Repeats: change requests for "%s" have been repeated %d time(s)' % (request, repeats))

_repeats = RepeatRequests()

def _requestSyncChanges():
    """ Send configuration request"""
    appInfo = appit.AppInfo()
    extraParams = { 'AppRevision'            : '%s-%s.app' % (appInfo.name(), appInfo.version()),
                    'ButtonsRevision'        : getAppSetting('webclient_buttons_revision'),
                    'ItcfgRevision'          : getAppSetting('webclient_itcfg_revision'),
                    'EmpsRevision'           : getAppSetting('webclient_employees_revision'),
                    'EmpsCount'              : employees.emps.getAppEmps().count(),
                    'EmpsInfoRevision'       : getAppSetting('webclient_employeeinfo_revision'),
                    'EmpsInfoCount'          : employeeInfo.getAppEmpInfo().count(),
                    'SchedulesRevision'      : getAppSetting('webclient_schedules_revision'),
                    'JobCodesRevision'      : getAppSetting('webclient_job_codes_revision'),
                    'JobCategoriesRevision'  : getAppSetting('webclient_job_categories_revision'),
                    'DataCollectionRevision' : getAppSetting('webclient_datacollection_revision'),
                    'CertificatesRevision'   : getAppSetting('webclient_ca_certs_revision') }
    if (getAppWebClientSetup().supportFirmwareUpdates()):
        extraParams['FwRevision'] = updateit.get_version()
    # send request
    with closing(commsHelper.openHttpConnection()) as conn:
        deviceID = getAppWebClientSetup().getDeviceID()
        if deviceID is None or deviceID.strip() == '':
            deviceID = cfg.get(cfg.CFG_PARTNO)
            log.warn('Device ID not set. Using default of "%s"' % deviceID)
        data = commsHelper.httpGet(conn, '/changes/%s' % deviceID, extraParams)
    return data

def _syncChanges():
    global _repeats
    
    try:
        data = _requestSyncChanges()
        if data is None:
            return
    except commsHelper.UnauthorisedException as e:
        log.dbg('%s! Registering...' % e)
        registerDevice.registerDevice()
        data = _requestSyncChanges()
    except Exception as e:
        log.dbg('Unable to get change requests from server: %s' % str(e))
        onlineState.setIsOnline(False)
        return

    root = ET.fromstring(data)
    if (root.find('firmware') != None):
        _repeats.update('firmware')
        with busyIndicator.BusyIndicator(_('Installing new firmware')):
            with restartManager.PreventRestartLock():
                syncConfig.updateFirmware(root.find('firmware').text)
    else:
        _repeats.reset('firmware')

    if (root.find('application') != None):
        _repeats.update('application')
        with busyIndicator.BusyIndicator(_('Installing new application')):
            with restartManager.PreventRestartLock():
                syncConfig.updateApplication(root.find('application').text)
    else:
        _repeats.reset('application')

    restartReqManager = fileHandler.RestartRequestManager()
    if (root.find('itcfg') != None):
        _repeats.update('itcfg')
        with busyIndicator.BusyIndicator(_('Loading itcfg')):
            with restartManager.PreventRestartLock():
                syncConfig.updateItcfg(restartReqManager)
    else:
        _repeats.reset('itcfg')
        
    if (root.find('buttons') != None):
        _repeats.update('buttons')
        with busyIndicator.BusyIndicator(_('Loading buttons')):
            with restartManager.PreventRestartLock():
                syncConfig.updateButtons(restartReqManager)
    else:
        _repeats.reset('buttons')
        
    if (root.find('certificates') != None):
        _repeats.update('certificates')
        with busyIndicator.BusyIndicator(_('Loading certificates')):
            with restartManager.PreventRestartLock():
                syncConfig.updateCertificates(restartReqManager)
    else:
        _repeats.reset('certificates')

    if (root.find('dataCollection') != None):
        _repeats.update('dataCollection')
        with busyIndicator.BusyIndicator(_('Loading data collection definitions')):
            with restartManager.PreventRestartLock():
                syncConfig.updateDataCollection(restartReqManager)
    else:
        _repeats.reset('dataCollection')

    if (restartReqManager.isRebootRequested()):
        restartManager.reboot(30)
    elif (restartReqManager.isRestartRequested()):
        restartManager.restart(30)

    if (root.find('employees') != None):
        _repeats.update('employees')
        with busyIndicator.BusyIndicator(_('Loading employees')):
            with timeUtils.TimeMeasure('Importing employees'):
                employees.syncEmployees()
    else:
        _repeats.reset('employees')

    if (root.find('employeeInfo') != None):
        _repeats.update('employeeInfo')
        with busyIndicator.BusyIndicator(_('Loading employee info')):
            employeeInfo.syncEmployeeInfo()
    else:
        _repeats.reset('employeeInfo')

    if (root.find('schedules') != None):
        _repeats.update('schedules')
        with busyIndicator.BusyIndicator(_('Loading Schedules')):
            handler = schedulesHandler.SchedulesHandler()
            handler.syncSchedules()
    else:
        _repeats.reset('schedules')
        
    if (root.find('jobCodes') != None):
        _repeats.update('jobCodes')
        with busyIndicator.BusyIndicator(_('Loading Job Codes')):
            handler = jobCodesHandler.JobCodesFileHandler()
            handler.syncJobCodes()
    else:
        _repeats.reset('jobCodes')

    if (root.find('jobCategories') != None):
        _repeats.update('jobCategories')
        with busyIndicator.BusyIndicator(_('Loading Job Categories')):
            handler = jobCategoriesHandler.JobCategoriesHandler()
            handler.syncSchedules()
    else:
        _repeats.reset('jobCategories')

    # _repeats.list()
    

def syncChanges():
    with _syncLock:
        _syncChanges()
