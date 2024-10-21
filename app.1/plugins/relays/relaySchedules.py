# -*- coding: utf-8 -*-
#
# Copyright 2010 Grosvenor Technology
#

"""
:mod:`tblRelayOverride` --- RelayOverrides class
================================================

These are setup at the terminal typically to ring bells at predefined times.            

"""

import datetime
import threading
import log
import xml.etree.cElementTree
from applib.db import table
from applib.db.database import getAppDB
from applib.utils import crashReport, relayManager


#-------------------------------------------------------------------------------
class TblRelayOverrides(table.Table):
    """ Create an tblRelayTimes instance
    
    Relay override dates
    
    These do not specify the year and therefore do not need updating every
    year e.g. 25/12 -> 26/12
    
    During these periods the relay times are not activated. This allows the
    programming of bank holidays, company shut downs etc.
    
    :param db: is the database object (Database)
    
    """

    columnDefs = {  'RecID'     : 'INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL',
                    'StartDate' : 'TEXT NOT NULL',
                    'EndDate'   : 'TEXT NOT NULL',
                    }
 
    def __init__(self, db, tableName='tblRelayOverrides'):
        super(TblRelayOverrides, self).__init__(db, tableName)


    def add(self, startDate, endDate):
        sql = 'INSERT INTO %s (StartDate, EndDate ) VALUES (?,?)' % self.tableName
        self.runQuery(sql, (startDate, endDate))


    def selectAllOrderByTime(self):
        sql = 'SELECT * FROM %s ORDER BY StartDate, EndDate' % self.tableName
        return self.runSelectAll(sql)


    def deleteByRecID(self, recID):
        sql = "DELETE FROM %s WHERE RecID = ?" % self.tableName
        self.runQuery(sql, (recID,))


    def updateByRecID(self, recID, startDate, endDate):
        sql = 'UPDATE %s SET StartDate, EndDate WHERE RecID = (?)' % self.tableName
        self.runQuery(sql, (recID,))       


    def isOverrideActive(self, mmdd):
        """ See if an override is active for the given date"""
        
        sql = '''SELECT COUNT (*) FROM %s WHERE StartDate <= ? AND EndDate >= ?''' % self.tableName
        count = self.runSelectOne(sql, (mmdd, mmdd))
        if (count == None):
            return False
        if (count[0] == 0):
            return False
        return True
        
        

