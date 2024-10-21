# -*- coding: utf-8 -*-
#
# Copyright 2014 Grosvenor Technology
#



"""
:mod:`relayManager` --- Relay Manager module
============================================

.. versionadded:: 2.4

The relay manager helps with sharing access to IO board relays across
different software components. For example, an application may have
a scheduler for driving relays on a time table basis but also driven 
by the user via the UI.

The main function :func:`setRelayOn` of this module allows to turn on a relay
for a given time. After that time, the relay will be turned off again, unless
there was another call to that function with a longer duration time.

Example::

    # Activate first relay on first IO board for 5 seconds.
    relayManager.setRelayOn(0, 0, 5)
    # or
    relayManager.setRelayOn( ioboard.getIOBoard(), 0, 5)
 
:func:`setRelayAlwaysOn` can be used to turn the relay on and keep it on until
:func:`clearRelayAlwaysOn` is called. The relay stays on regardless of calls to
:func:`setRelayOn`. Once :func:`clearRelayAlwaysOn` is called, the relay is turned
off, unless there is a duration from :func:`setRelayOn` pending, in which case the 
relay is turned off when that timer expired.

.. autofunction:: applib.utils.relayManager.setRelayOn

.. autofunction:: applib.utils.relayManager.setRelayAlwaysOn

.. autofunction:: applib.utils.relayManager.clearRelayAlwaysOn

"""
import ioboard
import threading
import gobject  # @UnresolvedImport


class IOBoardInvalidException(Exception):
    pass

class IOBoardRelayInvalidException(Exception):
    pass


def setRelayOn(ioBoard, relay, duration):
    """ Set relay on. The relay is turned off again
        after *duration* number of seconds, unless it is
        set to be always on via :func:`setRelayAlwaysOn` or
        if there was another call to :func:`setRelayOn`
        with a longer duration.
        
        *ioBoard* is either an :class:`ioboard.IOBoard` object 
        or an integer which is used as index with 
        :func:`ioboard.getIOBoards()` (starting at zero).
        *relay* is also an integer, starting at zero for the first
        relay.
        An **IOBoardInvalidException** is thrown, if the IO board 
        does not exist or is invalid. **IOBoardRelayInvalidException** is 
        thrown if *relay* is invalid.
    """
    if (duration < 0):
        raise Exception('Duration must be positive')
    with _sharedRelayLock:
        (relayState, ioBoard, relay) = _getSharedRelayStateAndIoBoard(ioBoard, relay)
        ioBoard.setRelay(relay, True)
        relayState.restartTimer(duration)


def setRelayAlwaysOn(ioBoard, relay):
    """ Set relay on and keep it on until :func:`clearRelayAlwaysOn`
        is called. Calls to :func:`setRelayOn` will also not
        turn the relay off at the end of the duration. 
        
        *ioBoard* and *relay* specify the IO board and relay, see
        :func:`setRelayOn` for details.
    """ 
    with _sharedRelayLock:
        (relayState, ioBoard, relay) = _getSharedRelayStateAndIoBoard(ioBoard, relay)
        relayState.setAlwaysOn()
        ioBoard.setRelay(relay, True)

def clearRelayAlwaysOn(ioBoard, relay):
    """ Clear "relay always" on flag. The relay is turned off, unless
        a duration set by :func:`setRelayOn` is still running, in which
        case the relay is turned off after the duration.
        
        *ioBoard* and *relay* specify the IO board and relay, see
        :func:`setRelayOn` for details.
    """ 
    with _sharedRelayLock:
        (relayState, ioBoard, relay) = _getSharedRelayStateAndIoBoard(ioBoard, relay)
        relayState.clearAlwaysOn()
        if (not relayState.isTimerPending()):
            ioBoard.setRelay(relay, False)


_sharedRelayLock   = threading.Lock()
_sharedRelayStates = {}

def _getSharedRelayStateAndIoBoard(ioBoard, relay):
    # get ioBoard object
    if (not hasattr(ioBoard, 'getInfo')):
        try:
            ioBoard = ioboard.getIOBoards()[int(ioBoard)]
        except IndexError:
            raise IOBoardInvalidException('Invalid IO board')
        except ValueError:
            raise IOBoardInvalidException('Invalid IO board index')
    # get partno
    (partno, numRelays, _numInputs) = ioBoard.getInfo()
    # check relay
    try:
        relay = int(relay)
        if (relay<0 or relay>=numRelays):
            raise IOBoardRelayInvalidException('Invalid relay')
    except ValueError:
        raise IOBoardRelayInvalidException('Invalid relay')
    key = '%s__%s' % (partno, relay)
    if (key not in _sharedRelayStates):
        _sharedRelayStates[key] = _SharedRelayState(partno, relay)
    return (_sharedRelayStates[key], ioBoard, relay)


class _SharedRelayState(object):
    
    def __init__(self, partno, relay):
        self.__partno = partno
        self.__relay = relay
        self.__alwaysOn = False
        self.__timerID = None
    
    def setAlwaysOn(self):
        self.__alwaysOn = True
    
    def clearAlwaysOn(self):
        self.__alwaysOn = False

    def isAlwaysOn(self):
        return self.__alwaysOn

    def restartTimer(self, duration):
        if (self.__timerID != None):
            gobject.source_remove(self.__timerID)
        self.__timerID = gobject.timeout_add(int(duration*1000), self.__onTimer)
    
    def __onTimer(self):
        with _sharedRelayLock:
            self.__timerID = None
            if (not self.isAlwaysOn()):
                for ioBoard in ioboard.getIOBoards():
                    (partno, _numRelays, _numInputs) = ioBoard.getInfo()
                    if (partno == self.__partno):
                        ioBoard.setRelay(self.__relay, False)
                        break
            return False
    
    def isTimerPending(self):
        return (self.__timerID != None)








