# -*- coding: utf-8 -*-
#
# Copyright 2011 Grosvenor Technology
#


"""
:mod:`settingsEditor` --- Table Settings Editor
===============================================

This class enables a settings table (:class:`applib.db.tblSettings.TblSettings`) to be edited from a user menu
at the terminal.

Data types and editors
----------------------

:class:`SettingsEditorDialog` provides the following **editors** for the settings data:

    - **Boolean check box** for True/False::
    
        'name'         : 'tst_bool',
        'displayName'  : 'Test bool',
        'allowEdit'    : True,                 
        'hideInEditor' : False,        
        'format'       : 'bool',
        'options'      : '',
        'data'         : 'False' 

    - **Number input** which allow a maximum and minimum value to be validated::
    
        'name'         : 'tst_number',
        'displayName'  : 'Test Number 0..99',
        'allowEdit'    : True,                 
        'hideInEditor' : False,        
        'format'       : 'number',
        'options'      : 'min=0,max=99',
        'data'         : '25'

    - **Number input** with unit::
    
        'name'         : 'tst_timeout',
        'displayName'  : 'Timeout',
        'allowEdit'    : True,                 
        'hideInEditor' : False,        
        'format'       : 'number',
        'options'      : 'min=10,unit=sec',
        'data'         : '25'

    - **Text input** editor which can also take input from a reader and or check the length of input data::
    
         'name'         : 'tst_rdr',
         'displayName'  : 'Test reader',
         'allowEdit'    : True,            
         'hideInEditor' : False,
         'format'       : 'text',
         'options'      : 'len=12,rdr',
         'data'         : 'Hello'
    
    - **Masked Text** editor where the option field is used for the mask::
     
        'name'         : 'tst_mask',
        'displayName'  : 'Test mask',
        'allowEdit'    : True,            
        'hideInEditor' : False,             
        'format'       : 'mask',
        'options'      : 'AA_####_##',
        'data'         : 'GB-1234-12' 

    - **List selection** editor where the options field contain a list of the allowed choices::
    
        'name'         : 'tst_list',
        'displayName'  : 'Test list',
        'allowEdit'    : True,            
        'hideInEditor' : False,             
        'format'       : 'list',
        'options'      : 'Item1|Item2|Item3|Item4',
        'data'         : 'Item1'

    - **Multi selection** editor where the options field contain a list of the allowed choices and multiple items can be selected::
    
        'name'         : 'tst_multi',
        'displayName'  : 'Test Multi',
        'allowEdit'    : True,        
        'hideInEditor' : False,                 
        'format'       : 'multi',
        'options'      : 'Item1|Item2|Item3|Item4',
        'data'         : 'Item1'

    - **Time editor** to enter a valid time of day::
    
        'name'         : 'tst_time',
        'displayName'  : 'Test time',
        'allowEdit'    : True,       
        'hideInEditor' : False,                  
        'format'       : 'time',
        'options'      : '',
        'data'         : '09:00:00'

    - **Date editor** to enter a valid date::
    
        'name'         : 'tst_date',
        'displayName'  : 'Test Date',
        'allowEdit'    : True,              
        'hideInEditor' : False,           
        'format'       : 'time',
        'options'      : '',
        'data'         : '20/01/2011'
                
    - **IP address** editor to enter a valid address::
    
        'name'         : 'tst_ip',
        'displayName'  : 'Test IP',
        'allowEdit'    : True,             
        'hideInEditor' : False,            
        'format'       : 'ipAddr',
        'options'      : '',
        'data'         : '172.16.32.10'

.. versionchanged:: 1.5
    Property 'hideInEditor' added

.. versionchanged:: 1.7
    Unit option added for number settings

See :class:`applib.db.tblSettings.TblSettings` for more details on how to define settings.

Sub-sections
------------

.. versionadded:: 1.6

Sub-sections are supported by specifying a path-like section name, e.g.::

 settings = ({ 'name': 'App Settings',                'settings': appSettings},
             { 'name': 'Security',                    'settings': securitySettings},
             { 'name': 'Main Section/Sub Section 1',  'settings': someSettings},
             { 'name': 'Main Section/Sub Section 2',  'settings': someOtherSettings} )                

See :class:`applib.db.tblSettings.TblSettings` for more details on how to define settings.

Settings editor in application setup
------------------------------------
    
Normally the table settings are edited via the application setup menu.

Example of appSetup.py::

    # -*- coding: utf-8 -*-
    #
    
    import applib
    import appSettings
    from applib.gui import settingsEditor
    
    
    def runAppSetup():
        # Use applib.Application for initialisation and run settings editor dialog
        #
        app = applib.Application(settingsEditor.SettingsEditorDialog, appSettings.settings)        
        app.run()
    
    #
    # Entry point for application from application setup
    #
    # This script is executes when going to Firmware Setup -> Application -> Setup
    #
    if __name__ == '__main__':
        runAppSetup()


Calling the settings editor manually
------------------------------------

The following example shows how to call the application setting editor:

.. code-block:: python

    from applib.gui.settings import SettingsEditorDialog
    
    settings = SettingsEditorDialog()
    settings.run()

Classes
-------

"""