#-------------------------------------------------------------------------------
class TblRelayTimes(table.Table):
    """ Create an tblRelayTimes instance
    
    Relay times (Type = 0)
    
    Override times (Type = 1)
    During these periods the relay times are not activated. This allows the
    programming of bank holidays etc.
    
    :param db: is the database object (Database)
    
    """

    columnDefs = {  'RecID'     : 'INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL',
                    'StartTime' : 'TEXT NOT NULL',
                    'EndTime'   : 'TEXT NOT NULL',
                    'DOW'       : 'TEXT NOT NULL',
                    'IOBoard'   : 'INTEGER NOT NULL',
                    'Relay'     : 'INTEGER NOT NULL'
                    }
 
    def __init__(self, db, tableName = "tblRelayTimes"):
        super(TblRelayTimes, self).__init__(db, tableName)


    def add(self, startTime, endTime, dow, ioBoard, relay):
        sql = 'INSERT INTO %s (StartTime, EndTime, DOW, IOBoard, Relay ) VALUES (?,?,?,?,?)' % self.tableName
        self.runQuery(sql, (startTime, endTime, dow, ioBoard, relay))


    def selectAllOrderByTime(self):
        sql = 'SELECT * FROM %s ORDER BY DOW, StartTime, EndTime' % self.tableName
        return self.runSelectAll(sql)


    def deleteByRecID(self, recID):
        sql = 'DELETE FROM %s WHERE RecID = ?' % self.tableName
        self.runQuery(sql, (recID,) )
    
    
    def updateByRecID(self, recID, startTime, endTime, dow, ioBoard, relay):
        sql = 'UPDATE %s SET StartTime, EndTime, DOW, IOBoard, Relay WHERE RecID = (?,?,?,?,?,?)' % self.tableName
        self.runQuery(sql, (startTime, endTime, dow, ioBoard, relay, recID))       


    def selectAllFutureByRelayForDow(self, ioboard, relay, dow, hhmmss):
        sql = '''SELECT * from %s WHERE (IOBoard = ? AND Relay = ?) AND (StartTime > ? OR EndTime > ?)''' % self.tableName
        recs = self.runSelectAll(sql, (ioboard, relay, hhmmss, hhmmss))

        if (recs == None or len(recs) == 0):
            return None
        result = []
        for rec in recs:
            if str(dow) in rec['DOW']:
                result.append(rec)
        return result
        
        
    def getListOfRelaysUsed(self):
        sql = 'SELECT DISTINCT IOBoard, Relay FROM %s ORDER BY IOBoard, Relay' % self.tableName
        return self.runSelectAll(sql)
        

    def getAllActiveRelays(self, hhmmss, dow):
        sql = 'SELECT * from %s WHERE (? >= StartTime) AND (? < EndTime)' % self.tableName
        recs = self.runSelectAll(sql, (hhmmss, hhmmss))
        if (recs == None or len(recs) == 0):
            return None
        result = []
        for rec in recs:
            if str(dow) in rec['DOW']:
                result.append(rec)
        return result


    def getActiveRelay(self, ioboard, relay, hhmmss, dow):
        sql = 'SELECT * from %s WHERE (IOBoard = ?) AND (Relay = ?) AND  (? >= StartTime) AND (? < EndTime)' % self.tableName
        recs = self.runSelectAll(sql, (ioboard, relay, hhmmss, hhmmss))
        if (recs == None or len(recs) == 0):
            return None
        result = []
        for rec in recs:
            if str(dow) in rec['DOW']:
                result.append(rec)
        return result

        
    def getTodaysRelays(self, dow):
        sql = 'SELECT * from %s' % self.tableName
        recs = self.runSelectAll(sql)

        if (recs == None or len(recs) == 0):
            return None

        result = []
        for rec in recs:
            if str(dow) in rec['DOW']:
                result.append(rec)
        return result
    

#-------------------------------------------------------------------------------
class RelaySchedules(object):

    def __init__(self, db, tableName = 'tblRelay'):
        self.tableName = tableName
        super(RelaySchedules, self).__init__()
        self.__relays = TblRelayTimes(db, '%sTimes' % self.tableName)
        self.__overrides = TblRelayOverrides(db, '%sOverrides' % self.tableName)


    def open(self):
        self.__relays.open()
        self.__overrides.open()

        
    def drop(self):
        self.__relays.drop()
        self.__overrides.drop()


    def deleteAll(self):
        self.__relays.deleteAll()
        self.__overrides.deleteAll()

        
    def setRelayTime(self, startTime, endTime, dow, ioBoard, relay, recID=None):
        if (recID):
            self.__relays.updateByRecID(recID, startTime, endTime, dow, ioBoard, relay)
        else:
            self.__relays.add(startTime, endTime, dow, ioBoard, relay)

    def getNumberOfRelayTimes(self):
        return   self.__relays.count()
    
    def getNumberOfOverrides(self):
        return   self.__overrides.count()


    def deleteRelayTimeByRecID(self, recID):
        self.__relays.deleteByRecID(recID)
    
    
    def getAllRelayTimes(self):
        return self.__relays.selectAllOrderByTime()

    
    def setOverride(self, startmmdd, endmmdd, recID=None):
        if (recID):
            self.__overrides.updateByRecID(recID, startmmdd, endmmdd)
        else:
            self.__overrides.add(startmmdd, endmmdd)


    def isOverrideActive(self, mmdd):
        return self.__overrides.isOverrideActive(mmdd)
        
        
    def deleteOverrideByRecID(self, recID):
        self.__overrides.deleteByRecID(recID)


    def getAllOverrides(self):
        return self.__overrides.selectAllOrderByTime()
    
    
    def getActiveRelaysNow(self):
        return self.getAllActiveRelays(datetime.datetime.now())
    
    
    def selectAllFutureByRelayForDow(self, ioboard, relay, dow, hhmmss):
        return self.__relays.selectAllFutureByRelayForDow(ioboard, relay, dow, hhmmss)
    
        
    def getListOfRelaysUsed(self):
        return self.__relays.getListOfRelaysUsed()


    def isRelayActiveNow(self, ioboard, relay):
        return self.isRelayActive(ioboard, relay, datetime.datetime.now())
    
    
    def isRelayActive(self, ioboard, relay, when):
        hhmmss = when.strftime('%H:%M:%S')
        mmdd = when.strftime('%m/%d')
        if (self.__overrides.isOverrideActive(mmdd) == True):
            return False
        dow = when.isoweekday()
        recs = self.__relays.getActiveRelay(ioboard, relay, hhmmss, dow)
        if (recs == None or (len(recs) == 0)):
            return False
        return True

        
    def getAllActiveRelays(self, when):
        hhmmss = when.strftime('%H:%M:%S')
        mmdd = when.strftime('%m/%d')
        if (self.__overrides.isOverrideActive(mmdd) == True):
            return None
        dow = when.isoweekday()
        recs = self.__relays.getAllActiveRelays(hhmmss, dow)
        if (recs == None or (len(recs) == 0)):
            return None
