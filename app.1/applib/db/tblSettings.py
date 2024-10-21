# -*- coding: utf-8 -*-
#
# Copyright 2010 Grosvenor Technology
#


"""
:mod:`tblSettings` --- Table Settings
=====================================

A TblSettings table can hold typed key-value settings. It provides easy get/set
functions to access these settings.

In addition to this, a setting can also have a format and other properties which
are used by dialogs to change or import and export settings.

.. seealso::
    Class :class:`applib.gui.settingsEditor.SettingsEditorDialog`

Example::
    
    # First define the settings

    appSettings = ({'name'          : 'app_initialised',
                    'displayName'   : 'Initialised',
                    'allowEdit'     : True,
                    'hideInEditor'  : False,                    
                    'format'        : 'bool',
                    'options'       : '',
                    'data'          : 'False',
                    'comment'       : 'True if wizard was completed and application was initialised'},
                     
                    {'name'         : 'app_site_code',
                     'displayName'  : 'Site code',
                     'allowEdit'    : True,
                     'hideInEditor' : False,                     
                     'format'       : 'number',
                     'options'      : '',
                     'data'         : '2392', 
                     'comment'      : 'Site code, only checked if emp_site_code_check is enabled' })
    
    securitySettings = (
                    {'name'         : 'cfg_pin_enable',
                     'displayName'  : 'Enable PIN',
                     'allowEdit'    : True,   
                     'hideInEditor' : False,                                   
                     'format'       : 'bool',
                     'options'      : '',
                     'data'         : 'False',
                     'comment'      : 'Enable/disable PIN check for application settings editor' },
    
                    {'name'         : 'cfg_pin',
                     'displayName'  : 'PIN',
                     'allowEdit'    : True,   
                     'hideInEditor' : False,              
                     'format'       : 'number',
                     'options'      : 'len=4',
                     'data'         : '1905',
                     'comment'      : 'PIN (unencrypted) to access application settings editor' } )

    settings = ({ 'name': 'App Settings',        'settings': appSettings},
                { 'name': 'Security',            'settings': securitySettings})
        
    # Now use the settings
    from applib.db.tblSettings import initAppSettings, getAppSetting, getAppSettings
    
    initAppSettings(defaultSettings)
    
    # get site code
    print getAppSetting('app_site_code')
    
    # set the site code to 1234
    getAppSettings().set('app_site_code', '1234')
    
    
.. note::
    
    The default values only get applied if they do not exist in the database.
    
.. tip::
    :class:`applib.Application` calls :func:`initAppSettings` if *defaultSettings*
    are passed in. See :ref:`howto-application-settings` for more details.

.. versionchanged:: 1.5
    Property 'hideInEditor' added

.. versionchanged:: 3.0
    Added classes and functions for creation of default settings dictionary.


.. autofunction:: applib.db.tblSettings.initAppSettings
.. autofunction:: applib.db.tblSettings.getAppSettings
.. autofunction:: applib.db.tblSettings.getAppSetting

.. autoclass:: applib.db.tblSettings.TblSettings
   :members:


Since applib version 3.0, it is also possible to define the default settings by using
the following classes. The function :func:`settingsToDict` can be used to convert
a list of :class:`SettingsSection` classes to create a list of dictionaries as needed by
:func:`initAppSettings`.

Example::

    # First define the settings
    appSection = SettingsSection('App Settings')
    BoolSetting(appSection,
            name     = 'app_initialised', 
            label    = 'Initialised', 
            data     = 'False',
            comment  = ('True if wizard was completed and application was initialised'))
    s = MultiListSetting(appSection,
            name     = 'app_log',
            label    = 'Logging',
            data     = '',
            comment  = ('Enable/disable verbose logging' ))
    s.addListOption('dbg', 'Debug')
    s.addListOption('net', 'Net')
    s.addListOption('sql', 'SQL')

    securitySection = SettingsSection('Security')
    BoolSetting(securitySection,
            name     = 'cfg_pin_enable', 
            label    = 'Enable settings PIN', 
            data     = 'False', 
            comment  = ('Enable/disable PIN check for application settings editor'))
    NumberSetting(securitySection,
            name     = 'cfg_pin', 
            label    = 'Settings PIN', 
            data     = '1905',
            length   = '4',  
            comment  = ('PIN (unencrypted) to access application settings editor'))

    initAppSettings([appSection, securitySection])
    


.. autofunction:: applib.db.tblSettings.settingsToDict

.. autoclass:: applib.db.tblSettings.SettingsSection
    :members:

.. autoclass:: applib.db.tblSettings.TextSetting
    :members:
    :inherited-members:    
    
.. autoclass:: applib.db.tblSettings.NumberSetting
    :members:
    :inherited-members:    
    
.. autoclass:: applib.db.tblSettings.BoolSetting
    :members:
    :inherited-members:    
    
.. autoclass:: applib.db.tblSettings.ListSetting
    :members:
    :inherited-members:    
    
.. autoclass:: applib.db.tblSettings.MultiListSetting
    :members:
    :inherited-members:    
    
"""


