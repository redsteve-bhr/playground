# -*- coding: utf-8 -*-
#
# Copyright 2010 Grosvenor Technology
#


"""
:mod:`table` --- Table class
===================================

"""

import log
import time

class Table(object):
    """Create a table class instance. *db* is a :class:`applib.db.database.Database` class
    and *tbName* is the name of the table.
    """
    def __init__(self, db, tbName):
        self.db    = db
        self.tableName = tbName
        self.wasOpened = False

    def open(self):
        """ Open table (create if necessary)."""
        self.wasOpened = True
        if (not self.db.isOpen()):
            self.db.open()
        if (not self.exists()):
            self.create()
        if (hasattr(self, 'columnDefs')):
            self._checkColumns(self.columnDefs)
        log.dbg("Opening table %s" % self.tableName)

    def create(self):
        """Create table.

        This function gets called by :meth:`open()` when the table does not exist
        yet. It should therefore not be called directly.
        This function will look for *self.columnDefs* and *self.tableConstraints*
        which should be defined in the implementation of a table class. 
        If *self.columnDefs* is not defined, this function will raise an exception. 

        If defining *columnDefs* and *tableConstraints* is not flexible enough, 
        overloading this function is an option. In that case this function 
        (the implementation in Table) must not be called.
        
        """
        if (not hasattr(self, 'columnDefs')):
            log.err("No create function or column definition for table %s" % self.tableName)
            raise NameError, 'create function not implemented'
        
        if (hasattr(self, 'tableConstraints')):
            tableConstraints = ', ' + ', '.join(self.tableConstraints)
        else:
            tableConstraints = ''
            
        columnDef = ', '.join([ '[%s] %s' % (n, t) for n, t in self.columnDefs.items()])
        sql = 'CREATE TABLE [%s] (%s%s)' % (self.tableName, columnDef, tableConstraints)
        log.dbg('Creating table %s' % self.tableName)
        self.runQuery(sql)
        self.updateTableVersion()
    
    def updateTableVersion(self):
        """ Update table version. This method is automatically
        called on table creation (:meth:`create`) if the table 
        class object has a *version* variable.
        
        Example::

            class ColourTable(table.Table):
            
                columnDefs = {  'ID'          : 'INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL',
                                'Name'        : 'EXT NOT NULL',
                                'Colour'      : 'TEXT NOT NULL' }
            
                version = 2
                
                def __init__(self, db, tblName='tblColour'):
                    super(ColourTable, self).__init__(db, tblName)
                    
        .. seealso::
            :meth:`removeTableVersion`
            :meth:`getTableVersion`
            :meth:`hasVersionChanged`

        .. versionadded:: 2.2
        """
        if (not hasattr(self, 'version')):
            return
        tableVersions = TblTableVersions(self.db)
        tableVersions.open()
        tableVersions.setVersionForTable(self.tableName, self.version)

    def removeTableVersion(self):
        """ Remove version information of table. This method is
        automatically called when :meth:`drop` is executed.
        
        .. seealso::
            :meth:`updateTableVersion`
            :meth:`getTableVersion`
            :meth:`hasVersionChanged`

        .. versionadded:: 2.2
        """         
        tableVersions = TblTableVersions(self.db)
        tableVersions.open()
        tableVersions.removeVersionForTable(self.tableName)
    
    def getTableVersion(self):
        """ Get table version or *0* if unknown.

        .. seealso::
            :meth:`updateTableVersion`
            :meth:`removeTableVersion`
            :meth:`hasVersionChanged`

        .. versionadded:: 2.2
        """         
        tableVersions = TblTableVersions(self.db)
        tableVersions.open()
        return tableVersions.getVersionForTable(self.tableName)

    def hasVersionChanged(self):
        """ Return **True** if current table version is different from 
        version when table was created.

        .. seealso::
            :meth:`updateTableVersion`
            :meth:`removeTableVersion`
            :meth:`getTableVersion`

        .. versionadded:: 2.2
        """         
        if (not hasattr(self, 'version')):
            return False
        return self.version != self.getTableVersion()
        
    def _checkColumns(self, columnDefs):
        """ Checks whether all 'optional' columns exist and creates them if needed."""
        columns = self.getColumnNames()
        for colName, colDef in columnDefs.items():
            if (colName in columns):
                continue
            if (not colDef):
                log.err('Column %s needed but don`t know how to create?!' % colName)
            else:
                log.dbg('Creating column %s' % colName)
                self.runQuery('ALTER TABLE %s ADD COLUMN [%s] %s' % (self.tableName, colName, colDef))

    def close(self):
        """ Close table"""
        log.dbg("Closing table %s" % self.tableName)

    def exists(self):
        """Return True if table exists."""
        return self.db.tableExists(self.tableName)
    
    def rename(self, newName):
        """ Rename table name to *newName*.
        
        .. note:: This method does not change *self.tableName*, which means that
                  when left unchanged, any subsequent SQL commands will fail.
                  
        .. versionadded:: 2.0
                
        """ 
        sql = 'ALTER TABLE "%s" RENAME TO "%s"' % (self.tableName, newName)
        self.runQuery(sql)
    
    def getColumnNames(self):
        """Return a list of column names."""
        sql = 'PRAGMA table_info("%s")' % self.tableName
        cols = self.runSelectAll(sql)
        return [ c['name'] for c in cols]
        
    def getColumnTypes(self):
        """Return dictionary of column names with types.

        .. versionadded:: 2.0
                
        """        
        sql = 'PRAGMA table_info("%s")' % self.tableName
        cols = self.runSelectAll(sql)
        types = {}
        for c in cols:
            types[c['name']] = c['type']
        return types
        
    def drop(self):
        """Delete table from database."""
        self.db.dropTable(self.tableName)
        self.removeTableVersion()

    def deleteAll(self):
        """ Delete all entries in table"""
        # empty the table
        log.dbg("Deleting all entries from table %s" % self.tableName)
        sql = "DELETE FROM %s" % self.tableName
        log.sql(sql)
        with _SQLTimeWarning(sql):        
            with self.db.lock:
                self.db.dbcursor.execute(sql)
                self.db.dbconn.commit()

    def selectAll(self):
        """ Select all data and return a list of rows or None."""
        sql = 'SELECT * FROM %s' % self.tableName
        return self.runSelectAll(sql)

    def count(self):
        """ Count the number of rows / entries in the table. """
        sql = "SELECT COUNT (*) FROM %s" % self.tableName
        log.sql(sql)
        with _SQLTimeWarning(sql):
            with self.db.lock:
                try:
                    self.db.dbcursor.execute(sql)
                    result_set = self.db.dbcursor.fetchone()
                except:
                    result_set = None
        if (result_set == None):
            return 0
        return (result_set[0])

    def runQuery(self, sql, args=()):
        """ Execute a SQL command
    
        This function executes a SQL command. It does not expect or return
        any data back.
        The first argument is the SQL command. The second argument can be a tuple.
        Each question mark is replaced by a value from the tuple. Which 
        means that this:
        
        Example::
        
            self.runQuery('INSERT INTO myTable (Name, Colour) VALUES (?, ?)', ('red', '#ff0000'))
        
                
        will result in this SQL command:
        INSERT INTO myTable (Name, Colour) VALUES ('red' '#ff000000')

        *sql* is the SQL command and *args* is an optional tuple with arguments 
        for the SQL command.
        
        """
        if (not self.wasOpened):
            log.warn('Table %s used before opening it!' % self.tableName)
        # Just logging
        self.log(sql, args)
        with _SQLTimeWarning(sql,args):
            with self.db.lock:
                self.db.dbcursor.execute(sql, args)
                self.db.dbconn.commit()
                return self.db.dbcursor.rowcount

    def runSelectOne(self, sql, args=()):
        """ Execute a SQL query
    
        This function does the same as :meth:`runQuery()` but will return the first
        data row of the result.
        
        Example::
            
            res = self.runSelectOne('SELECT * FROM myTable WHERE Name = ?', ('red', ))
            if (res != None):
                print "Colour code for %s is %s" % (res['Name'], res['Colour'])
            else:
               print "No colour code found"
               
    
        *sql* is the SQL command and *args* is an optional tuple with arguments 
        for the SQL command.
        
        """
        if (not self.wasOpened):
            log.warn('Table %s used before opening it!' % self.tableName)
        self.log(sql, args)
        with _SQLTimeWarning(sql,args):
            with self.db.lock:
                self.db.dbcursor.execute(sql, args)
                return self.db.dbcursor.fetchone()

    def runSelectAll(self, sql, args=()):
        """ Execute SQL query.
        
        This function does exactly the same as :meth:`runSelectOne()` but will
        return the whole result as list of rows.
        
        Example::
            
            res = self.runSelectAll('SELECT * FROM myTable')
            
            for row in res:
                print "Colour code for %s is %s" % (row['Name'], row['Colour'])
        
        
        *sql* is the SQL query and *args* is an optional tuple with arguments for 
        the SQL command.

        """
        if (not self.wasOpened):
            log.warn('Table %s used before opening it!' % self.tableName)
        self.log(sql, args)
        with _SQLTimeWarning(sql,args):
            with self.db.lock:
                self.db.dbcursor.execute(sql, args)
                return self.db.dbcursor.fetchall()

    def insert(self, row, replace=False):
        """ Insert data into table.
        
        This is a convenient function to insert new data into a table. A
        SQL INSERT statement is execute based on the keys and values of 
        the dictionary *row*. If *replace* is **True** an 'INSERT OR REPLACE'
        SQL statement is used.

        Example::

            row = {'Name':'red', 'Colour': '#ff0000'}
            table.insert(row)
        
        The above code will result in the following SQL command::
        
            INSERT INTO TableName (Name, Colour) VALUES ('red', '#ff0000')
        
        .. versionchanged:: 2.0
            Optional *replace* parameter added.
            
        """
        if (not self.wasOpened):
            log.warn('Table %s used before opening it!' % self.tableName)
        sql = self._createInsertFromDict(row, replace=replace)
        self.runQuery(sql, row.values())

    def insertOrReplace(self, row, key):
        log.warn('Deprecated method "Table.insertOrReplace" called, use Table.insert(row, replace=True).')
        self.insert(row, True)

    def _createInsertFromDict(self, row, tableName=None, replace=False):
        # build name and values list
        if (tableName == None):
            tableName = self.tableName
        names  = ""
        values = ""
        for key in row.keys():
            names  = names + ("%s," % key)    
            values = values + "?,"
        names  = names.rstrip(',')
        values = values.rstrip(',')
        if (replace):
            sql = "INSERT OR REPLACE INTO %s (%s) VALUES (%s)" % (tableName, names, values)
        else:
            sql = "INSERT INTO %s (%s) VALUES (%s)" % (tableName, names, values)
        return sql

    def runQueries(self, *batch):
        """ Execute a batch of SQL commands.

        This method works like :meth:`runQuery`, but accepts many SQL commands. 
        Each parameter to this method must be a tuple containing the SQL command as string
        and the arguments to that command as tuple.
        
        Example using runQuery twice::
        
            self.runQuery('INSERT INTO myTable (Name, Colour) VALUES (?, ?)', ('red', '#ff0000'))
            self.runQuery('INSERT INTO myTable (Name, Colour) VALUES (?, ?)', ('green', '#00FF00'))            
        
        Example using runQueries::
        
            insertRed =   ('INSERT INTO myTable (Name, Colour) VALUES (?, ?)', ('red', '#ff0000'))
            insertGreen = ('INSERT INTO myTable (Name, Colour) VALUES (?, ?)', ('green', '#00FF00'))
            self.runQueries( insertRed, insertGreen )            


        .. versionadded:: 1.8

        """
        if (not self.wasOpened):
            log.warn('Table %s used before opening it!' % self.tableName)
        # Just logging
        for (sql, args) in batch:
            self.log(sql, args)
        with _SQLTimeWarning(sql,args):
            rowcount = 0
            with self.db.lock:
                try:
                    for (sql, args) in batch:            
                        self.db.dbcursor.execute(sql, args)
                        rowcount += self.db.dbcursor.rowcount
                    self.db.dbconn.commit()
                except:
                    self.db.dbconn.rollback()
                    raise            
            return rowcount

    def blockUpdate(self, data):
        """Execute block update
        
        This function deletes the content of the table and inserts
        each dictionary item in data as a new row. If a step fails the 
        operation is rolled back.
        
        Example::
        
            data = [ { 'Name': 'black', 'Colour': '#000000' },
                     { 'Name': 'white', 'Colour': '#ffffff' },
                     { 'Name': 'red',   'Colour': '#ff0000' },
                     { 'Name': 'blue',  'Colour': '#0000ff' }, ]
            tblColour.blockUpdate(data)


        *data* is a list of dictionaries, defining rows.
        
        """
        if (not self.wasOpened):
            log.warn('Table %s used before opening it!' % self.tableName)
        with self.db.lock:
            try:
                sql = "DELETE FROM %s" % self.tableName
                self.db.dbcursor.execute(sql)
                for row in data:
                    sql = self._createInsertFromDict(row)
                    self.db.dbcursor.execute(sql, row.values())
    
                self.db.dbconn.commit()
            except Exception as e:
                self.db.dbconn.rollback()
                log.err('Failed in blockUpdate (%s)' % e)
                raise

    def log(self, sql, args=()):
        """ Do pretty logging.
        
        .. versionadded:: 1.5
 
        """
        if (not log.sql_enabled):
            return
        try:
            for l in getFormattedSQL(sql, args):
                log.sql(l)
        except Exception as e:
            log.err('SQL Log failed: %s ("%s", "%s")' % (e, sql, args))
            log.sql('%s %s' % (sql, args))