import itg
import datetime
import applib.db.tblSettings as tblSettings

def _parseOptions(option_str):
    option = {}
    for o in option_str.split(','):
        item = o.split('=')
        if (len(item) == 2):
            key = item[0].strip()
            val = item[1].strip()
            option[key] = val
    return option

def _parseListItems(option_str):
    oList = []
    for i in option_str.split('|'):
        if ('=' in i):
            oList.append( i.split('=', 1))
        else:
            oList.append( ( i, i) )
    return oList


class SettingsEditorDialog(itg.PseudoDialog):
    """Create a :class:`SettingsEditorDialog` instance. The application setting
    **cfg_pin_enable** is used if *pinRequired* is not given. If **cfg_pin_enable**
    does not exist within the application settings no PIN will be required.
    
    The PIN is requested via :class:`PINDialog` which uses the same settings table. The
    application setting **cfg_pin** is used for the PIN. 
    
    The application settings (via :func:`applib.db.tblSettings.getAppSettings()`) are
    used when *settingsTable* is **None**.
    """

    def __init__(self, pinRequired=None, settingsTable=None):
        super(SettingsEditorDialog, self).__init__()
        self.__tblSettings = settingsTable
        
        if (self.__tblSettings == None):
            self.__tblSettings = tblSettings.getAppSettings()
            
        if (pinRequired == None):
            self.__pinRequired = self.__tblSettings.get('cfg_pin_enable')
            if (self.__pinRequired == None):
                self.__pinRequired = (self.__tblSettings.get('cfg_pin') != None)
        else:
            self.__pinRequired = pinRequired

        
    def run(self):
        """Runs the settings class"""
        
        if (self.__pinRequired):
            mgr = PINDialog(SettingsTable=self.__tblSettings)
            if (mgr.run() != itg.ID_OK):
                return itg.ID_BACK

        mgr = _SectionsDialog(self.__tblSettings)
        return mgr.run()
            
    

class PINDialog(itg.Dialog):
    """ PIN Dialog class.
        
        This class can be used to prompt the user to enter the PIN from the 
        settings. The class also validates the entered PIN. It returns **itg.ID_OK** 
        on a valid PIN entry.

        The application settings (via :func:`applib.db.tblSettings.getAppSettings()`) are
        used when *settingsTable* is **None**. The application setting **cfg_pin** is 
        used for the PIN. 
       
    """
    
    def __init__(self, SettingsTable=None):
        super(PINDialog, self).__init__()

        if (SettingsTable==None):
            SettingsTable = tblSettings.getAppSettings()

        self.__pin = str(SettingsTable.get('cfg_pin'))
        view = itg.NumberInputView(title=_('Enter PIN'), password=True)
        view.setButton(0, 'OK',     itg.ID_OK,       cb=self.__onOK, icon=None)
        view.setButton(1, 'Cancel', itg.ID_CANCEL,   cb=self.cancel, icon=None)
        self.addView(view)
        
    
    def __onOK(self, btnID):
        if (self.__pin != self.getView().getValue()):
            itg.msgbox(itg.MB_OK, 'Incorrect PIN entered\n')
            self.cancel()
        else:
            self.quit(btnID)


