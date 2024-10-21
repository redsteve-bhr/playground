# -*- coding: utf-8 -*-
#
#
import log

from applib.db.tblSettings import getAppSetting, SettingsSection, NumberSetting, BoolSetting, TextSetting


def isUSBBarcodeScan(reader, decoder):
    """Return True if the card read was done by barcode scanner rather than a
    standard swipe."""
    return (reader == 1) and (decoder == 1)

def decodeBadgeData(data):
    if ('-' in data):
        (siteCode, badgeCode) = data.split('-', 1)
    else:
        (siteCode, badgeCode) = (None, data)
    badgeLength = getAppSetting('badge_length')
    stripZeros  = getAppSetting('strip_zeros_from_badge')
    stripBadge  = getAppSetting('strip_badge')
    padBadge    = getAppSetting('pad_badge')
    numericOnly = getAppSetting('numeric_only_badge')
    if (badgeLength > 0 and len(badgeCode) != badgeLength):
        raise Exception(_('Invalid card!'))
    if (':' in stripBadge):
        try:
            (a,b) = stripBadge.split(':', 1)
            a = None if a=='' else int(a)
            b = None if b=='' else int(b)
            newBadgeCode = badgeCode[a:b]             
        except Exception as e:
            log.err('Error while stripping badge: %s' % e)
            raise Exception(_('Decode error!'))
        badgeCode = newBadgeCode
    if (stripZeros and badgeCode != '0'):
        badgeCode = badgeCode.lstrip('0')
    if (padBadge > 0):
        badgeCode = badgeCode.zfill(padBadge)
        if (len(badgeCode) != padBadge):
            raise Exception(_('Invalid card!'))
    if (not badgeCode):
        raise Exception(_('Decode error!'))
    if numericOnly and not isBadgeCodeNumeric(badgeCode):
        raise Exception(_('Non-numeric badge code!'))    
    if (getAppSetting('site_code_check') and getAppSetting('site_code').strip() == ''):
        return (None, '%s-%s' % (siteCode, badgeCode))
    return (siteCode, badgeCode)

def isBadgeCodeNumeric(badgeCode):
    for char in badgeCode:
        if not char.isnumeric():
            return False
    return True

def isSiteCodeValid(siteCode):
    if (siteCode == None):
        return True
    if (not getAppSetting('site_code_check')):
        return True
    return (str(siteCode) in getAppSetting('site_code').replace(' ', '').split(','))

def getSettings():
    sectionName = 'Badge Code'
    sectionComment = ('These are the settings for the Badge Code. ')                   
    badgeSection = SettingsSection(sectionName, sectionComment)
    BoolSetting(badgeSection,
            name     = 'site_code_check', 
            label    = 'Check site code', 
            data     = 'False',
            comment  = ('Enable/disable site code check for cards and badges that support it.'))
    TextSetting(badgeSection,
            name     = 'site_code',
            label    = 'Site code', 
            data     = '0', 
            comment  = ('Comma separated list of site codes to check (*site_code_check* needs to be enabled). '
                        'If *site_code* is empty and *site_code_check* is *True*, then the employee\'s badge code '
                        'must contain the site code (as in "SITECODE-BADGECODE").'))
    NumberSetting(badgeSection,
            name     = 'pad_keypad',
            label    = 'Pad keypad input', 
            data     = '0',
            comment  = ('If non zero, pad the key pad input to the specified length.'))
    NumberSetting(badgeSection,
            name     = 'badge_length',
            label    = 'Badge length', 
            data     = '0',
            comment  = ('If non zero, the badge code must be the same as the specified length.'))
    NumberSetting(badgeSection,
            name     = 'pad_badge',
            label    = 'Pad badge data', 
            data     = '0',
            comment  = ('If non zero, pad the badge data to the specified length.'))
    BoolSetting(badgeSection,
            name     = 'strip_zeros_from_badge', 
            label    = 'Strip leading zeros', 
            data     = 'False',
            comment  = ('Strip leading zeros from badge code if set.'))
    TextSetting(badgeSection,
            name     = 'strip_badge',
            label    = 'Strip badge data', 
            data     = '', 
            comment  = ('If non empty, used with Python\'s slice operator to strip badge code data (e.g. 2:-1 to strip off the first two and last characters).'))
    BoolSetting(badgeSection,
            name     = 'numeric_only_badge', 
            label    = 'Only allow numeric badge data', 
            data     = 'False',
            comment  = ('Disallows badge data with non-numeric characters if set.'))
    return [badgeSection,]
    