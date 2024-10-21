# -*- coding: utf-8 -*-
#
# Copyright 2011 Grosvenor Technology
#
from applib.db import database, tblLastTableSync
import xml.etree.cElementTree
import log
import relaySchedules


class RelaySchedulesHandler(object):
    
    def getHelp(self):
        return """
The relay schedule handler can import and export configured 
relay schedules. With this, it is possible to configure the
schedules on a terminal (e.g. via :ref:`action_relay.editor`), 
export it and re-import on other 
terminals that should run the same schedules.
"""

    def getExportName(self):
        return 'relays.xml'

    #-----------------------------------------------------------------------
    def fileImport(self, name, xmlData, restartReqManager, isDefaultData=False):
        if (log.debug_enabled):
            f = open('/tmp/%s' % name, 'w')
            f.write(xmlData)
            f.close()
            
        relayScheds = relaySchedules.RelaySchedules(database.getAppDB())
        relayScheds.open()
        
        lastTableSyncTbl = tblLastTableSync.TblLastTableSync()
        lastTableSyncTbl.open()
        (lastSync, lastMD5) = lastTableSyncTbl.getByTableName(relayScheds.tableName)
        if (isDefaultData and lastSync != None):
            log.dbg('Not applying defaults for %s (last sync on %s).' % (relayScheds.tableName, lastSync))
            return
        md5sum = tblLastTableSync.createMD5Sum(xmlData)
        if (md5sum == lastMD5):
            log.dbg('Not applying data for %s, no changes.' % relayScheds.tableName)
            return
        
        relayScheds.importFromXML(xmlData)
        if (isDefaultData):
            lastTableSyncTbl.setMD5(relayScheds.tableName, md5sum)
        else:
            lastTableSyncTbl.setSynched(relayScheds.tableName, md5sum)
            restartReqManager.requestRestart()

    #-----------------------------------------------------------------------
    def fileExport(self, name):
        relayScheds = relaySchedules.RelaySchedules(database.getAppDB())
        relayScheds.open()
        data = relayScheds.exportToXML()
        if (log.debug_enabled):
            f = open('/tmp/%s' % name, 'w')
            f.write(data)
            f.close()         
        return data

    def projectImport(self, name, xmlTag, restartReqManager):
        relayScheds = relaySchedules.RelaySchedules(database.getAppDB())
        relayScheds.open()
        lastTableSyncTbl = tblLastTableSync.TblLastTableSync()
        lastTableSyncTbl.open()
        (_lastSync, lastMD5) = lastTableSyncTbl.getByTableName(relayScheds.tableName)
        xmlData = xml.etree.cElementTree.tostring(xmlTag, "utf-8")
        md5sum = tblLastTableSync.createMD5Sum(xmlData)
        if (md5sum == lastMD5):
            log.dbg('Not applying data for %s, no changes.' % relayScheds.tableName)
            return
        relayScheds.importFromXML(xmlData)
        lastTableSyncTbl.setSynched(relayScheds.tableName, md5sum)
        restartReqManager.requestRestart()

    def projectExport(self, name):
        relayScheds = relaySchedules.RelaySchedules(database.getAppDB())
        relayScheds.open()
        return relayScheds.exportToXML(includeXMLHeaders=False)


         