class _SectionsDialog(itg.Dialog):
    
    def __init__(self, tblSettings, path=''):
        super(_SectionsDialog, self).__init__()
        self.__tblSettings = tblSettings
        if (not path):
            title = _('Settings editor')
        else:
            title = path.split('/')[-2]
        view = itg.MenuView(title)
        view.setBackButton('Back', cb=self.back)        
        view.setCancelButton('Cancel', cb=self.cancel)
        sectionNames = set()
        for row in self.__tblSettings.selectSectionNames():
            section = row['Section']
            if (not section.startswith(path)):
                continue
            if (len(self.__tblSettings.selectVisibleBySection(row['Section'])) == 0):
                continue
            sep  = section.find('/', len(path))
            if (sep >= 0): # found subsection
                name = section[len(path):sep]
                newPath = section[:sep+1]
            else: 
                name = section[len(path):]
                newPath = section
            if (name not in sectionNames):
                sectionNames.add(name)
                view.appendRow(name, hasSubItems=True, cb=self.__onSelect, data=newPath)
        self.addView(view)    
        
        
    def __onSelect(self, pos, row):
        path = row['data']
        if (path.endswith('/')):
            dlg = _SectionsDialog(self.__tblSettings, path)
        else:
            dlg = _SectionEdit(self.__tblSettings, path)
        dlg.run()


class _SectionEdit(itg.Dialog):
    
    def __init__(self, tblSettings, sectionName):
        super(_SectionEdit, self).__init__()
        self.__tblSettings = tblSettings
        title = sectionName.split('/')[-1]
        view = itg.MenuView(title)
        view.setBackButton('Back', cb=self.back)        
        view.setCancelButton('Cancel', cb=self.cancel)
        for row in self.__tblSettings.selectVisibleBySection(sectionName):
            if (str(row['Format']).startswith('bool')):
                bval = (True if (row['Data'] == 'True') else False)
                view.appendRow(row['DisplayName'], checked=bval, hasSubItems=False, data=row, cb=self.__onToggleCheckbox)
            else:
                view.appendRow(row['DisplayName'], value=self.__getData(row), data=row, cb=self.__onSelect)
        self.addView(view)    
    
    def __getData(self, rowData):
        if (rowData['Format'] in ('multi', 'list')):
            options = {}
            for (label, identifier) in _parseListItems(rowData['Options']):
                options[identifier] = label
            data = []
            for d in rowData['Data'].split('|'):
                if (d in options):
                    data.append(options[d])
                else:
                    data.append(d)
            data = ','.join(data) 
        elif (rowData['Format'] == 'number'):
            options = _parseOptions(rowData['Options'])
            if ('unit' in options):
                data = '%s %s' % (rowData['Data'],options['unit'])
            else:
                data = rowData['Data']
        else:
            data = rowData['Data']
        return data
        
    def __isAllowedEdit(self, rowData):
        return (rowData['allowEdit'])

    def __onToggleCheckbox(self, pos, row):
        if (not self.__isAllowedEdit(row['data'])):
            return
        newValue = not row['checked']
        menu = self.getView()
        menu.changeRow(pos, 'checked', newValue)
        self.__tblSettings.set(row['data']['Name'], newValue)
        
        
    def __onSelect(self, pos, row):
        rowData = row['data']
        if (not self.__isAllowedEdit(rowData)):
            itg.msgbox(itg.MB_OK, '"%s" is "%s"' % (rowData['DisplayName'], self.__getData(rowData)))
        else:
            dlgTypes = { 'number'   : _NumberInputDialog, 
                         'mask'     : _MaskInputDialog,
                         'list'     : _ListInputDialog,
                         'multi'    : _MultiInputDialog,                         
                         'text'     : _TextInputDialog,
                         'time'     : _TimeInputDialog,
                         'date'     : _DateInputDialog,
                         'ipAddr'   : _IpAddrInputDialog }
            
            if (rowData['format'] in dlgTypes):
                dlg = dlgTypes[rowData['format']](self.__tblSettings, rowData)
            else:
                dlg = _TextInputDialog(self.__tblSettings, rowData)
            if (dlg.run() == itg.ID_OK):
                dbrow = self.__tblSettings.selectByName(rowData['Name'])
                menu = self.getView()
                menu.changeRow(pos, 'value', self.__getData(dbrow))
                menu.changeRow(pos, 'data', dbrow)
    

