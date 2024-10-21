# -*- coding: utf-8 -*-
#
# Copyright 2023 Grosvenor Technology
#
import os
import xml.etree.cElementTree as ET
import threading
from contextlib import closing

import log
import tblSchedules
from applib.db.tblSettings import getAppSetting, getAppSettings
from miscUtils import getElementText
# Wrapped to prevent circular reference issues. Issue occurs during manual/build_doc.py.
try:
    from webClient import commsHelper
except ImportError:
    log.dbg("Error while importing: {}".format(str(ImportError)))

_syncLock = threading.Lock()

class SchedulesHandler(object):
    """Handler for Schedule import and export
    
    Schedule XML Format:
    
        <schedules>
            <revision>1</revision>
            <schedule>
                <empID>string</empID>
                <revision>1</revision>
                <shifts>
                    <shift>
                        <id>1</id>
                        <startDateTime>2022-01-25T09:21:33</startDateTime>
                        <endDateTime>2022-01-25T17:21:33</endDateTime>
                    </shift>
                    <shift>
                        <id>2</id>
                        <startDateTime>2022-01-26T09:21:33</startDateTime>
                        <endDateTime>2022-01-26T17:21:33</endDateTime>
                    </shift>
                </shifts>
            </schedule>
        </schedules>    

    """
    def __init__(self):
        self._filename = "schedules.xml"
        self._restart  = False

    def getHelp(self):
        return """Schedules File Handler"""

    def getXsd(self):
        return ""

    def getExportName(self):
        return "schedules.xml"

    def getRevision(self):
        """ Return last known revision. """
        return getAppSetting('webclient_schedules_revision')
    
    def fileImport(self, name, data, restartReqManager, isDefaultData=False):
        if (log.debug_enabled and not isDefaultData):
            f = open('/tmp/%s' % name, 'w')
            f.write(data)
            f.close()

        currentRevision = self.getRevision()
        xml = ET.fromstring(data)

        schedules = tblSchedules.getAppSchedules()
        updatedRevision = getElementText(xml, 'revision', currentRevision)
        scheduleList = xml.findall('schedule')
        if scheduleList is None:
            log.err('No "schedule" elements found in Schedules XML')
            return
        for schedule in scheduleList:
            empID = getElementText(schedule, 'empID', '')
            if empID == '':
                log.err('Schedules XML error: schedule did not contain a valid "empID" element')
                continue
            revision = getElementText(schedule, 'revision', updatedRevision)
            if revision > updatedRevision:
                updatedRevision = revision
            shiftList = schedule.findall('shifts/shift')
            if shiftList is not None:
                for shift in shiftList:
                    shiftID = getElementText(shift, 'id', '')
                    startDateTime = getElementText(shift, 'startDateTime', '')
                    endDateTime = getElementText(shift, 'endDateTime', '')
                    if self._validateShiftRecord(shiftID, startDateTime, endDateTime):
                        schedules.insert(tblSchedules.Schedule(empID, shiftID, startDateTime, endDateTime).record())
            else:
                log.err('No "shift" elements found for schedule')
        if updatedRevision > currentRevision:
            getAppSettings().set('webclient_schedules_revision', updatedRevision)
        else:
            log.warn('Schedule Import: records were received from server, but Revision of "%s" was unchanged' % updatedRevision)

    def fileExport(self, name):
        xmlStr = '<schedules>\n<revision>%s</revision>\n' % getAppSetting('webclient_schedules_revision')
        schedules = tblSchedules.getAppSchedules()
        scheduleList = schedules.getAllSchedulesByEmployee()
        empID = ''
        for schedule in scheduleList:
            if schedule['EmpID'] != empID:
                # Start of records for next employee
                if empID != '':
                    xmlStr += '</shifts>\n'
                    xmlStr += '</schedule>\n'
                empID = schedule['EmpID']
                xmlStr += '<schedule>\n'
                xmlStr += '<empID>%s</empID>\n' % empID
                xmlStr += '<shifts>\n'
            xmlStr += '<shift>\n'
            xmlStr += '    <id>%s</id>\n' % schedule['id']
            xmlStr += '    <startDateTime>%s</startDateTime>\n' % schedule['startDateTime']
            xmlStr += '    <endDateTime>%s</endDateTime>\n' % schedule['endDateTime']
            xmlStr += '</shift>\n'
        if empID != '':
            xmlStr += '</shifts>\n'
            xmlStr += '</schedule>\n'
        xmlStr += '</schedules>'
        return xmlStr

    def _validateShiftRecord(self, shiftID, startDateTime, endDateTime):
        if shiftID == '':
            log.err('Schedule XML error: shift did not contain a valid "id" element')
            return False
        if startDateTime == '':
            log.err('Schedule XML error: shift did not contain a valid "startDateTime" element')
            return False
        if endDateTime == '':
            log.err('Schedule XML error: shift did not contain a valid "endDateTime" element')
            return False
        return True
    
    def _syncUpdates(self, schedules, conn, forceResync):
        """ Request all changes after revision and apply to table. Last
            revision is updated at the end and the number of received
            records and total records on the server is returned.
        """
        currentRevision = self.getRevision() if not forceResync else None
        log.dbg('Requesting updates (revision since %s)' % currentRevision)
        extraParams = {}
        extraParams['Revision'] = currentRevision
        stream = commsHelper.httpStreamRequest(conn, 'GET', '/schedules', None, extraParams)
        optAttribs = {}
        updatedRevision = currentRevision
        recordCount = {'Added': 0, 'Updated': 0, 'Deleted': 0, 'Unchanged': 0, 'Received': 0}
        for (event, elem) in ET.iterparse(stream):
            if elem.tag == 'revision' and event == 'end':
                revision = elem.text
                if revision > updatedRevision:
                    updatedRevision = revision
            elif elem.tag == 'schedule' and event == 'end':
                empID = getElementText(elem, 'empID', '')
                if empID == '':
                    log.err('Schedules XML error: schedule did not contain a valid "empID" element')
                    continue
                revision = getElementText(elem, 'revision', updatedRevision)
                if revision > updatedRevision:
                    updatedRevision = revision
                shifts = elem.findall('shifts/shift')
                for shift in shifts:
                    shiftID = getElementText(shift, 'id', '')
                    startDateTime = getElementText(shift, 'startDateTime', '')
                    endDateTime = getElementText(shift, 'endDateTime', '')
                    if self._validateShiftRecord(shiftID, startDateTime, endDateTime):
                        record = tblSchedules.Schedule(empID, shiftID, startDateTime, endDateTime).record()
                        existingRecord = schedules.getSchedule(empID, shiftID)
                        if existingRecord:
                            if (record['StartDateTime'] != existingRecord['StartDateTime'] or 
                                record['EndDateTime'] != existingRecord['EndDateTime']):
                                # Update existing record
                                schedules.insert(record, replace=True)
                                recordCount['Updated'] += 1
                            else:
                                recordCount['Unchanged'] += 1
                        else:
                            # Insert new record
                            schedules.insert(record, replace=False)
                            recordCount['Added'] += 1
                        recordCount['Received'] += 1
        
        if recordCount['Received'] > 0:
            log.info('%d Schedules received' % recordCount['Received'])
            log.info('%d Schedules added' % recordCount['Added'])
            log.info('%d Schedules updated' % recordCount['Updated'])
            log.info('%d Schedules unchanged' % recordCount['Unchanged'])
            log.info('%d Schedules in database' % schedules.count())
            log.info('Latest Schedules revision: %s' % updatedRevision)
            if updatedRevision > currentRevision:
                getAppSettings().set('webclient_schedules_revision', updatedRevision)
            else:
                log.warn('Schedule Sync: records were received from server, but Revision of "%s" was unchanged' % updatedRevision)

        # return number of received updates and total server count
        totalServerCount = optAttribs.get('totalScheduleCount')
        if (totalServerCount == None):
            totalServerCount = 0
            log.warn('Total server count for Schedules not specified!')
        return (recordCount['Received'], int(totalServerCount))
    
    def syncSchedules(self, forceResync=False):
        """Sychronises the Schedule records from an import stream of XML data."""
        with _syncLock:
            schedules = tblSchedules.getAppSchedules()
            # temporary -- assume that incoming data is a complete replacement
            schedules.deleteAll()
        
        with closing(commsHelper.openHttpConnection()) as conn:
            # request all new and updated Schedules and receive total count
            self._syncUpdates(schedules, conn, forceResync)
        
    def fileDelete(self, name):
        name = self.getExportName()
        filename = '/mnt/user/db/%s' % name
        try:
            os.unlink(filename)
        except Exception as e:
            log.warn('Error deleting %s: %s' % (name, e))
