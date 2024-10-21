# -*- coding: utf-8 -*-
#
# Copyright 2023 Grosvenor Technology
#
import os
import xml.etree.cElementTree as ET
import threading
from contextlib import closing
import tblJobCategories

import log
from applib.db.tblSettings import getAppSetting, getAppSettings
from miscUtils import getElementText
# Wrapped to prevent circular reference issues. Issue occurs during manual/build_doc.py.
try:
    from webClient import commsHelper
except ImportError:
    log.dbg("Error while importing: {}".format(str(ImportError)))

_syncLock = threading.Lock()


class JobCategoriesHandler(object):
    """Handler for Job Categories import and export

    Job Category XML Format:

        <jobCategories>
            <revision>74</revision>
            <jobCategory>
                <revision>73</revision>
                <id>1</id>
                <level>1</level>
                <name>
                    <text language="en">Department One EN</text>
                    <text language="fr">Department One FR</text>
                </name>
            </jobCategory>
            <jobCategory>
                <revision>74</revision>
                <id>2</id>
                <level>2</level>
                <name>
                    <text language="en">Department Two EN</text>
                    <text language="fr">Department Two FR</text>
                </name>
            </jobCategory>
        </jobCategories>


    """

    def __init__(self):
        self._filename = "jobCategories.xml"
        self._restart = False

    def getHelp(self):
        return """Job Categories File Handler"""

    def getXsd(self):
        return ""

    def getExportName(self):
        return "jobCategories.xml"

    def getRevision(self):
        """ Return last known revision. """
        return getAppSetting('webclient_job_categories_revision')

    def fileImport(self, name, data, restartReqManager, isDefaultData=False):
        if (log.debug_enabled and not isDefaultData):
            f = open('/tmp/%s' % name, 'w')
            f.write(data)
            f.close()

        currentRevision = self.getRevision()
        xml = ET.fromstring(data)
        jobCategories = tblJobCategories.getAppJobCategories()
        jobCategoriesList = xml.findall('jobCategory')

        if jobCategoriesList is None:
            log.err('No "jobCategory" elements found in Job Categories XML')
            return

        for jobCategoryTag in jobCategoriesList:
            jobCategoryId = getElementText(jobCategoryTag, 'id', '')

            revision = getElementText(jobCategoryTag, 'revision', '')
            if revision > currentRevision:
                currentRevision = revision

            level = getElementText(jobCategoryTag, 'level', '')
            name = ET.tostring(jobCategoryTag, 'utf-8')

            jobCategories.insert(tblJobCategories.JobCategory(jobCategoryId, level, name).record())

        getAppSettings().set('webclient_job_categories_revision', currentRevision)

    def fileExport(self, name):
        xmlStr = '<jobCategories>\n<revision>%s</revision>\n' % getAppSetting('webclient_job_categories_revision')
        jobCategories = tblJobCategories.getAppJobCategories()
        jobCategoriesList = jobCategories.getAllJobCategories()

        for jobCategory in jobCategoriesList:
            xmlStr += '<jobCategory>\n'
            xmlStr += '<id>%s</id>\n' % jobCategory.jobCategoryID
            xmlStr += '<level>%s</level>\n' % jobCategory.level
            xmlStr += '<name>%s</name>\n' % jobCategory.name
            xmlStr += '</jobCategory>\n'
        xmlStr += '</jobCategories>'

        return xmlStr

    def _syncUpdates(self, jobCategories, conn, forceResync):
        """ Request all changes after revision and apply to table. Last
            revision is updated at the end and the number of received
            records and total records on the server is returned.
        """
        currentRevision = self.getRevision() if not forceResync else None
        updatedRevision = currentRevision
        log.dbg('Requesting updates (revision since %s)' % currentRevision)
        extraParams = {}
        extraParams['Revision'] = currentRevision
        stream = commsHelper.httpStreamRequest(conn, 'GET', '/jobCategories', None, extraParams)
        optAttribs = {}
        recordCount = {'Added': 0, 'Updated': 0, 'Removed': 0, 'Unchanged': 0, 'Received': 0}
        originalJobCategories = jobCategories.getAllJobCategoryIDs()
        for (event, elem) in ET.iterparse(stream):
            if elem.tag == 'jobCategory' and event == 'end':
                jobCategoryId = getElementText(elem, 'id', '', warn=True)
                level = getElementText(elem, 'level', '', warn=True)
                nameElem = elem.find('name')
                if nameElem is not None:
                    name = ET.tostring(elem.find('name')).decode('utf-8')
                else:
                    name = ''
                    log.warn('Failed to find "%s" under element "%s"; using default of "%s"' % ('name', elem.tag, name))
                revision = getElementText(elem, 'revision', updatedRevision)
                if revision > updatedRevision:
                    updatedRevision = revision

                record = tblJobCategories.JobCategory(jobCategoryId, level, name).record()
                existingRecord = jobCategories.getJobCategory(jobCategoryId)
                if existingRecord:
                    if record['Level'] != existingRecord['Level'] or record['Name'] != existingRecord['Name']:
                        # Update existing record
                        jobCategories.insert(record, replace=True)
                        recordCount['Updated'] += 1
                    else:
                        recordCount['Unchanged'] += 1
                    originalJobCategories.pop(jobCategoryId, None)
                else:
                    # Insert new record
                    jobCategories.insert(record, replace=False)
                    recordCount['Added'] += 1
                recordCount['Received'] += 1
            elif elem.tag == 'revision' and event == 'end':
                if elem.text > updatedRevision:
                    updatedRevision = elem.text

        for jobCategoryID in originalJobCategories:
            jobCategories.deleteByJobCategoryID(jobCategoryID)
            recordCount['Removed'] += 1

        if recordCount['Received'] > 0:
            log.info('%d Job Categories received' % recordCount['Received'])
            log.info('%d Job Categories added' % recordCount['Added'])
            log.info('%d Job Categories updated' % recordCount['Updated'])
            log.info('%d Job Categories unchanged' % recordCount['Unchanged'])
            log.info('%d Job Categories removed' % recordCount['Removed'])
            log.info('%d Job Categories in database' % jobCategories.count())
            log.info('Latest Job Categories revision: %s' % revision)

            if updatedRevision == currentRevision:
                log.warn('Job Categories Import: records were received from server, but Revision of "%s" was unchanged' % updatedRevision)
            else:
                getAppSettings().set('webclient_job_categories_revision', revision)

        # return number of received updates and total server count
        totalServerCount = optAttribs.get('totalJobCategoriesCount')
        if (totalServerCount == None):
            totalServerCount = 0
            log.warn('Total count for Job Categories not received from server!')
        return (recordCount['Received'], int(totalServerCount))

    def syncSchedules(self, forceResync=False):
        """Sychronises the Job Categories records from an import stream of XML data."""
        with _syncLock:
            jobCategories = tblJobCategories.getAppJobCategories()

        with closing(commsHelper.openHttpConnection()) as conn:
            self._syncUpdates(jobCategories, conn, forceResync)

    def fileDelete(self, name):
        name = self.getExportName()
        filename = '/mnt/user/db/%s' % name
        try:
            os.unlink(filename)
        except Exception as e:
            log.warn('Error deleting %s: %s' % (name, e))