class _HelpDialog(itg.Dialog):
    
    def __init__(self, row):
        super(_HelpDialog, self).__init__()
        helpText  = row['Comment']
        helpText += '\n\nDefault: %s' % row['DefaultData']
        helpTitle = '%s (%s)' % (row['DisplayName'], row['Name'])
        view = itg.TextView(helpTitle, helpText, 'text/plain')
        view.setButton(_('OK'), itg.ID_OK, self.quit)
        self.addView(view)


class _NumberInputDialog(itg.Dialog):
    
    def __init__(self, tblSettings, dbrow):
        super(_NumberInputDialog, self).__init__()

        self.__tblSettings = tblSettings
        self.__dbRow = dbrow

        view = itg.NumberInputView(title=self.__dbRow['DisplayName'])
        view.setButton(0, 'OK', itg.ID_OK, cb=self.__onOK)
        if (self.__dbRow['Comment']):
            view.setButton(1, 'Help', itg.ID_HELP, cb=self.__onHelp)        
        view.setButton(2, 'Reset',  itg.ID_BACK,   cb=self.__onReset)        
        view.setButton(3, 'Cancel', itg.ID_CANCEL, cb=self.cancel)
        view.setValue(self.__dbRow['data'])
        self.addView(view)

    def __isValid(self):
        try:
            val = int(self.getView().getValue())
            opt = _parseOptions(self.__dbRow['options'])
            if (('min' in opt) and (val < int(opt['min']))):
                itg.msgbox(itg.MB_OK, 'Number must be greater or equal to %s' % opt['min'])
                return False
            if (('max' in opt) and (val > int(opt['max']))):
                itg.msgbox(itg.MB_OK, 'Number must be less than or equal to %s' % opt['max'])
                return False
        except:
                itg.msgbox(itg.MB_OK, 'A valid number must be entered!')
                return False
            
        
        return True

    def __onOK(self, btnID):
        val = self.getView().getValue()
        if (self.__dbRow['data'] != val):
            if (self.__isValid()):
                self.__tblSettings.set(self.__dbRow['Name'], int(val))
                self.quit(btnID)
        else:
            self.cancel()

    def __onHelp(self, btnID):
        self.runDialog(_HelpDialog(self.__dbRow))
    
    def __onReset(self, btnID):
        self.getView().setValue( self.__dbRow['DefaultData'])

    def getValue(self):
        return self.getView().getValue()




class _MaskInputDialog(itg.Dialog):
    
    def __init__(self, tblSettings, dbrow):
        super(_MaskInputDialog, self).__init__()

        self.__tblSettings = tblSettings
        self.__dbRow = dbrow

        view = itg.MaskedTextInputView(self.__dbRow['Options'], self.__dbRow['data'], self.__dbRow['DisplayName'])
        view.setButton(0, 'OK', itg.ID_OK, cb=self.__onOK)
        if (self.__dbRow['Comment']):
            view.setButton(1, 'Help', itg.ID_HELP, cb=self.__onHelp)        
        view.setButton(2, 'Reset',  itg.ID_BACK,   cb=self.__onReset)        
        view.setButton(3, 'Cancel', itg.ID_CANCEL, cb=self.cancel)
        self.addView(view)

    def __onOK(self, btnID):
        val = self.getView().getValue()
        if (self.__dbRow['data'] != val):
            self.__tblSettings.set(self.__dbRow['Name'], val)
            self.quit(btnID)
        else:
            self.cancel()

    def __onHelp(self, btnID):
        self.runDialog(_HelpDialog(self.__dbRow))
    
    def __onReset(self, btnID):
        self.getView().setValue( self.__dbRow['DefaultData'])

    def getValue(self):
        return self.getView().getValue()


