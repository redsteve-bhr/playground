# -*- coding: utf-8 -*-
#
# Copyright 2010 Grosvenor Technology
#

"""
:mod:`restartManager` --- Restart and reboot manager
====================================================

This module contains functions and classes to restart the
application and reboot the terminal and ways to delay this.   

.. versionchanged:: 1.5
    PreventRestartLocks are not preventing restart and reboot
    requests comming from the same thread. 
    
    
"""

import threading
import os
import watchit
import time
import itg
import log

from applib.db import tblAppEvents

_preventers = []
_threadsToIgnore = []
_condition = threading.Condition()
_cleanups = []
_restartFromUIInProgress = False


def _addPreventer(obj):
    """ Add preventer object to list """
    with _condition:
        _preventers.append(obj)

def _delPreventer(obj):
    """ Remove preventer object from list and notify waiting threads """
    with _condition:
        _preventers.remove(obj)
        _condition.notifyAll()

def _addThreadToIgnore(threadID):
    """ Add threadID of thread to ignore when finding active preventers. """
    _threadsToIgnore.append(threadID)
    
def _activePreventers():
    """ Return True if there are any active preventers for threadID """
    for p in _preventers:
        if (p.isPreventing(_threadsToIgnore)):
            return True
    return False

def _getThreadID():
    return threading.currentThread().name

def setupSignals():
    """ Setup signal handler for HUB signal, which is used for clean shutdown """
    import signal
    signal.signal(signal.SIGHUP, _onSigHup) #@UndefinedVariable
    
def _onSigHup(signum, frame):
    """ Signal handler, start thread to restart application """
    _RestartAppThread().start()


class _RestartAppThread(threading.Thread):
    """ Thread to restart application, used when HUB signal is caught. """
    
    def run(self):
        restart(120, _('External application restart requested, restarting now...'))


class PreventRestartLock(object):
    """While some background threads may require an application restart
    or terminal reboot, it is often useful to allow a person in front
    of the terminal to finish their task first (and vice versa).
    
    The easiest way to prevent a restart/reboot is to use the PreventRestartLock()
    with the with-statement::


        with restartManager.PreventRestartLock():
            doStuff()

    It is also possible to use the member functions of PreventRestartLock()::
    
        rl = restartManager.PreventRestartLock()
        rl.acquire()
        try:
            doStuff()
        finally:
            rl.release()

    """

    def __enter__(self):
        self.acquire()
        
    def __exit__(self, exc_type, exc_value, traceback):
        self.release()
    
    def acquire(self):
        """Acquire lock and prevent an application restart or terminal reboot."""
        self._threadID = _getThreadID()
        _addPreventer(self)
        log.dbg('Added restart prevent lock (%d locks active)' % len(_preventers))        
        
    def release(self):
        """Release lock.""" 
        _delPreventer(self)
        log.dbg('Removed restart prevent lock (%d locks active)' % len(_preventers))

    def isPreventing(self, threadsToIgnore):
        # Object is preventing restarts if not in threadsToIgnore list.
        return (self._threadID not in threadsToIgnore)
    

def registerCleanup(func, args=None):
    """ Register callback *func* which will be called before a restart. If *args* is
    not **None** it must be a tuple or list and will be used as parameters for the callback.
    Example::
    
        def onRestart():
            pass
            
        # ...
        
        restartManager.registerCleanup(onRestart)
    
    Example with callback parameter::

        def onRestart(param1, param2):
            pass
            
        # ...
        
        restartManager.registerCleanup(onRestart, (param1, param2))
    
    .. note:: If the callback is a class method, registering it may prevent the class
              from being freed. A weak reference should be used in these cases.
              
    .. versionadded:: 1.2
    """
    _cleanups.append( (func, args) )

def _runCleanupsAndExit(cmd):
    """ Execute cleanup functions and execute cmd via os.system """
    for (func, args) in _cleanups:
        if (callable(func)):
            try:
                if (args != None):
                    func(*args)
                else:
                    func()
            except Exception as e:
                log.err('Error calling cleanup %s: %s' % (func, e))
    os.system(cmd)
    _die(10)

def _die(timeout):
    """ Use watchdog to reboot in timeout seconds. This function will never return. """
    try:
        w = watchit.WatchIT()
        w.register(timeout)
    except Exception as e:
        log.err('Failed to register with watchdog: %s' % (e,))
    while True:
        time.sleep(10)

def _showWaitboxAndDie(msg, timeout):
    """ Show waitbox with msg and make sure to die/reboot after timeout.
    
    This function is supposed to run in the UI thread. The dying part is
    executed as a safety measure if running the cleanups and restarting/rebooting
    normally is not done within the timeout.  
    
    """
    itg.waitbox(msg, _die, (timeout,))