import log
import database

from applib.db.table import Table


_appSettings = None

def initAppSettings(appDefaultSettings):
    """Initialise application's settings with default settings."""
    global _appSettings
    if (appDefaultSettings == None):
        _appSettings = _NoSettings()
    else:
        _appSettings = TblSettings(database.getAppDB())
        _appSettings.open(appDefaultSettings)


def getAppSettings():
    """ Get the application's settings table object. "initAppSettings" needs
    to be called  before to load all default settings. This is normally 
    done by :class:`applib.Application`.
    """
    return _appSettings


def getAppSetting(name):
    """ Get application setting by its *name*.
    
    Example::
        log = getAppSetting('app_log')
    """
    return getAppSettings().get(name)


class TblSettings(Table):
    """ Create a tblSettings class instance. *db* is a 
    :class:`applib.db.database.Database` class.
    """

    columnDefs = {  'SettingID'     : 'INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL',
                    'Name'          : 'TEXT UNIQUE NOT NULL',
                    'Section'       : 'TEXT NOT NULL',
                    'AllowEdit'     : 'INTEGER',
                    'HideInEditor'  : 'INTEGER',
                    'DisplayName'   : 'TEXT NOT NULL',
                    'Format'        : 'TEXT',
                    'Options'       : 'TEXT',
                    'Data'          : 'TEXT',
                    'DefaultData'   : 'TEXT',
                    'Comment'       : 'TEXT' }
 

    def __init__(self, db, tableName='tblSettings'):
        super(TblSettings, self).__init__(db, tableName)
        self.__aliases = {}

    def open(self, defData):
        """Open tblSettings table.
        
        This function opens the settings table and will apply the default
        settings if needed. *defData* holds the default data (see above for 
        examples).
        """
        super(TblSettings, self).open()
        self.applyDefaults(defData)
        self.runSanityCheck()

    def updateDefaultItem(self, old, defItem, section):
        # private
        if ((old['Section'] == section) and
            (old['AllowEdit'] == defItem['allowEdit']) and
            (old['HideInEditor'] == defItem['hideInEditor']) and            
            (old['DisplayName'] == defItem['displayName']) and
            (old['Format'] == defItem['format']) and
            (old['Comment'] == defItem['comment']) and
            (old['DefaultData'] == defItem['data']) and
            (old['Options'] == defItem['options'])):
            return
            
        sql = '''UPDATE %s 
                    SET Section=?, 
                        AllowEdit=?, 
                        HideInEditor=?,
                        DisplayName=?, 
                        Format=?, 
                        Options=?,
                        Comment=?, 
                        DefaultData=? WHERE Name = ?''' % self.tableName
        self.runQuery(sql, (section , defItem['allowEdit'], defItem['hideInEditor'],
                            defItem['displayName'], defItem['format'], 
                            defItem['options'],     defItem['comment'],     
                            defItem['data'],        defItem['name']))
        

    def addDefaultItem(self, defItem, section):
        # private

        sql = '''INSERT INTO %s
                (Name, Section, AllowEdit, HideInEditor, DisplayName,
                Format, Options, Data, DefaultData, Comment)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);'''  % self.tableName
        try:
            self.runQuery(sql, (defItem['name'],  section , 
                                defItem['allowEdit'], defItem['hideInEditor'], defItem['displayName'], 
                                defItem['format'], defItem['options'],
                                defItem['data'], defItem['data'], defItem['comment']))
        except:
            log.err('Failed to add setting %s (%s)' % (defItem['name'], defItem['displayName']))
            raise


    def applyDefaults(self, defData):
        # private
        defaultSettings = set()
        for section in defData:
            for setting in section['settings']:
                if ('aliases' in setting):
                    for alias in setting['aliases'].split(','):
                        self.__aliases[ alias.strip() ] = setting['name']
                defaultSettings.add(setting['name'])
                if ('comment' not in setting):
                    setting['comment'] = None 
                if ('hideInEditor' not in setting):
                    setting['hideInEditor'] = False
                old = self.selectByName(setting['name'])
                if (old == None):
                    self.addDefaultItem(setting, section['name'])
                else:
                    self.updateDefaultItem(old, setting, section['name'])
        # find removed elements
        result_set = self.runSelectAll('SELECT Name, Data FROM %s'  % self.tableName)
        for setting in result_set:
            if (setting['Name'] not in defaultSettings):
                if (setting['Name'] in self.__aliases):
                    newName = self.__aliases[setting['Name']]
                    log.info('Converting setting %s => %s' % (setting['Name'], newName))
                    sql = 'UPDATE %s SET Data=? WHERE Name = ?' % self.tableName
                    self.runQuery(sql, (setting['Data'], newName))
                self.runQuery("DELETE FROM %s WHERE Name = ?" % self.tableName, (setting['Name'],))


    def getAsString(self, name):
        """ Returns value of setting *name* as string before
            any type conversion. If the setting does not exist, **None** is returned.
            
            .. versionadded:: 1.2               
        """
        if (name in self.__aliases):
            newName = self.__aliases[name]
            log.warn('Setting %s is deprecated, use %s instead!' % (name, newName))
            name = newName
        sql = '''SELECT Data FROM %s WHERE Name = ?'''  % self.tableName
        result_set = self.runSelectOne(sql, (name,))
        if (result_set == None):
            return None
        return result_set['Data']
        
    def get(self, name):
        """ Retrieve value of setting *name*.
        
        If the setting does not exist, **None** is returned. The returned value
        will be converted to its type (e.g. string, int or list)
            
        .. versionchanged:: 1.2 
           The default value will be returned, if the conversion 
           of a number fails.
         
        """
        if (name in self.__aliases):
            newName = self.__aliases[name]
            log.warn('Setting %s is deprecated, use %s instead!' % (name, newName))
            name = newName
        sql = '''SELECT Data, Format, DefaultData FROM %s WHERE Name = ?'''  % self.tableName
        result_set = self.runSelectOne(sql, (name,))
        if (result_set == None):
            return None
        return self.__getTypedData(name, result_set['Data'], result_set['Format'], result_set['DefaultData'])
    
    def getAllAsString(self):
        """Return dictionary containing all settings (as string).
        
        .. versionadded:: 1.2
        
        """
        settings = {}
        sql = '''SELECT Name, Data FROM %s'''  % self.tableName
        result_set = self.runSelectAll(sql)
        for result in result_set:
            settings[result['Name']] = result['Data']
        return settings 

    def getAll(self):
        """Return dictionary containing all settings (type converted)."""
        settings = {}
        sql = '''SELECT Name, Data, Format, DefaultData FROM %s'''  % self.tableName
        result_set = self.runSelectAll(sql)
        for result in result_set:
            settings[result['Name']] = self.__getTypedData(result['Name'], result['Data'], result['Format'], result_set['DefaultData'])
        return settings 

    def __getTypedData(self, name, data, dataFmt, defaultData):
        if (dataFmt == 'number'):
            try:
                return int(data)
            except:
                log.warn('Setting %s has invalid value %s (using default)' % (name, data))
                return defaultData
        elif (dataFmt == 'bool'):
            return (data == 'True')
        elif (dataFmt == 'multi'):
            return data.split('|') if data else []
        elif (dataFmt == 'text' and data):
            return data.replace('\\n', '\n')
        else:
            return data

    def set(self, name, data, checkType=True):
        """Apply new value *data* for setting *name*.
        The setting must already exist.
        
        If *checkType* is **True** a warning message will be logged if *data*
        is of the wrong type.
        
        """
        if (name in self.__aliases):
            newName = self.__aliases[name]
            log.warn('Setting %s is deprecated, use %s instead!' % (name, newName))
            name = newName
        # check type first
        try:
            if (checkType):
                sql = 'SELECT Format FROM %s WHERE Name = ?'  % self.tableName
                result_set = self.runSelectOne(sql, (name,))
                if (result_set != None):
                    dataFmt = result_set['Format']
                    if (dataFmt == 'number' and type(data) != int):
                        log.warn('Warning, setting %s with wrong type (%s, int expected!' % (name, type(data)))
                    elif (dataFmt == 'bool' and type(data) != bool):
                        log.warn('Warning, setting %s with wrong type (%s, bool expected!' % (name, type(data)))
        except Exception as e:
            log.err('Error while checking settings type! (%s)' % e)
        if (data == None):
            data = ''
        sql = 'UPDATE %s SET Data=? WHERE Name = ?' % self.tableName
        self.runQuery(sql, ('%s' % data, name,))


    def selectByName(self, name):
        sql = '''SELECT * FROM %s WHERE Name = ?''' % self.tableName
        result_set = self.runSelectOne(sql, (name,))
        if (result_set == None):
            return None
        return result_set

    def nameExists(self, name):
        sql = '''SELECT COUNT (*) FROM %s WHERE Name = ?''' % self.tableName
        count = self.runSelectOne(sql, (name,))

        if (count == None):
            return False
        elif (count[0] == 0):
            return False
        return True

    def selectAll(self):
        sql = 'SELECT * FROM %s ORDER BY Section' % self.tableName
        result_set = self.runSelectAll(sql)
        return result_set


    def selectBySection(self, section):
        sql = '''SELECT * FROM %s WHERE Section = ?''' % self.tableName
        result_set = self.runSelectAll(sql, (section,))
        return result_set

    def selectVisibleBySection(self, section):
        sql = '''SELECT * FROM %s WHERE Section = ? AND HideInEditor = ?''' % self.tableName
        result_set = self.runSelectAll(sql, (section,0))
        return result_set

    def selectSectionNames(self):
        sql = '''SELECT DISTINCT Section FROM %s ORDER BY Section ASC''' % self.tableName
        result_set = self.runSelectAll(sql)
        return result_set

    def runSanityCheck(self):
        for s in self.selectAll():
            try:
                self.checkSetting(s)
            except:
                log.err('Failed to check value %s' % s['Name'])
        
    def checkSetting(self, s):
        name    = s['Name']
        data    = s['Data']        
        dataFmt  = s['Format']
        options = s['Options']
        if (dataFmt == 'number'):
            try:
                _n = int(data)
            except:
                log.warn('Setting %s(=%s) is not a number!' % (name, data))
        elif (dataFmt == 'bool'):
            if (data not in ('True', 'False')):
                log.warn('Setting %s(=%s) is not a boolean (e.g. True or False)!' % (name, data))
        elif (dataFmt == 'list'):
            options = [ i.split('=',1)[-1] for i in options.split('|') ]
            if (data not in options):
                log.warn('Setting %s(=%s) has invalid list value (e.g. not %s)!' % (name, data, ','.join(options)))
        elif (dataFmt == 'multi'):
            options = [ i.split('=',1)[-1] for i in options.split('|') ]
            for d in data.split('|'):
                if (d and d not in options):
                    log.warn('Setting %s(=%s) has invalid multi-list value (e.g. %s not in %s)!' % (name, data, d, ','.join(options)))
                