class _TextInputDialog(itg.Dialog):
    
    def __init__(self, tblSettings, dbrow):
        super(_TextInputDialog, self).__init__()

        self.__tblSettings = tblSettings
        self.__dbRow = dbrow

        if (self.__isReaderAllowed(self.__dbRow['options'])):
            self.setReaderCb(self.__onReader)

        view = itg.TextInputView(self.__dbRow['DisplayName'])
        view.setButton(0, 'OK', itg.ID_OK, cb=self.__onOK)
        if (self.__dbRow['Comment']):
            view.setButton(1, 'Help', itg.ID_HELP, cb=self.__onHelp)        
        view.setButton(2, 'Reset',  itg.ID_BACK,   cb=self.__onReset)        
        view.setButton(3, 'Cancel', itg.ID_CANCEL, cb=self.cancel)
        data = self.__dbRow['data']
        if (data == None):
            data = ''
        view.setValue(data)
        self.addView(view)

    def __onReader(self, isValid, rdr, decoder, data):
        self.getView().setValue(data)
        itg.successSound()

    def __isReaderAllowed(self, option_str):
        if (option_str.find('rdr') >= 0):
            return True
        return False

    def __isValid(self):
        val = self.getView().getValue()
        opt = _parseOptions(self.__dbRow['options'])
        if (('len' in opt) and (len(val) > int(opt['len']))):
            itg.msgbox(itg.MB_OK, 'Input length must be less than %s' % opt['len'])
            return False
        return True

    def __onOK(self, btnID):
        val = self.getView().getValue()
        if (self.__dbRow['data'] != val):
            if (self.__isValid()):
                self.__tblSettings.set(self.__dbRow['Name'], val)
                self.quit(btnID)
        else:
            self.cancel()

    def __onHelp(self, btnID):
        self.runDialog(_HelpDialog(self.__dbRow))
    
    def __onReset(self, btnID):
        self.getView().setValue( self.__dbRow['DefaultData'])

    def getValue(self):
        return self.getView().getValue()


class _ListInputDialog(itg.Dialog):
    
    def __init__(self, tblSettings, dbrow):
        super(_ListInputDialog, self).__init__()
        self.__tblSettings = tblSettings
        self.__dbRow = dbrow
        view = itg.ListView(title=self.__dbRow['DisplayName'])
        view.setOkButton('OK', self.__onOK)
        if (self.__dbRow['Comment']):        
            view.setHelpButton('Help', self.__onHelp)        
        view.setCancelButton('Cancel', self.cancel)
        for (label, data) in _parseListItems(self.__dbRow['Options']):
            view.appendRow(label, data)
        (idx, _row) = view.findRowBy('data', self.__dbRow['data'])
        if (idx != None):
            view.selectRow(idx)        
            self.__selectedItem = self.__dbRow['data']
        self.addView(view)

    def __onOK(self, btnID):
        value = self.getValue()
        if (self.__dbRow['data'] != value):
            self.__tblSettings.set(self.__dbRow['Name'], value)
            self.quit(btnID)
        else:
            self.cancel()

    def __onHelp(self, btnID):
        self.runDialog(_HelpDialog(self.__dbRow))
    
    def getValue(self):
        return self.getView().getSelectedRow()['data']


class _MultiInputDialog(itg.Dialog):
    
    def __init__(self, tblSettings, dbrow):
        super(_MultiInputDialog, self).__init__()
        self.__tblSettings = tblSettings
        self.__dbRow = dbrow
        view = itg.CheckListView(title=self.__dbRow['DisplayName'])
        view.setOkButton('OK', self.__onOK)
        if (self.__dbRow['Comment'] and hasattr(view, 'setHelpButton')):        
            view.setHelpButton('Help', self.__onHelp)
        selections = dbrow['data'].split('|')        
        view.setCancelButton('Cancel', self.cancel)
        for (label,data) in _parseListItems(self.__dbRow['Options']):
            checked = data in selections
            view.appendRow(label, checked, data)
        self.addView(view)

    def __onOK(self, btnID):
        value = self.getValue()
        if (self.__dbRow['data'] != value):
            self.__tblSettings.set(self.__dbRow['Name'], value)
            self.quit(btnID)
        else:
            self.cancel()

    def __onHelp(self, btnID):
        self.runDialog(_HelpDialog(self.__dbRow))
    
    def getValue(self):
        view = self.getView()
        values = '|'.join( r['data'] for r in view.getSelectedRows())
        return values