def _restartOrReboot(threadID, timeout, msg, cmd):
    """ Wait max timeout seconds or until no one 
    is preventing restart/reboot and execute cmd while showing msg. 
    """ 
    maxTimeout = timeout
    with _condition:
        _addThreadToIgnore(threadID)
        endTime = time.time() + timeout
        while (_activePreventers() and timeout > 0):        
            _condition.wait(timeout)
            timeout = endTime - time.time()
            if (timeout > maxTimeout):
                timeout = 5
        if (not _restartFromUIInProgress):
            itg.runLater(_showWaitboxAndDie, (msg, 20,))
        _runCleanupsAndExit(cmd)

def restart(timeout=300, msg=None):
    """ Restart application as soon as possible. The application will restart
    after *timeout* seconds, regardless of any active :class:`PreventRestartLock` objects.
    The message *msg* will appear on the screen 5 seconds before the restart. If
    *msg* is not set, a generic restart message will be shown.
    
    .. note:: This function must not be used by the main UI thread (so only from
              background threads), use :func:`restartFromUI` instead.
    
    """ 
    tblAppEvents.addSystemEvent('app.restart.request')    
    if (msg == None):
        msg = _('Terminal application is restarting...')
    threadID = _getThreadID()
    _restartOrReboot(threadID, timeout, msg, 'sleep 5; start-stop-daemon -K -p /var/run/app.pid')


def reboot(timeout=300, msg=None):
    """ Reboot terminal as soon as possible. The terminal will reboot
    after *timeout* seconds, regardless of any active :class:`PreventRestartLock` 
    objects.     
    The message *msg* will appear on the screen 5 seconds before the reboot. If
    *msg* is not set, a generic restart message will be shown.
    
    .. note:: This function must not be used by the main UI thread (so only from
              background threads), use :func:`restartFromUI` instead.
    
    """ 
    tblAppEvents.addSystemEvent('app.reboot.request')    
    if (msg == None):
        msg = _('Terminal is rebooting...')
    threadID = _getThreadID()        
    _restartOrReboot(threadID, timeout, msg, 'sleep 5; reboot')        

def _restartOrRebootFromUI(threadID, timeout, cmd):
    """ Wait max timeout seconds or until no one 
    is preventing restart/reboot and execute cmd 
    """ 
    maxTimeout = timeout
    with _condition:
        _addThreadToIgnore(threadID)
        endTime = time.time() + timeout
        while (_activePreventers() and timeout > 0):
            _condition.wait(timeout)
            timeout = endTime - time.time()
            if (timeout > maxTimeout):
                timeout = 5
        try:
            w = watchit.WatchIT()
            w.register(timeout)
        except Exception as e:
            log.err('Failed to register with watchdog: %s' % (e,))
        _runCleanupsAndExit(cmd)
        
def restartFromUI(timeout=300, msg=None):
    """ Restart application as soon as possible. The application will restart
    after *timeout* seconds, regardless of any active :class:`PreventRestartLock` objects.
    The message *msg* will appear on the screen 5 seconds before the restart. If
    *msg* is not set, a generic restart message will be shown.
    
    .. note:: This function must not be used by a background thread, use func:`restart`
              instead.
    """ 
    
    tblAppEvents.addSystemEvent('app.restart.ui')
    global _restartFromUIInProgress
    _restartFromUIInProgress = True
    if (msg == None):
        msg = _('Terminal application is restarting...')
    threadID = _getThreadID()
    cmd = 'sleep 5; start-stop-daemon -K -p /var/run/app.pid'
    itg.waitbox(msg, _restartOrRebootFromUI, (threadID, timeout, cmd))
    
def rebootFromUI(timeout=300, msg=None):
    """ Reboot terminal as soon as possible. The terminal will reboot
    after *timeout* seconds, regardless of any active :class:`PreventRestartLock` objects.
    The message *msg* will appear on the screen 5 seconds before the reboot. If
    *msg* is not set, a generic restart message will be shown.
    
    .. note:: This function must not be used by a background thread, use func:`reboot`
              instead.

    """    
    tblAppEvents.addSystemEvent('system.reboot.ui')
    global _restartFromUIInProgress
    _restartFromUIInProgress = True
    if (msg == None):
        msg = _('Terminal is rebooting...')
    threadID = _getThreadID()        
    cmd = 'sleep 5; reboot'
    itg.waitbox(msg, _restartOrRebootFromUI, (threadID, timeout, cmd))
    