class _NoSettings(object):
    """ Settings table with no settings."""

    def get(self, name):
        return None

    def getAll(self):
        return []

    def set(self, name, data, checkType=True):
        raise Exception('no settings!')


class SettingsSection():
    """ Settings section class. A section has a name and a list of settings.
    
    .. versionadded:: 3.0
    """
    
    def __init__(self, name, sectionComment = ''):
        self.__name = name
        self.__sectionComment = sectionComment
        self.__settings = []
        
    def add(self, setting):
        """ Add setting to section. """
        self.__settings.append(setting)
        
    def extend(self, settings):
        """ Add list of settings to section. """
        self.__settings.extend(settings)

    def getSettings(self):
        """ Return all settings of section. """
        return self.__settings
    
    def getName(self):
        """ Get name of section. """
        return self.__name

    def getSectionComment(self):
        """ Get the comment for the section. """
        return self.__sectionComment


class _BaseSetting(object):
    """ Base setting class. """

    def __init__(self, section=None, settingType=None, name=None, label=None, data=None, comment=None):
        self.__name = name
        self.__label = label
        self.__data = data
        self.__comment = comment
        self.__type = settingType
        self.__aliases = []
        self.__allowEdit = True
        self.__hideInEditor = False
        if (section != None):
            section.add(self)
        
    def setComment(self, comment):
        """ Set help/comment. """
        self.__comment = comment

    def getComment(self):
        """ Return help/comment. """
        return self.__comment
    
    def getName(self):
        """ Set name (identifier) of setting. """
        return self.__name
    
    def getLabel(self):
        """ Set label of setting. """
        return self.__label
    
    def getType(self):
        """ Return type of setting. """
        return self.__type
    
    def setAllowEdit(self, val):
        """ Allow editing of value via settings editor (*val* must be **True** or **False**). """
        self.__allowEdit = val
        
    def getAllowEdit(self):
        """ Return **True** if editing the setting via the settings editor is allowed. """
        return self.__allowEdit
    
    def setHideInEditor(self, val):
        """ Hide setting in settings editor (*val* must be **True** or **False**). """
        self.__hideInEditor = val
        
    def getHideInEditor(self):
        """ Return **True** if setting should be hidden in settings editor. """
        return self.__hideInEditor
        
    def getData(self):
        """ Return default value of setting. """
        return self.__data
    
    def addAlias(self, alias):
        """ Add alias of setting. """
        self.__aliases.append(alias)
        
    def getAliases(self):
        """ Return list of aliases. """
        return self.__aliases
    
    def _getOptionsForDict(self):
        # This can be overridden
        return ''
    
    def getAsDict(self):
        """ Return setting as dictionary. This is useful when importing settings into the settings table. """
        # this can be used if the field type has no options
        d = {   'name'          : self.getName(),
                'displayName'   : self.getLabel(),
                'allowEdit'     : self.getAllowEdit(),
                'format'        : self.getType(),
                'options'       : self._getOptionsForDict(),
                'data'          : self.getData(),
                'comment'       : self.getComment()}
        # add aliases if needed
        if (self.getAliases()):
            d.update({'aliases' : ','.join(self.getAliases())})
        # Check if that is needed
        if (self.getHideInEditor()):
            d.update({'hideInEditor' : self.getHideInEditor()})
        return d

        