class TblTableVersions(Table):

    columnDefs = {  'Name'     : 'TEXT UNIQUE NOT NULL PRIMARY KEY',
                    'Version'  : 'INTEGER DEFAULT 0'
                 }

    def __init__(self, db, tableName='tblTableVersions'):
        super(TblTableVersions, self).__init__(db, tableName)

    def setVersionForTable(self, name, version):
        sql = "INSERT OR REPLACE INTO %s (Name, Version) VALUES (?, ?)" % self.tableName
        self.runQuery(sql, (name, version))

    def getVersionForTable(self, name):
        sql = 'SELECT Version FROM %s WHERE Name = ?' % self.tableName
        result = self.runSelectOne(sql, (name,))
        if (result != None):
            return result['Version']
        return 0
    
    def removeVersionForTable(self, name):
        sql = "DELETE FROM %s WHERE Name = ?" % self.tableName
        self.runQuery(sql, (name,))




def getFormattedSQL(sql, args=()):
    """ Return formatted SQL."""
    sqlKeywords = ['WHERE', 'ORDER BY', 'LIMIT', 'GROUP BY', 'SET', 'VALUES'] 
    stm = ' '.join( [ l.strip() for l in sql.splitlines() ])
    if (not stm.endswith(';')):
        stm += ';'
    # insert parameters
    if (len(args) > 0):
        stm = stm.replace('(?)', "'%s'")
        stm = stm.replace('?', "'%s'")
        stm = stm % tuple(args)
    if (not stm.startswith('SELECT *') and not stm.startswith('DELETE')):
        sqlKeywords.append('FROM')
    # line break on keywords
    for k in sqlKeywords:
        stm = stm.replace(k, '\n    %s' % k)
    # line break on comma and opening bracket for CREATE and INSERT statements
    if (stm.startswith('CREATE') or stm.startswith('INSERT')):
        for k in (', ', ' ('):
            stm = stm.replace(k,   '%s\n      ' % k)
    # log all lines with line number
    return [ '%02d: %s' % (i+1, l) for i,l in enumerate(stm.splitlines()) ]



class _SQLTimeWarning(object):

    def __init__(self, sql, args=()):
        self.__maxTime = 30.0
        try:
            self.__sql = getFormattedSQL(sql, args)
        except:
            self.__sql = []
            
    def __enter__(self):
        self.__start = time.time()
        
    def __exit__(self, exc_type, exc_value, traceback):
        diff = time.time() - self.__start
        if (diff < 0 or diff > self.__maxTime):
            log.warn('Database access took very long (%.2f seconds)' % (diff))
            for l in self.__sql:
                log.warn(l)
            
    
