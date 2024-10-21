# -*- coding: utf-8 -*-
#
# Copyright 2011 Grosvenor Technology
#

from applib.db import sqlTime, database, tblSettings, tblTransactions
import xml.etree.cElementTree as ET
import log

_trans = None

def getAppTransactions():
    """Get global clockserver transaction table object."""
    global _trans
    if (_trans == None):
        clksrv1Functions = tblSettings.getAppSetting('clksrv_functions')
        clksrv2Functions = tblSettings.getAppSetting('clksrv2_functions')
        if (clksrv1Functions != None and 'trans' in clksrv1Functions):
            log.dbg('Using primary clockserver for transactions')
            prefix = 'clksrv'
        elif (clksrv2Functions != None and 'trans' in clksrv2Functions):
            log.dbg('Using secondary clockserver for transactions')            
            prefix = 'clksrv2'
        else:
            log.warn('No clockserver configured for transactions, using primary one!')
            prefix = 'clksrv'
        warnLevel = tblSettings.getAppSetting('%s_trans_warn_level' % prefix)
        maxLevel  = tblSettings.getAppSetting('%s_trans_max_level' % prefix)        
        keepTime  = tblSettings.getAppSetting('%s_trans_keep_time' % prefix)        
        _trans = Transaction(database.getAppDB(), warnLevel, maxLevel, keepTime)
    return _trans


#-------------------------------------------------------------------------------
class Transaction(tblTransactions.TblTransactions):
    """Clockserver Transaction class. """

    columnDefs = {'TransID' : 'INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL', 
                  'Sent'    : 'INTEGER DEFAULT "0" NOT NULL',
                  'Time'    : 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL',
                  'Data'    : 'TEXT NOT NULL',
                  'Event'   : 'TEXT',
                  'DataType': 'TEXT' }

    #-----------------------------------------------------------------------
    def __init__(self, db, warnLevel=1000, maxLevel=20000, keepTime = 60*60*24, retryTime = 60):
        super(Transaction, self).__init__(db, "tblTrans", warnLevel, maxLevel, keepTime, retryTime)

    def open(self, comm=None):
        """Open/create transaction table and start background thread for sending transactions. """
        super(Transaction, self).open()
        # don't start thread if comm is None
        if (comm != None):
            log.dbg('Starting transaction thread with %s' % comm.getName())
            # Create sender
            sender = TransactionSender(comm)
            # Start transaction thread
            self.startThread(sender)

    def create(self):
        super(Transaction, self).create()
        log.dbg("Creating index for %s" % self.tableName)
        self.runQuery('CREATE INDEX %sIndex ON %s(Time);' % (self.tableName, self.tableName))

    def addClocking(self, transTime, transData, transEvent=None, transDataType=None):
        """Add clocking to transaction table and send when possible. """
        self.insert({'Time':transTime, 'Data': transData, 'Event': transEvent, 'DataType': transDataType})
        
    def addClockingTag(self, emp, transTime, transDataTag, transEvent=None, transDataType=None):
        """ Add clocking to transaction table (see :meth:`addClocking`). *transDataTag* is an
            ElementTree element containing the transaction data. Employee ID, identification
            and verification methods are added by this method.
        """
        ET.SubElement(transDataTag, 'empID').text = emp.getEmpID()
        ET.SubElement(transDataTag, 'identifiedBy').text = emp.getUsedIdentificationMethod()
        ET.SubElement(transDataTag, 'verifiedBy').text = emp.getUsedVerificationMethod()
        transData = ET.tostring(transDataTag)
        self.insert({'Time':transTime, 'Data': transData, 'Event': transEvent, 'DataType': transDataType})
        


class TransactionSender(object):

    def __init__(self, comm):
        self.comm = comm

    def prepare(self):
        self.__conn = None

    def send(self, data):
        log.dbg("Sending transaction #%s" % data['TransID'])
        log.dbg("    transaction time : %s" % data['Time'])
        log.dbg("    transaction data : %s" % data['Data'])

        localTime = sqlTime.sqlTime2MyLocalTime(data['Time'], '%Y-%m-%dT%H:%M:%S%z')
        if (not self.comm.useTimeZoneOffset()):
            localTime = localTime[0:19]
        
        transEvent    = data['Event'] if (data['Event'] != None) else ''
        transData     = data['Data']
        transDataType = ' type="%s"' % data['DataType'] if (data['DataType'] != None) else ''
        
        log.dbg("Local time of transaction was %s" % localTime)
        
        # Reuse connection of possible
        if (self.__conn == None):
            self.__conn = self.comm.getConnection()
                    
        rsp = self.comm.send(
                "    <trans>\n"
                "      <event>%s</event>\n"
                "      <data%s>%s</data>\n"
                "      <time>%s</time>\n"
                "    </trans>\n"
                % (transEvent, transDataType, transData, localTime), conn=self.__conn)

        if (rsp.find("<transRsp>clearTransaction") < 0):
            raise Exception('Server Error (%s)' % rsp)

    def postSend(self, ignore=None):
        # Close connection once all pending transactions were sent
        if (self.__conn != None):
            self.__conn.close()