class BoolSetting(_BaseSetting):
    """ Wrapper class for defining a boolean setting.
    
    .. versionadded:: 3.0
    """
    
    def __init__(self, section=None, name=None, label=None, data=None, comment=None):
        super(BoolSetting, self).__init__(section, 'bool', name, label, data, comment)


class TextSetting(_BaseSetting):
    """ Wrapper class for defining a text setting.
    
    .. versionadded:: 3.0
    """

    def __init__(self, section=None, name=None, label=None, data=None, comment=None):
        super(TextSetting, self).__init__(section, 'text', name, label, data, comment)


class NumberSetting(_BaseSetting):
    """ Wrapper class for defining a numeric setting.
    
    .. versionadded:: 3.0
    """

    def __init__(self, section=None, name=None, label=None, data=None, minValue=None, maxValue=None, length=None, units=None, comment=None):
        super(NumberSetting, self).__init__(section, 'number', name, label, data, comment)
        self.__minValue = minValue
        self.__maxValue = maxValue
        self.__units = units
        self.__len = length
            
    def _getOptionsForDict(self):
        s = []
        if (self.__minValue != None):
            s.append('min=%s' % self.__minValue)
        if (self.__maxValue != None):
            s.append('max=%s' % self.__maxValue)
        if (self.__len != None):
            s.append('len=%s' % self.__len)
        if (self.__units != None):
            s.append('unit=%s' % self.__units)
        return ','.join(s)