#        for i in recs:
#            log.info( 'Found %s -> %s DOW %s R%s-%s' % (i['StartTime'], i['EndTime'], i['DOW'], i['IOBoard'], i['Relay']) )
        return recs


    def exportToXML(self, includeXMLHeaders=True):
        if (not includeXMLHeaders):
            data = []
        else:
            data = ['<?xml version="1.0" encoding="UTF-8"?>']
            data.append('''
            <!-- Relay Schedule Definitions
            
            This XML file defines the configured relay schedule. A relay schedule consists
            of a number of relay times defining the ON time for a particular relay. The schedule
            may also contain Override periods, these are dates during which the relay ON 
            time is ignored.
            
            Note: 
            The 'dayOfWeek' field format requires Mon=1 Sun=7. In order to include multiple 
            days e.g. Sat,Sun enter 6,7.
            The 'from/to' date format in the Override period is MM/DD
            
            The example below switches relay 1 on the first IOBoard at 9:00am for 10
            seconds except for January 1 and December 25/26 during which it is 
            ignored.
            
            <relaySchedules>
            
              <relayTimes>
                <relayTime>
                  <from>09:00:00</from>
                  <to>09:00:10</to>
                  <dayOfWeek>1,2,3,4,5,6,7</dayOfWeek>
                  <ioBoard>1</ioBoard>
                  <relay>1</relay>
                </relayTime>
              </relayTimes>
        
              <overridePeriods>
                  <overridePeriod>
                      <from>01/01</from>
                      <to>01/01</to>
                  </overridePeriod>
                  <overridePeriod>
                      <from>12/25</from>
                      <to>12/26</to>
                  </overridePeriod>
              </overridePeriods>
        
            </relaySchedules>
            
            -->''')
        
        data.append('<relaySchedules>')
        data.append('  <relayTimes>')
        for relayTime in self.__relays.selectAllOrderByTime():
            data.append('    <relayTime>')
            data.append('      <from>%s</from>' % relayTime['StartTime'])
            data.append('      <to>%s</to>' % relayTime['EndTime'])
            data.append('      <dayOfWeek>%s</dayOfWeek>' % relayTime['DOW'])
            data.append('      <ioBoard>%s</ioBoard>' % relayTime['IOBoard'])
            data.append('      <relay>%s</relay>' % relayTime['Relay'])
            data.append('    </relayTime>')
        data.append('  </relayTimes>')
        data.append('  <overridePeriods>')
        for op in self.__overrides.selectAllOrderByTime():
            data.append('    <overridePeriod>')
            data.append('      <from>%s</from>' % op['StartDate'])
            data.append('      <to>%s</to>' % op['EndDate'])
            data.append('    </overridePeriod>')
        data.append('  </overridePeriods>')
        data.append('</relaySchedules>')
        return '\n'.join(data)  
    
    def _toHHMMSS(self, text):
        fields = text.strip().split(':')
        if (len(fields) != 3):
            raise Exception('Invalid time "%s", time must be HH:MM:SS!' % text)
        try:
            hh = int(fields[0])
            mm = int(fields[1])
            ss = int(fields[2])
            if (hh < 0 or hh > 23 or mm < 0 or mm > 59 or ss < 0 or ss > 59):
                raise Exception('Invalid time "%s", time must be HH:MM:SS!' % text)
            return '%02d:%02d:%02d' % (hh, mm, ss)
        except:
            raise Exception('Invalid time "%s", time must be HH:MM:SS!' % text)

    def _toMMDD(self, text):
        fields = text.strip().split('/')
        if (len(fields) != 2):
            raise Exception('Invalid date "%s", date must be MM/DD!' % text)
        try:
            mm = int(fields[0])
            dd = int(fields[1])
            if (mm < 1 or mm > 12 or dd < 1 or dd > 31):
                raise Exception('Invalid date "%s", date must be MM/DD!' % text)
            return '%02d/%02d' % (mm, dd)
        except:
            raise Exception('Invalid date "%s", date must be MM/DD!' % text)
    
    
    def importFromXML(self, xmlData):
        """Take XML and populate the database"""
        relayData = []
        overrideData  = []
            
        root = xml.etree.cElementTree.fromstring(xmlData)
        if (root.tag != 'relaySchedules'):
            raise Exception('Error parsing XML; expected tag "relaySchedules" got "%s"' % root.tag)
        
        nodes = root.getchildren()
        for node in nodes:
            if (node.tag == 'relayTimes'):
                for rts in node:
                    if (rts.tag != 'relayTime'):
                        continue
                    for rt in rts:
                        if rt.tag == 'from':
                            startTime =  self._toHHMMSS(rt.text)
                        if rt.tag == 'to':
                            endTime = self._toHHMMSS(rt.text)
                        if rt.tag == 'dayOfWeek':
                            dow = rt.text
                        if rt.tag == 'ioBoard':
                            ioBoard = rt.text
                        if rt.tag == 'relay':
                            relay = rt.text
                    relayData.append( {'StartTime' : startTime, 
                                      'EndTime'    : endTime,
                                      'DOW'        : dow,
                                      'IOBoard'    : ioBoard,
                                      'Relay'      : relay} )
    
            if (node.tag == 'overridePeriods'):
                for ops in node:
                    if (ops.tag != 'overridePeriod'):
                        continue
                    for i in ops:
                        if i.tag == 'from':
                            fromDate = self._toMMDD(i.text)
                        if i.tag == 'to':
                            toDate = self._toMMDD(i.text)
                    overrideData.append( {'StartDate'    : fromDate, 
                                          'EndDate'      : toDate} )

            self.__relays.blockUpdate(relayData)
            self.__overrides.blockUpdate(overrideData)


