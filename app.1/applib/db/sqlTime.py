# -*- coding: utf-8 -*-
#
# Copyright 2010 Grosvenor Technology
#

"""
:mod:`sqlTime` --- Time functions
=================================

This package contains functions, which make time handling and conversion
easier. 
 
"""

import log
import time
import calendar
import datetime

sqlTimeFormat = "%Y-%m-%d %H:%M:%S"

# NOTE: The following is to prevent an issue where strptime is
# not working when called inside a thread for the first time.
try:
    time.strptime("2010-09-14 17:30:00", sqlTimeFormat)
except Exception as e:
    log.warn('Error running time.strptime (%s)' % e)


class _LocalTZ(datetime.tzinfo):
    """ Current timezone"""
    
    def __init__(self, utc):
        super(_LocalTZ, self).__init__()
        self.__isdst = self.__utcIsInDST(utc)
        
    def __utcIsInDST(self, utc):
        if (time.daylight == 0):
            return False
        if (utc == None):
            return False
        # Alright, this is silly! To find out whether the time is in 
        # DST or not, we create a struct_time and calculate the UNIX
        # time, just to convert it to local time, which will then 
        # contain the DST information.
        t = time.struct_time( (utc.year, utc.month, utc.day, utc.hour, utc.minute, utc.second, -1, -1, -1) )
        u = calendar.timegm(t)
        t = time.localtime(u)
        return (t.tm_isdst == 1)

    def utcoffset(self, dt):
        """ Return offset to UTC, including DST."""
        if (self.__isdst):
            return datetime.timedelta(seconds=-time.altzone)
        return datetime.timedelta(seconds=-time.timezone)

    def tzname(self, dt):
        """ Return name of TZ"""
        if (self.__isdst):
            return time.tzname[1]
        return time.tzname[0]

    def dst(self, dt):
        """ Return DST offset."""
        if (self.__isdst):
            return datetime.timedelta(seconds=(time.timezone-time.altzone))
        return datetime.timedelta(0)



class _UTC(datetime.tzinfo):
    """UTC timezone"""

    def utcoffset(self, dt):
        """ Return offset to UTC, including DST."""        
        return datetime.timedelta(0)

    def tzname(self, dt):
        """ Return name of TZ"""        
        return 'UTC'

    def dst(self, dt):
        """ Return DST offset."""        
        return datetime.timedelta(0)


def sqlTime2MyTime(sqlTime, myTimeFormat):
    """Convert SQLite time string into user defined string.
    *sqlTime* is a string containing the time to convert in SQLite
    time format (e.g. like '2010-09-14 17:30:00'). *myTimeFormat* is 
    the time format compatible with `strptime() <http://docs.python.org/library/time.html#time.strptime>`_
    used to convert *sqlTime* to the new format.

    .. note::
        The time itself will not change, so no GMT to local
        time conversion is done.


    """
    t = time.strptime(sqlTime, sqlTimeFormat)
    return time.strftime(myTimeFormat, t)


def sqlTime2MyLocalTime(sqlTime, myTimeFormat):
    """Convert SQLite time string (as UTC) into user defined string (localtime).
    *sqlTime* is a string containing the UTC time to convert in SQLite
    time format (e.g. like '2010-09-14 17:30:00'). *myTimeFormat* is 
    the time format compatible with `strptime() <http://docs.python.org/library/time.html#time.strptime>`_
    used to convert *sqlTime* to the new format. The time will be converted 
    from UTC to local time.

    .. note::
        This function works like :func:`sqlTime2MyTime` but will read *sqlTime*
        as UTC and convert it to local time.

    """
    utc   = datetime.datetime.strptime(sqlTime, sqlTimeFormat).replace(tzinfo=_UTC())
    local = utc.astimezone(_LocalTZ(utc))
    return local.strftime(myTimeFormat)


def getSqlTimestampNow():
    """Get SQLite formated UTC time.
    
    The format is "%Y-%m-%d %H:%M:%S" (e.g. '2010-09-14 17:30:00'), which is also used as time
    format in SQLite.
    
    """
    return time.strftime(sqlTimeFormat, time.gmtime())


def localTime2SqlTime(localTime):
    """ Get SQLite time string (UTC) from given local time. *localTime* is
    a `datetime.datetime() <http://docs.python.org/library/datetime.html#datetime-objects>`_ object.
    
    .. versionadded:: 1.1
    """
    t = time.mktime(localTime.timetuple())
    return time.strftime(sqlTimeFormat, time.gmtime(t))