class _ListSetting(_BaseSetting):
    """ Base class for list setting.
    
    .. versionadded:: 3.0
    """

    def __init__(self, listType, section=None, name=None, label=None, data=None, comment=None):
        super(_ListSetting, self).__init__(section, listType, name, label, data, comment)
        self.__options = []
            
    def addListOption(self, key=None, label=None):
        """ Add list option. *key* and *label* are both **Strings**. """
        self.__options.append({key : label})
        
    def _getOptionsForDict(self):
        # 'options'      : 'Internal=internal|USB=usb',
        s = []
        for option in self.__options:
            for key, label in option.items():
                if (label == None):
                    s.append('%s' % key)
                else:
                    s.append('%s=%s' % (label, key))
        return '|'.join(s)


class ListSetting(_ListSetting):
    """ Wrapper class for defining list setting. 
    
    .. versionadded:: 3.0
    """

    def __init__(self, section=None, name=None, label=None, data=None, comment=None):
        super(ListSetting, self).__init__('list', section, name, label, data, comment)
        self.__options = []


class MultiListSetting(_ListSetting):
    """ Wrapper class for defining multi-list setting.
    
    .. versionadded:: 3.0
    """

    def __init__(self, section=None, name=None, label=None, data=None, comment=None):
        super(MultiListSetting, self).__init__('multi', section, name, label, data, comment)
        self.__options = []


