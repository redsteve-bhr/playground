# -*- coding: utf-8 -*-
#
# Copyright 2010 Grosvenor Technology
#

"""
:mod:`tblTransactions` --- Transaction table class
===================================================

This class implements an abstract transaction table.

A transaction (here) is basically just a message. These messages inform
a server about certain new events and get then marked as sent or deleted.
Because there is no answer, apart from the success or failure of receiving
the message, transactions can be sent in a background thread. Transactions
could be used for:

    - bookings, clockings
    - certain events (e.g. door opened or closed)
    - alarms

In fact, transactions can be used whenever there is no answer from a server
needed and when it is sufficient to send the transaction at the next 
possible moment without needing to know when they actually arrived at the server.
But nevertheless, a transaction will be resent until it was successfully 
transmitted.

This class provides the functions to store a transaction into a table and to
send new transactions in a background thread. From the developers point of 
view, inserting a transaction into the database, means sending it at the
next possible moment.

Nevertheless, it is still required to derive from this class to define the 
transaction data layout and the function for adding a new transaction. 

Example::

    class MyTransactions(tblTransactions.TblTransactions):
    
        columnDefs = {  'TransID': 'INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL',
                        'Sent'   : 'INTEGER DEFAULT "0" NOT NULL',
                        'Time'   : 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL',
                        'Data'   : 'TEXT NOT NULL' }
    
        def __init__(self, db):
            super(MyTransactions, self).__init__(db, "tblTrans")
    
        def addTrans(self, transTime, transData):
            self.insert({'Time':transTime, 'Data': transData})


This example shows a fully functional transaction class. This transaction has
a 'Time' and 'Data' field. Additionally all transaction tables must have a 
'TransID' and a 'Sent' field! 

The addTrans() function allows it to add new transactions. The insert() 
function used here is implemented in :class:`TblTransactions`. In addition to the 
implementation in :class:`applib.db.table.Table`, this function also notifies the transaction thread
about a new transaction.

Implementation of :meth:`TblTransactions.insert`::

   def insert(self, row):
        with self.cond:
            # Insert new data
            super(TblTransactions, self).insert(row)
            # Tell waiting threads to wake up
            self.cond.notifyAll()
        self.unsentTransactions += 1


This is very important to understand, because if a new transaction is added
by not using :meth:`TblTransactions.insert()` but :meth:`applib.db.table.Table.runQuery()` or 
using the database directly, it is necessary to wake up the thread as shown above.

The MyTransactions class defines the data layout of a transaction and 
provides a function for adding them. But in order to really send a 
transaction, it is necessary to implement a sender class. An instance of
such a class must then be given to the thread, when starting it.

Example::

    self.trans = MyTransactions(self.db)
    self.trans.open()
    self.startThread(sender)

The :meth:`TblTransactions.startThread()` function takes a sender object as argument. The sender 
must have a *prepare()* and a *send()* function. Because the data layout of the 
transaction and the sender itself are quite related to each other (one 
defines the data, the other sends it), it might be a good idea to hide the
sender class behind the transaction class.

Example::

    class MyTransactions(TblTransactions.TblTransactions):

        # [...]
    
        def startThread(self):
            sender = MySender()
            super(MyTransactions, self).startThread(sender)
           
        # [...]
    
    class MySender():

        def prepare(self):
            pass

        def send(self, data):
            self.sendToServer(data['Time'], data['Data'])


The *prepare()* function can be used to load or initialise the sender in the
background, rather then in the main thread.

If the *send()* function runs without exceptions, the transaction will be marked as sent.
If *send()* raises an exception, the background thread will try to send the 
transaction again after the *retryTime*.


"""



from threading import Condition, Thread
import log
from table import Table
import sqlTime
import time
import datetime

