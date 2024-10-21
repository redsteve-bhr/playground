# -*- coding: utf-8 -*-

import emps
import log
from applib.utils import timeUtils
from applib.db import tblLastTableSync
from engine import fileHandler
import xml.etree.cElementTree
import StringIO
import hashlib
  

class EmployeeHandler(object):
    
    def getHelp(self):
        return """
The employees file handler can import and export an XML file containing
all employees. On import, any employee not in the file will be removed
from the terminal.
"""
    
    def getExportName(self):
        return 'tblEmps.xml'

    def fileImport(self, name, data, restartReqManager, isDefaultData=False):
        tblEmps = emps.getAppEmps()
        # Create and compare MD5 checksum
        lastTableSyncTbl = tblLastTableSync.TblLastTableSync()
        lastTableSyncTbl.open()
        (lastSync, lastMD5) = lastTableSyncTbl.getByTableName(tblEmps.tableName)
        if (isDefaultData and lastSync != None):
            log.dbg('Not applying defaults for %s (last sync on %s).' % (tblEmps.tableName, lastSync))
            return
        md5sum = tblLastTableSync.createMD5Sum(data)
        if (md5sum == lastMD5):
            log.dbg('Not applying data for %s, no changes.' % tblEmps.tableName)
            return
        # Import new data
        self.__importFromXML(tblEmps, data)
        # Save new MD5
        if (isDefaultData):
            lastTableSyncTbl.setMD5(tblEmps.tableName, md5sum)
        else:
            lastTableSyncTbl.setSynched(tblEmps.tableName, md5sum)

    def projectImport(self, name, xmlTag, restartReqManager):
        data = xml.etree.cElementTree.tostring(xmlTag, "UTF-8")
        self.fileImport(name, data, restartReqManager)

    def __parseEmp(self, data):
        for (_ev, elem) in xml.etree.cElementTree.iterparse(data):
            if (elem.tag == 'row'):
                # convert row to employee dictionary
                emp = {}
                for col in elem:
                    if (col.tag == 'col'):
                        name = col.get('name', None)
                        value = col.text
                        if (name and value):
                            emp[name] = value
                yield emp
                elem.clear()

    def __createMD5(self, cols, emp):
        lst = [ emp[c] if c in emp else '' for c in cols ]
        return hashlib.md5( '|'.join(lst) ).hexdigest()

    def __importFromXML(self, tblEmps, data):
        addedCount = updatedCount = unchangedCount = removedCount = 0
        with timeUtils.TimeMeasure('Updating employees'):
            availableColumns = tblEmps.columnDefs.keys()
            availableColumns.sort() 
            allEmpIDs = tblEmps.getAllEmpIDsAndMD5s()
            for emp in self.__parseEmp(StringIO.StringIO(data)):
                try:
                    if ('EmpID' not in emp):
                        raise Exception('No EmpID')
                    # update employee table
                    empID = emp['EmpID']
                    if (empID in allEmpIDs):
                        # compare MD5
                        emp['MD5'] = self.__createMD5(availableColumns, emp)
                        if (emp['MD5'] != allEmpIDs[empID]):
                            # update record
                            tblEmps.insert(emp, replace=True)
                            updatedCount += 1
                        else:
                            unchangedCount += 1
                        # delete from list
                        del allEmpIDs[empID]
                    else:
                        # add new record
                        tblEmps.insert(emp, replace=False)
                        addedCount += 1
                except Exception as e:
                    log.err('Error in employee import: %s' % (e,))
            # delete records
            for empID in allEmpIDs.iterkeys():
                tblEmps.deleteByEmpID(empID)
                removedCount += 1
        log.dbg('Total employees imported = %s' % (addedCount + updatedCount + unchangedCount))
        log.dbg('Added     = %s' % addedCount)
        log.dbg('Updated   = %s' % updatedCount)
        log.dbg('Unchanged = %s' % unchangedCount)        
        log.dbg('Removed   = %s' % removedCount)

    def fileExport(self, name):
        tblEmps = emps.getAppEmps()
        data = ['<?xml version="1.0" encoding="UTF-8"?>', '<tableData name="%s">' % tblEmps.tableName]
        for row in tblEmps.selectAll():
            data.append('  <row>')
            for i in row.keys():
                if (i != 'MD5' and row[i] != None):
                    data.append('    <col name="%s">%s</col>' % (i, row[i]))
            data.append('  </row>')
        data.append('</tableData>')
        return "\n".join(data)     

class EmployeesReportHandler(object):
    
    def getHelp(self):
        return """
The employees report file handler can export a CSV file containing
basic details for all employees.

Exported Details:
- Employee ID
- External ID
- Badge Code
- Number of Fingers Enrolled
- Number of Templates
- Number of Face Templates (always 0 for IT terminals)
- Number of Photos (always 0 for IT terminals)
- Roles
- Display Items (flattened to single CSV field)

"""
    
    def getExportName(self):
        return 'employeesReport.csv'

    def fileExport(self, name):
        tblEmps = emps.getAppEmps()
        data = ['"EmployeeID","ExternalID","BadgeCode","FingersEnrolledCount","FingerTemplateCount","FaceTemplateCount","PhotoCount","Roles","DisplayItems"']
        template = '"%s","%s","%s","%d","%d","%d","%d","%s","%s"'
        for row in tblEmps.selectAll():
            empID = row['EmpID']
            externalID = row['ExternalID']
            badgeCode = row['BadgeCode']
            roles = row['Roles']
            fingers = emps.getAppEmps().getTemplateRepository().getFingers(empID)
            fingersEnrolledCount = len(fingers)
            templates = emps.getAppEmps().getTemplateRepository().getTemplates(empID)
            fingerTemplateCount = len(templates)
            displayItems = emps.getAppEmpDisplayItems().parseToCSV(empID)
            
            line = template % (empID, externalID, badgeCode, fingersEnrolledCount, fingerTemplateCount, 0, 0, roles, displayItems)
            data.append(line)
        export = "\n".join(data)
        return export

def loadPlugin():
    fileHandler.register('^tbl.*\.xml$', EmployeeHandler(), 'Employees')
    fileHandler.register('^employeesReport\.csv$', EmployeesReportHandler(), 'Employees Report')