def settingsToDict(settings):
    """ Convert list of setting sections to dictionary suitable for :func:`initAppSettings`. 
    
    .. versionadded:: 3.0
    """
    # Create sections dictionary with name as key, and sub-dictionary as value
    sections = {}
    for section in settings:
        dictSettings = [s.getAsDict() for s in section.getSettings()]
        sectionName = section.getName()
        sectionComment = section.getSectionComment()
        
        # Some sections appear twice, but we only want one of each in the document, just extend settings if already have it
        if (sectionName in sections):
            sections[sectionName]['settings'].extend(dictSettings)
        else:
            sections[sectionName] = {'settings': dictSettings, 'comment': sectionComment}
            
    # Return list containing dictionary for each entry in sections
    return [ {'name':k, 'sectionComment':v['comment'], 'settings':v['settings']} for k,v in sections.iteritems() ]
    

def _compareSetting(section, setting, new, old):
    if (new == old):
        return
    log.warn('Setting %s / %s differs' % (section, setting))
    diff = set(new.keys()) - set(old.keys())
    if (diff):
        log.warn('Added setting key for %s / %s: %s' % (section, setting, ', '.join(diff)))
    diff = set(old.keys()) - set(new.keys())
    if (diff):
        log.warn('Missing settings for %s / %s: %s' % (section, setting, ', '.join(diff)))
    for skey in set(new.keys()) & set(old.keys()):
        if (new[skey] != old[skey]):
            log.warn('%s / %s [%s] differs:' % (section, setting, skey))
            log.warn('      %-25s : %-25s' % (skey, new[skey]))
            log.warn('      %-25s : %-25s' % (skey, old[skey]))
    
def _compareSettingsSection(section, new, old):
    newSettings = {}
    for s in new:
        newSettings[s['name']] = s
    oldSettings = {}
    for s in old:
        oldSettings[s['name']] = s
    if (newSettings == oldSettings):
        return
    log.warn('Settings in section %s differ' % section)
    diff = set(newSettings.keys()) - set(oldSettings.keys())
    if (diff):
        log.warn('Added settings in %s: %s' % (section, ', '.join(diff)))
    diff = set(oldSettings.keys()) - set(newSettings.keys())
    if (diff):
        log.warn('Missing settings in %s: %s' % (section, ', '.join(diff)))
    for setting in set(newSettings.keys()) & set(oldSettings.keys()):
        _compareSetting(section, setting, newSettings[setting], oldSettings[setting])

def compareSettingsDict(newSettings, oldSettings):
    newSections = {}
    for s in newSettings:
        newSections[s['name']] = s['settings']
    oldSections = {}
    for s in oldSettings:
        oldSections[s['name']] = s['settings']
    diff = set(newSections.keys()) - set(oldSections.keys())
    if (diff):
        log.warn('Added sections: %s' % ', '.join(diff))
    diff = set(oldSections.keys()) - set(newSections.keys())
    if (diff):
        log.warn('Missing sections: %s' % ', '.join(diff))
    for section in set(newSections.keys()) & set(oldSections.keys()):
        _compareSettingsSection(section, newSections[section], oldSections[section])
    