class TblTransactions(Table):
    """ Create a tblTransaction Class Instance.    
    *db* is a :class:`applib.db.database.Database` class and *tblName* is the name of 
    the transaction table. *warnLevel* is the number of unsent transactions to start 
    showing warnings. *maxLevel* is the maximum number of unsent transactions before :meth:`hasSpace`
    returns **False**. *keepTime* is the number of seconds to keep sent transactions 
    in the database before removing. *retryTime* is the number of seconds to wait before 
    retry sending a transaction after a failure.
    """
    
    def __init__(self, db, tblName, warnLevel=1000, maxLevel=20000, keepTime = 60*60*24, retryTime = 60):
        self.warnLevel = int(warnLevel)
        self.maxLevel  = int(maxLevel)
        self.keepTime  = int(keepTime)
        self.retryTime = int(retryTime)
        self.thread = None
        self.cond   = Condition()        
        super(TblTransactions, self).__init__(db, tblName)

    def open(self):
        """ Opens the transaction table"""
        super(TblTransactions, self).open()
        self.unsentTransactions = self.getNumberUnsent()
        log.dbg("Unsent Transactions: %d" % self.unsentTransactions)
        
    def close(self):
        """ Closes the transaction table and stops transaction thread."""
        super(TblTransactions, self).close()
        self.stopThread()

    def startThread(self, sender):
        """Starts the transaction thread.
        
        This thread will wait for new transactions to come in and then
        call the *sender* to send the next transaction.
        The *sender* must implement a *prepare* and *send* function.
        """
        log.dbg("Starting thread...")
        self.thread = TblTransactionsThread(self, sender, self.retryTime)
        self.thread.start()
    
    def stopThread(self, timeout=5):
        """ Stop transaction thread. *timeout* is the nummer of seconds
        to wait for the thread to stop.
        
        .. versionchanged:: 1.6
          Added optional timeout parameter, defaults to 5 seconds.
          
        """
        log.dbg("Stopping thread...")
        with self.cond:
            if (self.thread):
                self.thread.running = False
            self.cond.notifyAll()
        if (self.thread):
            self.thread.join(timeout)

    def getUnsentDataBySQL(self, sql, timeout=None, maxResults=200):
        # acquire lock
        with self.cond:
            # get the next unsent transactions
            data = self.runSelectAll(sql)
            # if we got no data, wait until we got notified
            if (not data):
                self.cond.wait(timeout)
            # try again
            data = self.runSelectAll(sql)
        return data

    def getUnsentData(self, timeout=None, maxResults=200):
        sql = '''SELECT *
                FROM %s
                WHERE Sent = '0'
                ORDER BY Time
                LIMIT %d''' % (self.tableName, maxResults)
        return self.getUnsentDataBySQL(sql, timeout, maxResults)

    def interruptibleWait(self, timeout):
        with self.cond:
            self.cond.wait(timeout)

    def markAsSent(self, transID):
        sql = "UPDATE %s SET Sent = '1' WHERE TransID = (?)" % self.tableName
        self.runQuery(sql, (transID,))
        log.dbg("TransID #%d marked as sent" % transID)
        self.unsentTransactions -= 1

    def getExpiryTimestamp(self):
        period = datetime.timedelta(seconds=self.keepTime)
        expiryTime = datetime.datetime.utcnow() - period
        return expiryTime.strftime(sqlTime.sqlTimeFormat)

    def deleteOldSentTransactions(self):
        # if keepTime is negative, then do not delete 
        # old items at all
        if (self.keepTime < 0):
            return
        sql = 'DELETE FROM %s WHERE Sent = "1" AND Time < (?)' % self.tableName
        deleted = self.runQuery(sql, (self.getExpiryTimestamp(),))
        if (deleted):
            log.dbg('Deleted %d old transactions' % deleted)

    def insert(self, row):
        """ Insert transaction into table.
        
        This function is the same as Table.insert(), but it will also 
        notify the transaction thread about a new transaction to send.
        """
        with self.cond:
            # Insert new data
            super(TblTransactions, self).insert(row)
            # Tell waiting threads to wake up
            self.cond.notifyAll()
        self.unsentTransactions += 1

    def blockUpdate(self, data):
        super(TblTransactions, self).blockUpdate(data)
        # Update the count as the insert has not been called
        self.unsentTransactions = self.getNumberUnsent()

    def selectLast(self, numTrans):
        """ Select last transactions.
        
        This function returns the last *numTrans* transactions as a list of rows.
        """
        
        sql = '''SELECT strftime('%%s', Time) AS UnixTime,* 
                FROM %s 
                ORDER BY Time DESC 
                LIMIT ?''' % self.tableName
        return self.runSelectAll(sql, (numTrans,))

    def getNumberUnsent(self):
        """ Get the number of unsent transactions. """
        sql = '''SELECT COUNT (*) 
                  FROM %s 
                  WHERE Sent = 0''' % self.tableName
        count = self.runSelectOne(sql)
        if (count == None):
            return 0
        return count[0]
        
    def getOldestSent(self):
        """ Return SQL timestamp of oldest sent transaction of ``None``."""
        sql = 'SELECT Time FROM %s WHERE Sent = "1" ORDER BY Time ASC' % self.tableName
        res = self.runSelectOne(sql)
        return res[0] if res != None else None
    
    def getOldestUnsent(self):
        """ Return SQL timestamp of oldest unsent transaction of ``None``."""        
        sql = 'SELECT Time FROM %s WHERE Sent = "0" ORDER BY Time ASC' % self.tableName
        res = self.runSelectOne(sql)
        return res[0] if res != None else None
    
    def getLastSent(self):
        """ Return SQL timestamp of last sent transaction of ``None``."""        
        sql = 'SELECT Time FROM %s WHERE Sent = "1" ORDER BY Time DESC' % self.tableName
        res = self.runSelectOne(sql)
        return res[0] if res != None else None
        
    def getLastUnsent(self):
        """ Return SQL timestamp of last unsent transaction of ``None``."""        
        sql = 'SELECT Time FROM %s WHERE Sent = "0" ORDER BY Time DESC' % self.tableName
        res = self.runSelectOne(sql)
        return res[0] if res != None else None
    
    def getNumberOfSentTransactionsAfter(self, sqlTime):
        """ Return number of sent transactions after (or at) *sqlTime*."""
        sql = 'SELECT COUNT(*) FROM %s WHERE Sent = "1" AND Time >= (?)' % self.tableName
        count = self.runSelectOne(sql, (sqlTime,))
        if (count == None):
            return 0
        return count[0]

    def selectTransactionsAfter(self, sqlTime, numTrans):
        """ Return number of sent transactions after (or at) *sqlTime*."""
        sql = 'SELECT * FROM %s WHERE Time > (?) LIMIT ?' % self.tableName
        return self.runSelectAll(sql, (sqlTime, numTrans))
    
    def markAsUnsentAfter(self, sqlTime):
        """ Mark sent transactions after *sqlTime* as unsent."""
        sql = "UPDATE %s SET Sent = '0' WHERE Time >= (?)" % self.tableName
        self.runQuery(sql, (sqlTime,))
        self.unsentTransactions = self.getNumberUnsent() 
        
    def hasSpace(self):
        """ Test if there is space to save new transactions
        
        This function calculates the number of transactions that can still be 
        stored in the table. Sent transactions are NOT counted. It uses the 
        *maxLevel* to calculate the space.
        If there is still space for new transactions, **True** is returned.
        """
        log.dbg("Unsent trans %d Max %d" % (self.unsentTransactions, self.maxLevel))
        if (self.unsentTransactions >= self.maxLevel):
            # try deleting some sent transactions
            log.dbg("Transaction buffer full")
            return False
            
        return True

    def getWarnings(self):
        """ Get any warnings (used by :mod:`applib.utils.healthMonitor`). """
        warnings = []
        if (self.unsentTransactions >= self.maxLevel):
            warnings.append( {'msg': _('Transaction buffer full')})
        elif (self.unsentTransactions >= self.warnLevel):
            warnings.append( {'msg': _('Transaction buffer level high')})
        return warnings
        
    def getHealthName(self):
        return _('Transaction Status')
  
    def getHealth(self):
        """ Get the health of the transaction buffer 
        (used by :mod:`applib.utils.healthMonitor`). """
        # get the count of unsent
        self.unsentTransactions = self.getNumberUnsent() 
        totalTransactions = self.count()
        if (self.unsentTransactions >= self.warnLevel):
            healthy = False
        else:
            healthy = True
        items = [ ( _('Unsent'),  '%d' % self.unsentTransactions),
                  ( _('Total'), '%d' % totalTransactions),
                  ( _('Warn Level'), '%d' % self.warnLevel),
                  ( _('Max Level'), '%d' % self.maxLevel)]
        if (self.thread and self.thread.lastError):
            items.append( ( _('Last Error'), self.thread.lastError) )
        return (self.getHealthName(), healthy, items)



class TblTransactionsThread(Thread):

    def __init__(self, dmTrans, sender, retryTime=60):
        super(TblTransactionsThread, self).__init__()
        self.dmTrans   = dmTrans
        self.sender    = sender
        self.retryTime = retryTime
        self.lastError = None
        self.running   = False

    def run(self):
        self.running = True
        time.sleep(5)
        self.sender.prepare()
        while (self.running):
            data = self.dmTrans.getUnsentData()
            if (not data):
                continue
            log.dbg("Got %d transactions" % len(data))
            for trans in data:
                try:
                    self.sender.send(trans)
                    self.dmTrans.markAsSent(trans["TransID"])
                    self.lastError = None
                except Exception as e:
                    log.err('Failed to send transaction (%s)' % e)
                    self.lastError = str(e)
                    self.dmTrans.interruptibleWait(self.retryTime)
                    break
            if (hasattr(self.sender, 'postSend')):
                self.sender.postSend(self.dmTrans)
            self.dmTrans.deleteOldSentTransactions()
        log.dbg("Exiting thread")

