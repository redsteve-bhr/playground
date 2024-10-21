# -*- coding: utf-8 -*-
#
# Copyright 2023 Grosvenor Technology
#
"""Miscellaneous Utilities

Small functions that do not have a suitable place elsewhere.
"""
import itg
import log
import calendar
import time
import cfg
import datetime
from applib.db.tblSettings import getAppSetting

def hasCameraSupport():
    return hasattr(itg, 'WebcamView')

def getOptionForLanguage(tag, language, default=None):
    """ Extract text content of the tag for given language. """
    if (tag == None):
        return default
    if (len(tag) == 0):
        return tag.text or ''
    if language is not None:
        for text in tag:
            if (text.tag != 'text'):
                continue
            if (text.get('language').lower() == language):
                return text.text
            elif (text.get('en') == language):
                default = text.text
    return default

def getElementText(element, tagPath, default='', warn=False, language=None):
    """Returns the text of the XML element found at tagPath under the supplied 
    element. Returns the default if no element can be found.

    For example, given an 'itemElement' containing this XML...

        <item>
            <label>
                <text language='en'>English Label</text>
                <text language='fr'>Label en Francais</text>
            </label>
        <item>

    ...the text in French can be retrieved with:

        labelText = miscUtils.getElementText(itemElement, 'label', language='fr')

    """
    result = element.find(tagPath)
    if result is not None:
        return getOptionForLanguage(result, language, default)
    else:
        if warn:
            log.warn('Failed to find "%s" under element "%s"; using default of "%s"' % (tagPath, element.tag, default))
        return default

def daynameExtension(forDay):
    if forDay in [1, 21, 31]:
        return 'st'
    elif forDay in [2, 22]:
        return 'nd'
    elif forDay in [3, 23]:
        return 'rd'
    else:
        return 'th'

def userFriendlyDate(dateTime, includeTime=True):
    if includeTime:
        formatStr = '%d{ext} %b %Y, %H:%M'
    else:
        formatStr = '%d{ext} %b %Y'
    dateStr = dateTime.strftime(formatStr).format(ext=daynameExtension(dateTime.day))
    if dateStr.startswith('0'):
        dateStr = dateStr[1:]
    return dateStr

def utcIsInDST(utc):
    """Returns True if the timezone uses DST and DST is currently active."""
    if (time.daylight == 0):
        return False
    if (utc == None):
        return False
    t = time.struct_time( (utc.year, utc.month, utc.day, utc.hour, utc.minute, utc.second, -1, -1, -1) )
    u = calendar.timegm(t)
    t = time.localtime(u)
    return (t.tm_isdst == 1)
    
def timestampWithUTCOffset(dateTime):
    """Returns the specified date-time (which is assumed to be Local time) as a string,
    with the UTC offset appended.
    """

    formatStr = "%Y-%m-%dT%H:%M:%S"
    if utcIsInDST(dateTime):
        offsetSeconds = -time.altzone
    else:
        offsetSeconds = -time.timezone
        
    if offsetSeconds >= 0:
        sep = '+'
    else:
        sep = '-'

    m, _ = divmod(offsetSeconds, 60)
    h, m = divmod(m, 60)
    offsetStr = ('{:02d}{:02d}'.format(abs(h), abs(m)))
    try:
        return dateTime.strftime(formatStr) + sep + offsetStr
    except Exception as e:
        log.warn('Time Stamp: could not calculate offset: %s' % e)
        return dateTime.strftime(formatStr)

def getFirstDayOfWeek():
    """Returns the first day of the week (in numeric form) for the locale, where
    0 is Monday and 6 is Sunday. A value of -1 will use the terminal's Region and
    Language setting to determine the correct value. An invalid value will be
    treated as -1.
    """
    try:
        firstDay = int(getAppSetting('app_first_day_of_week'))
        if firstDay < -1 or firstDay > 6:
            firstDay = -1
    except:
        firstDay = -1

    if firstDay == -1:
        # Use default based on locale
        area = cfg.get('it_locale')
        if ('_US' in area):
            firstDay = 6  # Sunday
        else:
            firstDay = 0  # Monday

    return firstDay

def getDateFormat():
    """Returns the date format for the locale, usually set via the
    `app_date_format` application settings, or read from the terminal's
    locale.

    The returned format will be as required by the CalendarView (which
    is the intended use for this format).
    """
    import re

    area = cfg.get('it_locale')
    if ('_US' in area):
        localeFormat = '%m/%d/%Y'
    else:
        localeFormat = '%d/%m/%Y'
    defaultFormat = '%d/%m/%Y'
    appFormat = getAppSetting('app_date_format')

    # Use appFormat, fall back on the locale format if appFormat is not set
    dateFormat = appFormat
    if dateFormat is None or dateFormat == '':
        dateFormat = localeFormat
    else:
        # Check for invalid characters
        for c in dateFormat:
            if not c in '-%/dmY':
                log.warn('Invalid date format: "%s"' % dateFormat)
                # Fall back to default format
                dateFormat = localeFormat
                break

    # If appFormat is not available or is invalid, and locale format is also
    # not available, fall back on the old default
    if dateFormat is None or dateFormat == '':
        dateFormat = defaultFormat

    # Always use upper-case 'Y' (4-digit year)
    dateFormat = re.sub('y', 'Y', dateFormat)

    # Check for invalid format
    testDateTime = datetime.datetime.now()
    try:
        testDateTimeStr = testDateTime.strftime(dateFormat)
        datetime.datetime.strptime(testDateTimeStr, dateFormat)
    except Exception as e:
        log.warn('Invalid date format: "%s": %s' % (dateFormat, str(e)))
        dateFormat = defaultFormat

    return dateFormat