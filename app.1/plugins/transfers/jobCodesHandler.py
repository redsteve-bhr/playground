# -*- coding: utf-8 -*-
#
# Copyright 2023 Grosvenor Technology
#
import os
import xml.etree.cElementTree as ET
import threading
from contextlib import closing

import log
import tblJobCodes
from applib.db.tblSettings import getAppSetting, getAppSettings
from miscUtils import getElementText
# Wrapped to prevent circular reference issues. Issue occurs during manual/build_doc.py.
try:
    from webClient import commsHelper
except ImportError:
    log.dbg("Error while importing: {}".format(str(ImportError)))

_syncLock = threading.Lock()

class JobCodesFileHandler(object):
    """Handler for Job Code import and export
    
    Job Code XML Format:
    
        <jobCodes>
            <revision>90</revision>
            <jobCode>
                <revision>89</revision>
                <jobCategoryID>1</jobCategoryID>
                <code>1234</code>
                <id>1</id>
                <name>
                    <text language="en">Job Code One EN</text>
                    <text language="fr">Job Code One FR</text>
                </name>
            </jobCode>
            <jobCode>
                <revision>90</revision>
                <jobCategoryID>2</jobCategoryID>
                <code>4321</code>
                <id>2</id>
                <name>
                    <text language="en">Job Code Two EN</text>
                    <text language="fr">Job Code Two FR</text>
                </name>
            </jobCode>
        </jobCodes>

    """
    def __init__(self):
        self._filename = "jobCodes.xml"
        self._restart  = False

    def getHelp(self):
        return """Job Codes File Handler"""

    def getXsd(self):
        return ""

    def getExportName(self):
        return "jobCodes.xml"

    def getRevision(self):
        """ Return last known revision. """
        return getAppSetting('webclient_job_codes_revision')
    
    def fileImport(self, name, data, restartReqManager, isDefaultData=False):
        if (log.debug_enabled and not isDefaultData):
            f = open('/tmp/%s' % name, 'w')
            f.write(data)
            f.close()

        currentRevision = self.getRevision()
        xml = ET.fromstring(data)
        jobCodes = tblJobCodes.getAppJobCodes()
        jobCodesList = xml.findall('jobCode')

        if jobCodesList is None:
            log.err('No "jobCode" elements found in Job Codes XML')
            return

        for jobCodeTag in jobCodesList:
            jobCodeID = getElementText(jobCodeTag, 'jobCodeID', '')
            jobCategoryID = getElementText(jobCodeTag, 'jobCategoryID', '')
            code = getElementText(jobCodeTag, 'code', '')
            # name = ET.tostring(jobCodeTag, 'utf-8')
            name = ET.tostring(jobCodeTag.find('name')).decode('utf-8')

            revision = getElementText(jobCodeTag, 'revision', '')
            if revision > currentRevision:
                currentRevision = revision

            jobCodes.insert(tblJobCodes.JobCode(jobCodeID, jobCategoryID, code, name).record())

        getAppSettings().set('webclient_job_codes_revision', currentRevision)

    def fileExport(self, name):
        xmlStr = '<jobCodes>\n<revision>%s</revision>\n' % getAppSetting('webclient_job_codes_revision')
        jobCodes = tblJobCodes.getAppJobCodes()
        jobCodesList = jobCodes.getAllJobCodes()

        for jobCode in jobCodesList:
            xmlStr += '<jobCode>\n'
            xmlStr += '    <id>%s</id>\n' % jobCode['id']
            xmlStr += '    <jobCategoryID>%s</jobCategoryID>\n' % jobCode['jobCategoryID']
            xmlStr += '    <code>%s</code>\n' % jobCode['code']
            xmlStr += '    <name>%s</name>\n' % jobCode['name']
            xmlStr += '</jobCode>\n'
        xmlStr += '</jobCodes>'
        return xmlStr

    def _syncUpdates(self, jobCodes, conn, forceResync):
        """ Request all changes after revision and apply to table. Last
            revision is updated at the end and the number of received
            records and total records on the server is returned.
        """
        currentRevision = self.getRevision() if not forceResync else None
        updatedRevision = currentRevision
        log.dbg('Requesting updates (revision since %s)' % currentRevision)
        extraParams = {}
        extraParams['Revision'] = currentRevision
        stream = commsHelper.httpStreamRequest(conn, 'GET', '/jobCodes', None, extraParams)
        optAttribs = {}
        recordCount = {'Added': 0, 'Updated': 0, 'Removed': 0, 'Unchanged': 0, 'Received': 0}
        originalJobCodes = jobCodes.getAllJobCodeIDs()
        for (event, elem) in ET.iterparse(stream):
            if elem.tag == 'jobCode' and event == 'end':
                jobCodeID = getElementText(elem, 'id', '', warn=True)
                jobCategoryID = getElementText(elem, 'jobCategoryID', '', warn=True)
                code = getElementText(elem, 'code', '', warn=True)
                nameElem = elem.find('name')
                if nameElem is not None:
                    name = ET.tostring(elem.find('name')).decode('utf-8')
                else:
                    name = ''
                    log.warn('Failed to find "%s" under element "%s"; using default of "%s"' % ('name', elem.tag, name))
                # revision = getElementText(elem, 'revision', updatedRevision)
                # if revision > updatedRevision:
                #     updatedRevision = revision

                record = tblJobCodes.JobCode(jobCodeID, jobCategoryID, code, name).record()
                existingRecord = jobCodes.getJobCode(jobCodeID)
                if existingRecord:
                    if (record['JobCategoryID'] != existingRecord['JobCategoryID'] or
                        record['Code'] != existingRecord['Code'] or
                        record['Name'] != existingRecord['Name']):
                        # Update existing record
                        jobCodes.insert(record, replace=True)
                        recordCount['Updated'] += 1
                    else:
                        recordCount['Unchanged'] += 1
                    originalJobCodes.pop(jobCodeID, None)
                else:
                    # Insert new record
                    jobCodes.insert(record, replace=False)
                    recordCount['Added'] += 1
                recordCount['Received'] += 1
            elif elem.tag == 'revision' and event == 'end':
                if elem.text > updatedRevision:
                    updatedRevision = elem.text
        
        for jobCodeID in originalJobCodes:
            jobCodes.deleteByJobCodeID(jobCodeID)
            recordCount['Removed'] += 1
            
        if recordCount['Received'] > 0:
            log.info('%d Job Codes received' % recordCount['Received'])
            log.info('%d Job Codes added' % recordCount['Added'])
            log.info('%d Job Codes updated' % recordCount['Updated'])
            log.info('%d Job Codes unchanged' % recordCount['Unchanged'])
            log.info('%d Job Codes removed' % recordCount['Removed'])
            log.info('%d Job Codes in database' % jobCodes.count())
            log.info('Latest Job Codes revision: %s' % updatedRevision)

            if updatedRevision == currentRevision:
                log.warn('Job Codes Import: records were received from server, but Revision of "%s" was unchanged' % updatedRevision)
            else:
                getAppSettings().set('webclient_job_codes_revision', updatedRevision)

        # return number of received updates and total server count
        totalServerCount = optAttribs.get('totalJobCodesCount')
        if (totalServerCount == None):
            totalServerCount = 0
            log.warn('Total count for Job Codes was not received from server!')
        return (recordCount['Received'], int(totalServerCount))
    
    def syncJobCodes(self, forceResync=False):
        """Sychronises the Job Codes records from an import stream of XML data."""
        with _syncLock:
            jobCodes = tblJobCodes.getAppJobCodes()
        
        with closing(commsHelper.openHttpConnection()) as conn:
            self._syncUpdates(jobCodes, conn, forceResync)
        
    def fileDelete(self, name):
        name = self.getExportName()
        filename = '/mnt/user/db/%s' % name
        try:
            os.unlink(filename)
        except Exception as e:
            log.warn('Error deleting %s: %s' % (name, e))