#-------------------------------------------------------------------------------
class RelayBackgroundThread(threading.Thread):
    
    def __init__(self, ioboard, relay, relayTimes):
        super(RelayBackgroundThread, self).__init__()        
        self.__event = threading.Event()
        self.__relayTimes = relayTimes
        self.__ioboardNum = ioboard
        self.__relayNum = relay
    
    def __waitUntil(self, hhmmss, dow):
        log.dbg('R%s-%s waiting until %s (dow %s)' % (self.__ioboardNum, self.__relayNum, hhmmss, dow))
        while True:
            self.__event.wait(1)
            if (self.__event.isSet()):
                return None
            now = datetime.datetime.now()
            if (now.strftime('%H:%M:%S') >= hhmmss):
                if (dow == now.isoweekday()):
                    return now.strftime('%H:%M:%S')
        return None
    
    def __switchRelay(self, state, reqhhmmss):
        actualhhmmss = datetime.datetime.now().strftime('%H:%M:%S')
        if (actualhhmmss != reqhhmmss):
            log.warn('R%s-%s %s [%s] Switched late!'  % (self.__ioboardNum, self.__relayNum, reqhhmmss, actualhhmmss))
        try:
            log.dbg('R%s-%s %s [%s] %s'  % (self.__ioboardNum, self.__relayNum, reqhhmmss, actualhhmmss, 'ON' if state else 'OFF'))
            if (state):
                relayManager.setRelayAlwaysOn(self.__ioboardNum-1, self.__relayNum-1)
            else:
                relayManager.clearRelayAlwaysOn(self.__ioboardNum-1, self.__relayNum-1)
        except Exception as e:
            log.warn('R%s-%s Exception. (%s)' % (self.__ioboardNum, self.__relayNum, e))
                
    def run(self):
        log.dbg('R%s-%s thread running' % (self.__ioboardNum, self.__relayNum))

        # Put the relay into the correct state at start up
        curhhmmss = datetime.datetime.now().strftime('%H:%M:%S')
        self.__switchRelay(self.__relayTimes.isRelayActiveNow(self.__ioboardNum, self.__relayNum), curhhmmss)

        while True:
            if (curhhmmss == None):
                break

            now = datetime.datetime.now()
            curdow = now.isoweekday()
            tomorrowDow = (now + datetime.timedelta(days=1)).isoweekday()
            curmmdd = now.strftime('%m/%d')

            if (self.__relayTimes.isOverrideActive(curmmdd)):
                log.dbg('R%s-%s Override active' % (self.__ioboardNum, self.__relayNum))
                curhhmmss = self.__waitUntil('00:00:00', tomorrowDow)
                continue

            # Retrieve a set of all relay schedules for later today (i.e. AFTER curhhmmss)
            rt = self.__relayTimes.selectAllFutureByRelayForDow(self.__ioboardNum, self.__relayNum, curdow, curhhmmss)
            if (rt == None or len(rt) == 0):
                curhhmmss = self.__waitUntil('00:00:00', tomorrowDow)
                continue

            times = []            
            for i in rt:
                log.dbg( 'R%s-%s, %s -> %s, DOW %s' % (i['IOBoard'], i['Relay'], i['StartTime'], i['EndTime'], i['DOW']) )
                if (i['StartTime'] > curhhmmss):
                    times.append({ 'Time' : i['StartTime'], 'State' : True})
                if (i['EndTime'] > curhhmmss):
                    times.append({ 'Time' : i['EndTime'],   'State' : False})
            times.sort(key = lambda i: i['Time'], reverse=False)

            try:
                # Wait for the first scheduled time in the list, then toggle the relay. Because
                # this updates curhhmmss, the next time round the loop this entry will not be
                # included in the 'times' list.
                curhhmmss = self.__waitUntil(times[0]['Time'], curdow)
                if (curhhmmss == None):
                    continue
                self.__switchRelay(times[0]['State'], times[0]['Time'])                        

            except Exception as e:
                log.warn('R%s-%s Exception. (%s)' % (self.__ioboardNum, self.__relayNum, e) )
                crashReport.createCrashReportFromException()
                curhhmmss = self.__waitUntil('00:00:00', tomorrowDow)

        log.dbg('R%s-%s exiting main loop' % (self.__ioboardNum, self.__relayNum) )

                    
            
    def stop(self):
        self.__event.set()
        self.join(2)




#-------------------------------------------------------------------------------
_relayThread = []

def startRelayThreads():
    
    relayScheds = RelaySchedules(getAppDB())
    relayScheds.open()
    relays = relayScheds.getListOfRelaysUsed()
    
    for i in relays:
        _relayThread.append( RelayBackgroundThread(i['IOBoard'], i['Relay'], relayScheds) )
    
    for i in _relayThread:
        i.start()

    
def stopRelayThreads():  
    global _relayThread
    for i in _relayThread:
        i.stop()
    _relayThread = []
        
      
        
#
## \}
