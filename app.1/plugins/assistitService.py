# -*- coding: utf-8 -*-
#
# Copyright 2014 Grosvenor Technology
#
import log
import os
import threading
import Queue
import dbus.service  # @UnresolvedImport

from engine import fileHandler
from applib.utils import restartManager, healthMonitor, nls

_srv = None
_thread = None
_commands = {}


def registerCommand(name, cb):
    """ Register new AssistIT command. The callback *cb* must accept 
       one parameter, which is a tuple containing all parameters the 
       user entered in AssistIT."""
    _commands[name] = cb 
    
def _cmdListCommands(params):
    """ AssistIT command to list all available commands. """
    if (params):
        return 'Syntax error, no parameters supported in list command'
    return 'Supported commands: \n' + '\n'.join( sorted(_commands.keys()))

def _getThread():
    """ Return thread for executing background jobs. """
    global _thread
    if (_thread == None):
        _thread = _ApplicationDbusServiceThread()
        _thread.start()
    return _thread


class _ApplicationDbusServiceThread(threading.Thread):
    """ Thread for executing background jobs. """
    
    def __init__(self):
        super(_ApplicationDbusServiceThread, self).__init__()
        self.__queue = Queue.Queue()
        self.__running = True
        
    def addJob(self, job):
        try:
            self.__queue.put(job, block=False)
        except Exception as e:
            log.err('AssistIT DBus queue full? (%s)' % e)
            
    def stop(self):
        self.__running = False
        self.addJob(None)
        if (self.name != threading.currentThread().name):
            self.join(timeout=1)
    
    def run(self):
        while self.__running:
            try:
                job = self.__queue.get(block=True)
                if (hasattr(job, 'execute')):
                    job.execute()
                self.__queue.task_done()
            except Exception as e:
                log.err('Failed to execute AssistIT DBUS job: %s' % e)
 

class _FileExportJob(object):
    """ Job for file export. """
    
    def __init__(self, filename, filelocation, reply_handler, error_handler):
        self.__filename = filename
        self.__filelocation = filelocation
        self.__reply_handler = reply_handler
        self.__error_handler = error_handler

    def execute(self):
        log.dbg('Got AssistIT export request for %s (%s)' % (self.__filename, self.__filelocation))
        try:
            handler = fileHandler.getFileHandlerForFile(self.__filename)
            if (handler == None):
                self.__reply_handler( 1, 'no file handler')
            elif (hasattr(handler, 'fileExport')):
                with restartManager.PreventRestartLock():
                    data = handler.fileExport(self.__filename)
                    if (data):
                        with open(self.__filelocation, 'w') as f:
                            f.write(data)
                        self.__reply_handler(0, 'File successfully exported')
                    else:
                        self.__reply_handler(2, 'exported file is empty')
            else:
                self.__reply_handler(3, 'file handler does not support export')
        except Exception as e:
            log.err('Error exporting to AssistIT %s: %s' % (self.__filename, e))
            self.__reply_handler(4, '%s' % e)
    

class _FileImportJob(object):
    """ Job for file import. """
    
    def __init__(self, filename, filelocation, reply_handler, error_handler):
        self.__filename = filename
        self.__filelocation = filelocation
        self.__reply_handler = reply_handler
        self.__error_handler = error_handler

    def execute(self):
        log.dbg('Got AssistIT import request for %s (%s)' % (self.__filename, self.__filelocation))
        try:
            self.__filename = os.path.basename(self.__filename)
            handler = fileHandler.getFileHandlerForFile(self.__filename)
            if (handler == None):
                self.__reply_handler( 1, 'no file handler')
            elif (hasattr(handler, 'fileImport')):
                with restartManager.PreventRestartLock():
                    rrm = fileHandler.RestartRequestManager()
                    data = open(self.__filelocation, 'r').read()
                    handler.fileImport(self.__filename, data, rrm)
                    if (rrm.isRebootRequested()):
                        self.__reply_handler(0, 'File successfully imported, application is rebooting')
                        restartManager.reboot(300, _('Rebooting terminal because system configuration has changed.'))
                    elif (rrm.isRestartRequested()):
                        self.__reply_handler(0, 'File successfully imported, application is restarting')
                        restartManager.restart(300, _('Restarting application because settings changed'))
                    else:
                        self.__reply_handler(0, 'File successfully imported')
            else:
                self.__reply_handler(3, 'file handler does not support import')
        except Exception as e:
            log.err('Error importing from AssistIT %s: %s' % (self.__filename, e))
            self.__reply_handler(4, '%s' % e)