class _TimeInputDialog(itg.Dialog):
    
    def __init__(self, tblSettings, dbrow):
        super(_TimeInputDialog, self).__init__()

        self.__tblSettings = tblSettings
        self.__dbRow = dbrow
        
        view = itg.TimeInputView(title=self.__dbRow['DisplayName'])
        view.setButton(0, 'OK', itg.ID_OK, cb=self.__onOK)
        if (self.__dbRow['Comment']):
            view.setButton(1, 'Help', itg.ID_HELP, cb=self.__onHelp)        
        view.setButton(2, 'Reset',  itg.ID_BACK,   cb=self.__onReset)        
        view.setButton(3, 'Cancel', itg.ID_CANCEL, cb=self.cancel)
        view.setTime(datetime.datetime.strptime(self.__dbRow['data'], '%H:%M:%S'))
        self.addView(view)

    def getValue(self):
        return(self.getView().getTime().strftime('%H:%M:%S'))
        
    def __onOK(self, btnID):
        val = self.getValue()
        if (self.__dbRow['data'] != val):
            self.__tblSettings.set(self.__dbRow['Name'], val)
            self.quit(btnID)
        else:
            self.cancel()
        self.quit(btnID)
        
    def __onHelp(self, btnID):
        self.runDialog(_HelpDialog(self.__dbRow))
    
    def __onReset(self, btnID):
        self.getView().setTime(datetime.datetime.strptime(self.__dbRow['DefaultData'], '%H:%M:%S'))

    
class _DateInputDialog(itg.Dialog):
    
    def __init__(self, tblSettings, dbrow):
        super(_DateInputDialog, self).__init__()
        
        self.__tblSettings = tblSettings
        self.__dbRow = dbrow
        
        view = itg.DateInputView(title=self.__dbRow['DisplayName'])
        view.setButton(0, 'OK', itg.ID_OK, cb=self.__onOK)
        if (self.__dbRow['Comment']):
            view.setButton(1, 'Help', itg.ID_HELP, cb=self.__onHelp)        
        view.setButton(2, 'Reset',  itg.ID_BACK,   cb=self.__onReset)
        view.setButton(3, 'Cancel', itg.ID_CANCEL, cb=self.cancel)
        view.setDate(datetime.datetime.strptime(self.__dbRow['data'], '%d/%m/%Y'))
        self.addView(view)

    def getValue(self):
        return(self.getView().getDate().strftime('%d/%m/%Y'))

    def __onOK(self, btnID):
        val = self.getValue()
        if (self.__dbRow['data'] != val):
            self.__tblSettings.set(self.__dbRow['Name'], val)
            self.quit(btnID)
        else:
            self.cancel()
        self.quit(btnID)

    def __onHelp(self, btnID):
        self.runDialog(_HelpDialog(self.__dbRow))
    
    def __onReset(self, btnID):
        self.getView().setDate(datetime.datetime.strptime(self.__dbRow['DefaultData'], '%d/%m/%Y'))


class _IpAddrInputDialog(itg.Dialog):
    
    def __init__(self, tblSettings, dbrow):
        super(_IpAddrInputDialog, self).__init__()
        
        self.__tblSettings = tblSettings
        self.__dbRow = dbrow

        view = itg.IPInputView(title=self.__dbRow['DisplayName'])
        view.setValue(self.__dbRow['data'])
        view.setButton(0, 'OK', itg.ID_OK, cb=self.__onOK)
        if (self.__dbRow['Comment']):
            view.setButton(1, 'Help', itg.ID_HELP, cb=self.__onHelp)        
        view.setButton(2, 'Reset',  itg.ID_BACK,   cb=self.__onReset)        
        view.setButton(3, 'Cancel', itg.ID_CANCEL, cb=self.cancel)
        self.addView(view)

    def getValue(self):
        return self.getView().getValue(padded=False)

    def __onOK(self, btnID):
        val = self.getValue()
        if (self.__dbRow['data'] != val):
            self.__tblSettings.set(self.__dbRow['Name'], val)
            self.quit(btnID)
        else:
            self.cancel()
        self.quit(btnID)        
        
    def __onHelp(self, btnID):
        self.runDialog(_HelpDialog(self.__dbRow))
    
    def __onReset(self, btnID):
        self.getView().setValue( self.__dbRow['DefaultData'])

