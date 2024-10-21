# -*- coding: utf-8 -*-
#
# Copyright 2011 Grosvenor Technology
#
"""
:mod:`timeUtils` --- Helper functions for handling time and dates.
==================================================================

This module contains functions and classes to help handling time 
and dates. 

    .. versionadded:: 1.8
        
"""

import datetime
import time
import log

class FixedOffset(datetime.tzinfo):

    def __init__(self, offset):
        self.__offset = datetime.timedelta(minutes = offset)

    def utcoffset(self, dt):
        return self.__offset

    def tzname(self, dt):
        return None

    def dst(self, dt):
        return None


def getDatetimeFromISO8601(timeStr):
    """Convert *timeStr* ISO8601 date time string into 
    `datetime.datetime <http://docs.python.org/library/datetime.html#datetime-objects>`_ object.
    The returned `datetime.datetime <http://docs.python.org/library/datetime.html#datetime-objects>`_ object
    is timezone aware (e.g. `utcoffset <http://docs.python.org/2/library/datetime.html#datetime.datetime.utcoffset>`_ 
    is returning the offset to UTC).
    
    .. note::
      Although the returned `datetime.datetime <http://docs.python.org/library/datetime.html#datetime-objects>`_ object
      is timezone aware and therefore knows its UTC offset, operations like 
      `strftime <http://docs.python.org/2/library/datetime.html#datetime.datetime.strftime>`_, etc. still work on the
      local time. If only the UTC time is needed, :func:`getUTCDatetimeFromISO8601` can be used instead.

    """    
    dt = datetime.datetime.strptime(timeStr[:19], '%Y-%m-%dT%H:%M:%S')
    offsetStr = timeStr[20:]
    offsetLen = len(offsetStr)
    # Time formats:
    # 2013-01-15T07:00:00-06       HH
    # 2013-01-15T07:00:00-600     HMM
    # 2013-01-15T07:00:00-0000   HHMM
    # 2013-01-15T07:00:00-00:00 HH:MM
    if (offsetLen == 3):
        offsetMin = int(offsetStr[0]) * 60 + int(offsetStr[-2:])
    elif (offsetLen == 2):
        offsetMin = int(offsetStr) * 60
    elif (offsetLen == 4):
        offsetMin = int(offsetStr[:2]) * 60 + int(offsetStr[-2:])            
    elif (offsetLen == 5):
        offsetMin = int(offsetStr[:2]) * 60 + int(offsetStr[-2:])            
    else:
        offsetMin = 0
    if (timeStr[19] == '-'):
        offsetMin *= -1
    return dt.replace(tzinfo=FixedOffset(offsetMin))


def getUTCDatetimeFromISO8601(timeStr):
    """Convert *timeStr* ISO8601 date time string into UTC 
    `datetime.datetime <http://docs.python.org/library/datetime.html#datetime-objects>`_ object.
    Unlike :func:`getDatetimeFromISO8601`, this function returns a timezone unaware 
    `datetime.datetime <http://docs.python.org/library/datetime.html#datetime-objects>`_ object which holds the UTC time
    of the given ISO8601 date time string. 

    """
    d = getDatetimeFromISO8601(timeStr)
    return (d - d.utcoffset()).replace(tzinfo=None)



class TimeMeasure(object):
    """ Helper class to measure how long things take. The used time
    is logged as debug output.
    
    Example::
    
        with timeUtils.TimeMeasure('Updating employees'):
            self.__parseEmployees(jsonData)
        
    .. versionadded:: 2.1
    """
    
    def __init__(self, name):
        self.name = name
        
    def __enter__(self):
        self.start = time.time()
        
    def __exit__(self, exc_type, exc_value, traceback):
        end = time.time()
        log.dbg('%s needed %ss' % (self.name, end-self.start))



xmlTimeFormat = "%Y-%m-%dT%H:%M:%S%z"

def getXMLTimestampNow():
    """ Get the XML formated local time (plus UTC offset).
    
    The format is "%Y-%m-%dT%H:%M:%S%z", which is also used as time
    format in XML.
    
    .. versionadded:: 3.1
    
    """
    return time.strftime(xmlTimeFormat)