class _CommandJob(object):
    """ Job for executing command. """
    
    def __init__(self, cb, cmdName, cmdParams, reply_handler, error_handler):
        self.__cb = cb
        self.__cmdName = cmdName
        self.__cmdParams = cmdParams
        self.__reply_handler = reply_handler
        self.__error_handler = error_handler

    def execute(self):
        log.dbg('Executing AssistIT command %s' % self.__cmdName)
        try:
            result = self.__cb(self.__cmdParams)
            self.__reply_handler(result)
        except Exception as e:
            log.err('Error executing AssistIT command %s: %s' % (self.__cmdName, e))
            self.__reply_handler('Error executing AssistIT command %s: %s' % (self.__cmdName, e))


class _ApplicationDbusService(dbus.service.Object):
    """ DBus service for file import, export, health and generic commands. """
    
    @dbus.service.method('com.gtl.it.application', in_signature='ss', out_signature='is', async_callbacks=('reply_handler', 'error_handler'))
    def fileExport(self, filename, filelocation, reply_handler, error_handler):
        _getThread().addJob(_FileExportJob(filename, filelocation, reply_handler, error_handler))
        
    @dbus.service.method('com.gtl.it.application', in_signature='', out_signature='as')
    def fileExportList(self):
        l = []
        for handler in fileHandler.getAll():
            if (hasattr(handler, 'fileExport') and hasattr(handler, 'getExportName')):
                l.append(handler.getExportName())
        return l
        
    @dbus.service.method('com.gtl.it.application', in_signature='ss', out_signature='is', async_callbacks=('reply_handler', 'error_handler'))
    def fileImport(self, filename, filelocation, reply_handler, error_handler):
        _getThread().addJob(_FileImportJob(filename, filelocation, reply_handler, error_handler))

    @dbus.service.method('com.gtl.it.application', in_signature='', out_signature='as')
    def fileImportList(self):
        l = []
        for handler in fileHandler.getAll():
            if (hasattr(handler, 'fileImport') and hasattr(handler, 'getExportName')):
                l.append(handler.getExportName())
        return l
    
    @dbus.service.method('com.gtl.it.application', in_signature='s', out_signature='b')
    def fileImportTest(self, filename):
        filename = os.path.basename(filename)
        handler  = fileHandler.getFileHandlerForFile(filename)
        if (handler != None and hasattr(handler, 'fileImport')):
            return True
        return False
    
    @dbus.service.method('com.gtl.it.application', in_signature='', out_signature='s')
    def getHealth(self):
        with nls.Language('en'):
            text = []
            for (name, healthy, details) in healthMonitor.getAppHealthMonitor().getHealthStatus():
                text.append('%s (%s)' % (name, ('Good' if healthy else 'Bad') ))
                text.append('=' * len(text[-1]))
                if (details):
                    for (name, value) in details:
                        text.append('%-20s : %s' % (name, value))
                text.append('')
            return '\n'.join(text)
    
    @dbus.service.method('com.gtl.it.application', in_signature='sas', out_signature='s', async_callbacks=('reply_handler', 'error_handler'))
    def execute(self, cmdName, cmdParams, reply_handler, error_handler):
        if (cmdName in _commands):
            j = _CommandJob(_commands[cmdName], cmdName, cmdParams, reply_handler, error_handler)
            _getThread().addJob(j)
        else:
            reply_handler('No such command "%s"!' % (cmdName,))
        


def loadPlugin():
    registerCommand('list', _cmdListCommands)

def startPlugin():
    if (os.path.exists('/etc/dbus-1/system.d/application-service.conf')):
        global _srv
        systemBus = dbus.SystemBus()
        name = dbus.service.BusName("com.gtl.it.application", systemBus)
        _srv = _ApplicationDbusService(systemBus, '/com/gtl/it/application', name)
 
def stopPlugin():
    global _srv, _thread
    _srv = None
    if (_thread != None):
        _thread.stop()
        _thread = None

