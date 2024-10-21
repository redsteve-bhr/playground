# -*- coding: utf-8 -*-
#
# Copyright 2011 Grosvenor Technology
#

"""
:mod:`periodicScheduler` --- Scheduling periodic tasks 
======================================================

.. versionadded:: 2.2

"""

import threading
import time
import datetime
import log
from applib.utils import healthMonitor


def _humanReadableTimeSpan(seconds):
    (minutes, seconds) = divmod(seconds, 60)
    (hours, minutes) = divmod(minutes, 60)
    if (hours > 1 and minutes == 0 and seconds == 0):
        return _('%d hours') % hours
    minutes += hours*60
    if (minutes > 1 and seconds == 0):
        return _('%d minutes') % minutes
    seconds += minutes*60
    return _('%d seconds') % seconds 


class _PeriodicTask(object):
    
    def __init__(self, name, func, period, retryTime, startIn, useHealthMonitor):
        self.__name = name
        self.__func = func
        self.__period = period
        self.__retryTime = retryTime
        self.__lastTime = None
        self.__nextTime = time.time() + startIn
        self.__lastError = None
        self.__scheduledNext = False
        self.__inProcess = False
        if (useHealthMonitor):
            healthMonitor.getAppHealthMonitor().add(self)

    def getName(self):
        return self.__name

    def getTimeToNextRun(self):
        """ Return number of seconds till next execution. """
        if (self.__scheduledNext):
            return -1;
        return (self.__nextTime - time.time())
    
    def scheduleNext(self):
        """ Next call to getTimeToNextRun will return -1 until task is executed. """
        self.__scheduledNext = True

    def run(self):
        self.__inProcess = True
        self.__lastTime = time.time()
        self.__scheduledNext = False
        log.dbg('Executing period task "%s"' % self.__name)
        try:
            self.__func()
            self.__lastError = None
            # add period time, make sure time is in future
            while (self.__nextTime < time.time()):
                self.__nextTime += self.__period
            log.dbg('Periodic task "%s" finished, running again in %ss' % (self.__name, self.__period))
        except Exception as e:
            self.__lastError = '%s' % (e,)
            # add retry time, make sure time is in future            
            while (self.__nextTime < time.time()):            
                self.__nextTime += self.__retryTime
            log.err('Periodic task "%s" failed, running again in %ss: %s' % (self.__name, self.__retryTime, e))
        self.__inProcess = False
            
    def getWarnings(self):
        if not self.__lastError:
            return []
        return [{ 'msg': '%s failed' % self.__name }]
        
    def getHealth(self):
        items = [(_('Last run'),  time.strftime('%x %X', time.localtime(self.__lastTime)) if self.__lastTime != None else ''),
                 (_('Next run'),  time.strftime('%x %X', time.localtime(self.__nextTime)) if not self.__inProcess else 'in progress'),
                 (_('Run every'), _humanReadableTimeSpan(self.__period))
                 ]
        if (self.__lastError):
            items.append((_('Error'), self.__lastError))
        return (self.__name, (self.__lastError == None), items)


_scheduler = None

def getScheduler():
    global _scheduler
    if (_scheduler == None):
        _scheduler = PeriodicScheduler()
    return _scheduler

def add(name, func, period, retryTime, startIn=0, useHealthMonitor=False):
    """ Add new periodic task to scheduler. *name* is a **string**
    used for logging and health monitoring. *func* is the function 
    that gets called periodically. *period* is the number of seconds between 
    successful calls and *retryTime* is the number of seconds to call *func*
    again after it returned with an exception. *startIn* specifies in how many
    seconds the task should be executed after adding.
    If *useHealthMonitor* is **True**, a health object is created and added
    to the application health monitor to show:
    
     - last run
     - next run
     - period time
     - last error
    
    Example::
    
        def myPeriodicFunc():
            log.info('Hello world')
        
        # [...]
        
        periodicScheduler.add('MyTestFunc', myPeriodicFunc, 10, 10)

    All tasks are executed within the same thread, which means that one task can 
    delay another. However, the *periodScheduler* module is not meant to be used  
    for high precision or guaranteed period times between calls. Instead it should
    be used for background tasks, which need to be executed periodically, but without
    the overhead of creating a thread for every task. A common scenario could look like
    this::
    
        # schedule department import every 4 hours (5 minutes retry time)
        periodicScheduler.add('Department import', importDepartments, 4*60*60, 300)
        
        # schedule user synchronisation every 2 minutes (5 minutes retry time)
        periodicScheduler.add('User sync', syncUsers, 120, 300)
        
        # schedule heartbeat (every 60s)
        periodicScheduler.add('Heartbeat', sendHeartbeat, 60, 60)
    
    The example above configures three tasks. All tasks run within the same thread, which
    means that the heartbeat could miss its 60s interval for example, if the department 
    import takes very long.
    
    A new *taskID* is returned by :func:`add`, which can be used with :func:`scheduleNext`::
    
        taskID = periodicScheduler.add('Task', taskFunc,  120, 300)
        
        # [...]
        
        periodicScheduler.scheduleNext(taskID)
        
    """
    return getScheduler().add(name, func, period, retryTime, startIn, useHealthMonitor)


def addDaily(name, func, hour, useHealthMonitor=False):
    """ Add new periodic task (like :func:`add`) that is executed
    once per day within the hour *hour*.
    
    Example::
    
        periodicScheduler.addDailyTask('Nightly check', nightCheck, 4)
    
    The configured nightly task runs every 24h, and is executed between 4 and 5 o'clock AM
    depending on the current time.
    """
    return getScheduler().addDaily(name, func, hour, useHealthMonitor)


def scheduleNext(taskID):
    """ Schedule task specified by *taskID* to run now/next. The task will be executed
    by the periodic scheduler thread and not the current one. Any task executed 
    at the moment has to finish before the next task can be executed."""
    getScheduler().scheduleNext(taskID)

def start():
    s = getScheduler()
    if (not s.isRunning()):
        s.start()

def stop():
    getScheduler.stop()


class PeriodicScheduler(threading.Thread):
    
    def __init__(self):
        super(PeriodicScheduler, self).__init__()
        self.__cond      = threading.Condition()
        self.__running   = False
        self.__tasks     = {}
        self.__nextTaskID = 1
        
    def isRunning(self):
        return self.__running
    
    def start(self):
        self.__running = True
        super(PeriodicScheduler, self).start()

    def add(self, name, func, period, retryTime, startIn=0, useHealthMonitor=False):
        log.dbg('Adding periodic task "%s" to scheduler' % (name,))
        with self.__cond:
            taskID = self.__nextTaskID
            self.__tasks[taskID] = _PeriodicTask(name, func, period, retryTime, startIn, useHealthMonitor)
            self.__nextTaskID += 1
            self.__cond.notifyAll()
        if (not self.__running):
            self.start()
        return taskID
    
    def addDaily(self, name, func, hour, useHealthMonitor=False):
        h = hour - datetime.datetime.now().hour
        if (h<0):
            h += 24
        self.add(name, func, 24*60*60, 24*60*60, h*60*60)

    def stop(self):
        with self.__cond:
            self.__running = False
            self.__cond.notifyAll()

    def scheduleNext(self, taskID):
        with self.__cond:
            if (taskID in self.__tasks):
                task = self.__tasks[taskID]
                task.scheduleNext()
                self.__cond.notifyAll()                
        
    def __waitForNextTask(self):
        with self.__cond:
            if (self.__tasks):
                # calculate time till next task is due
                task = min(self.__tasks.itervalues(), key=lambda t: t.getTimeToNextRun())
                wait = task.getTimeToNextRun()
                if (wait <= 0):
                    return task
                log.dbg('Waiting %ds for task "%s"' % (wait, task.getName()))
            else:
                wait = None
            self.__cond.wait(wait)
        return None
            
    def run(self):
        log.dbg('Period scheduler started')        
        while (self.__running):
            # get next task to run
            task = self.__waitForNextTask()
            if (task):
                task.run()
        log.dbg('Period scheduler ended')

