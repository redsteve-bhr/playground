# -*- coding: utf-8 -*-
#
# Copyright 2013 Grosvenor Technology
#
import os
import itg
import updateit
import re
import log
import cfg
from applib.db.tblSettings import getAppSetting, SettingsSection, NumberSetting, TextSetting
from applib.gui import screensaver, idlePhoto
from applib.utils import busyIndicator, healthMonitor
from engine import dynButtons
from applib import bio
from engine import empIdentifyDlg

_outOfDiskSpace = False

def getDiskSpace():
    # Note: Eclipse will mark statvfs as being undefined, because this 
    # function is POSIX-only and does not exist under Windows. It will
    # work correctly when run on the terminal.
    stat = os.statvfs('/mnt/user/')
    total_space = (stat.f_frsize * stat.f_blocks) / 1048576.00
    free_space = (stat.f_frsize * stat.f_bfree) / 1048576.00 # Free space in MB
    return (total_space, free_space)

def _checkDiskSpace():
    global _outOfDiskSpace
    minDiskSpace = getAppSetting('app_min_diskspace')
    (_, free_space) = getDiskSpace()
    if free_space < minDiskSpace:
        _outOfDiskSpace = True
    else:
        _outOfDiskSpace = False
    
def _getDefaultIdleTimeFormat():
    return '%X'

def _getDefaultIdleDateFormat():
    return '%x'

def _getDefaultIdleText():
    return ''

def _getDefaultIdleSubText():
    return _('Please select option or present card.')

def _getDefaultButtonsIdleSubText():
    return _('Please select option or present card.')

def _getDefaultKeypadIdleSubText():
    return _('Please present card or enter ID.')

def _getDefaultKeypadIdlePromptColor():
    return '#CCCCCC'
    

def _regexTagReplace(match):
    tagType = match.group(1)
    tagParam = match.group(2)
    if (tagType == 'appcfg'):
        return getAppSetting(tagParam)
    elif (tagType == 'syscfg'):
        return cfg.get(tagParam)
    else:
        log.warn('Unsupported tag type (%s)' % tagType)
    return ''

def _replaceTags(text):
    return re.sub(r'\{(.*?):(.*?)\}', _regexTagReplace, text)


class _IdleMenuBase(dynButtons.DynButtonsMixin, idlePhoto.IdlePhotoMixin, bio.BioIdentifyMixin, screensaver.ScreensaverMixin, itg.Dialog):

    def __init__(self):
        super(_IdleMenuBase, self).__init__()
        _checkDiskSpace()
        
    def getDefaultLeftImage(self):
        """ Return default left image (e.g. bio reader or card reader) """
        if (self.bioIdentifyEnabled):
            return itg.getSmallBioReaderImage()
        if (self.hasSwipeActionDialog()):
            if (hasattr(itg, 'getReaderType') and itg.getReaderType() == 'none'):
                return None
            return itg.getSmallReaderImage()        
        return None
    
    def onCardRead(self, valid, reader, decoder, data):
        """Called when a card is read"""
        if not _outOfDiskSpace:
            self.stopScreensaver()
            self.runSwipeAction(valid, reader, decoder, data, self.getIdlePhoto())

    def onBioSyncRequest(self):
        """ Called when biometric template synchronisation is needed. """
        if not _outOfDiskSpace:
            self.stopScreensaver()
            bio.BioSyncDialog().run()

    def onBioScanComplete(self):
        """ Called when a finger was scanned (but not yet identified). """
        if not _outOfDiskSpace:
            itg.tickSound()
            self.stopScreensaver()

    def onBioIdentify(self, templID):
        """ Called when a biometric finger was identified. """
        if not _outOfDiskSpace:
            self.stopScreensaver()
            self.runBioAction(templID, self.getIdlePhoto())

    def onKeypadReq(self, data=''):
        """ Called on keypad input from idle view."""
        if not _outOfDiskSpace:
            self.stopScreensaver()            
            idlePhoto = self.getIdlePhoto()
            if (isinstance(self.getView(), itg.IdleMenuWithKeypadView)):
                emp = empIdentifyDlg.getIdentifiedEmpByKeypadID(data)
            else:
                dlg = empIdentifyDlg.Dialog(_('Please identify'), True, True, data)
                resID = dlg.run()
                if (resID not in (itg.ID_OK, itg.ID_KEYPAD)):
                    return
                emp = dlg.getEmployee()
            if (emp):
                if (idlePhoto):
                    emp.setVerifyPhoto(idlePhoto)
                self.runKeypadActionDialog(emp)

class IdleMenuDialog(_IdleMenuBase):
    """ Standard idle dialog."""
    
    def __init__(self, employee):
        super(IdleMenuDialog, self).__init__()
        self.loadProperties('idle.menu')
        btnAlignment = self.getMenuPropertyText('button.alignment')
        view = itg.IdleMenuView(btnAlignment)
        self.populateButtons(view, 'idle.menu', employee)
        if (self.hasSwipeActionDialog()):
            self.setReaderCb(self.onCardRead)
        self.bioSyncCheckEnable()
        if (self.hasBioActionDialog()):
            self.bioIdentifyEnable()
        if (self.hasKeypadActionDialog()):
            if (updateit.get_type() == 'IT5100'):
                view.addIcon('/tmp/theme/icons/keypad-icon.png', self.onKeypadReq)
            view.setKeypadRequestCb(self.onKeypadReq)
        info1 = self.getMenuPropertyText('idle.time', _getDefaultIdleTimeFormat()).replace(' %p', '<span size="xx-small"> %p</span>')
        info2 = self.getMenuPropertyText('idle.date', _getDefaultIdleDateFormat())
        info3 = self.getMenuPropertyText('idle.text', _getDefaultIdleText())
        if _outOfDiskSpace:
            info1 = '<span size="small">' + _("Out of disk space") + '</span>'
            info2 = '<span size="x-small">' + "Device %s" % cfg.get(cfg.CFG_PARTNO) + '</span>'
            info3 = '<span size="x-small">' + _("Contact support") + '</span>'
        (info1, info2, info3) = map(_replaceTags, (info1, info2, info3))
        view.setText(info1, info2, info3)
        # Please note: getDefaultLeftImage depends on populateButtons and bioIdentifyEnable
        self.setViewDetails(view)
        busyIndicator.setIconView(view)
        healthMonitor.getAppHealthMonitor().setIconView(view)
        self.enableScreensaver(getAppSetting('scrnsvr_timeout'), getAppSetting('scrnsvr_time_per_image'))
        if (self.getMenuPropertyBoolean('idle.photo', False)):
            self.enableIdlePhoto()
        self.addView(view)

    def setViewDetails(self, view):
        view.setDetails( self.getMenuPropertyImage('idle.image.left', self.getDefaultLeftImage()), 
                         self.getMenuPropertyText('idle.subtext', _getDefaultIdleSubText()),
                         self.getMenuPropertyImage('idle.image.right'))



class ButtonsIdleMenuDialog(_IdleMenuBase):
    """ Multiple buttons idle dialog."""
    
    def __init__(self, employee):
        super(ButtonsIdleMenuDialog, self).__init__()
        self.loadProperties('idle.buttons')
        rows = self.getMenuPropertyInteger('idle.rows', 4)
        cols = self.getMenuPropertyInteger('idle.cols', 2)
        btnAlignment = self.getMenuPropertyText('button.alignment')
        view = itg.IdleMenuWithGridButtonsView(rows, cols, btnAlignment)
        self.populateButtons(view, 'idle.buttons', employee)
        if (self.hasSwipeActionDialog()):
            self.setReaderCb(self.onCardRead)
        self.bioSyncCheckEnable()
        if (self.hasBioActionDialog()):
            self.bioIdentifyEnable()
        if (self.hasKeypadActionDialog()):
            if (updateit.get_type() == 'IT5100'):
                view.addIcon('/tmp/theme/icons/keypad-icon.png', self.onKeypadReq)
            view.setKeypadRequestCb(self.onKeypadReq)
        info1 = self.getMenuPropertyText('idle.time', _getDefaultIdleTimeFormat()).replace(' %p', '<span size="xx-small"> %p</span>')
        info2 = self.getMenuPropertyText('idle.date', _getDefaultIdleDateFormat())
        info3 = self.getMenuPropertyText('idle.text', _getDefaultIdleText())
        if _outOfDiskSpace:
            info1 = '<span size="small">' + _("Out of disk space") + '</span>'
            info2 = '<span size="x-small">' + "Device %s" % cfg.get(cfg.CFG_PARTNO) + '</span>'
            info3 = '<span size="x-small">' + _("Contact support") + '</span>'
        (info1, info2, info3) = map(_replaceTags, (info1, info2, info3))
        view.setText(info1, info2, info3)
        # Please note: getDefaultLeftImage depends on populateButtons and bioIdentifyEnable
        self.setViewDetails(view)
        busyIndicator.setIconView(view)
        healthMonitor.getAppHealthMonitor().setIconView(view)
        self.enableScreensaver(getAppSetting('scrnsvr_timeout'), getAppSetting('scrnsvr_time_per_image'))
        if (self.getMenuPropertyBoolean('idle.photo', False)):
            self.enableIdlePhoto()
        self.addView(view)

    def setViewDetails(self, view):
        view.setDetails( self.getMenuPropertyImage('idle.image.left', self.getDefaultLeftImage()), 
                         self.getMenuPropertyText('idle.subtext', _getDefaultButtonsIdleSubText()),
                         self.getMenuPropertyImage('idle.image.right'))


class KeypadIdleMenuDialog(_IdleMenuBase):
    """ Keypad idle dialog."""
    
    def __init__(self, employee):
        super(KeypadIdleMenuDialog, self).__init__()
        self.loadProperties('idle.keypad')
        view = itg.IdleMenuWithKeypadView(self.getMenuPropertyBoolean('idle.numpad.digitsonly', False),
                                          self.getMenuPropertyText('idle.numpad.prompt.text', ''),
                                          self.getMenuPropertyText('idle.numpad.prompt.color', _getDefaultKeypadIdlePromptColor()),
                                          self.getMenuPropertyBoolean('idle.numpad.password', False))
        view.setLogo( self.getMenuPropertyImage('idle.numpad.image'))
        self.populateButtons(view, 'idle.keypad', employee)
        if (self.hasSwipeActionDialog()):
            self.setReaderCb(self.onCardRead)
        self.bioSyncCheckEnable()
        if (self.hasBioActionDialog()):
            self.bioIdentifyEnable()
        if (self.hasKeypadActionDialog()):
            view.setKeypadRequestCb(self.onKeypadReq)
        info1 = self.getMenuPropertyText('idle.time', _getDefaultIdleTimeFormat()).replace(' %p', '<span size="xx-small"> %p</span>')
        info2 = self.getMenuPropertyText('idle.date', _getDefaultIdleDateFormat())
        info3 = self.getMenuPropertyText('idle.text', _getDefaultIdleText())
        if _outOfDiskSpace:
            info1 = '<span size="small">' + _("Out of disk space") + '</span>'
            info2 = '<span size="x-small">' + "Device %s" % cfg.get(cfg.CFG_PARTNO) + '</span>'
            info3 = '<span size="x-small">' + _("Contact support") + '</span>'
        (info1, info2, info3) = map(_replaceTags, (info1, info2, info3))
        view.setText(info1, info2, info3)
        # Please note: getDefaultLeftImage depends on populateButtons and bioIdentifyEnable    
        self.setViewDetails(view)
        busyIndicator.setIconView(view)
        healthMonitor.getAppHealthMonitor().setIconView(view)
        self.enableScreensaver(getAppSetting('scrnsvr_timeout'), getAppSetting('scrnsvr_time_per_image'))
        if (self.getMenuPropertyBoolean('idle.photo', False)):
            self.enableIdlePhoto()
        self.addView(view)

    def setViewDetails(self, view):    
        view.setDetails( self.getMenuPropertyImage('idle.image.left', self.getDefaultLeftImage()), 
                         self.getMenuPropertyText('idle.subtext', _getDefaultKeypadIdleSubText()),
                         self.getMenuPropertyImage('idle.image.right'))



def _mktable(tbl):
    maxColWidths = [ max([len(r[c]) for r in tbl]) for c in xrange(len(tbl[0])) ]
    rowSeparator = ' '.join(['='*s for s in maxColWidths])
    lines = [ rowSeparator]
    lines.append(' '.join([c.ljust(maxColWidths[i]) for i,c in enumerate(tbl[0])]))
    lines.append(rowSeparator)
    for r in tbl[1:]:
        lines.append(' '.join([c.ljust(maxColWidths[i]) for i,c in enumerate(r)]))
    lines.append(rowSeparator)
    return lines

class IdleMenuAction(dynButtons.Action):

    def getName(self):
        return 'idle.menu'
    
    def getButtonText(self, actionParam, employee, languages):
        return 'Idle'

    def getDialog(self, actionParam, employee, languages):
        return IdleMenuDialog(employee)

    def getHelp(self):
        tbl = ( ( 'Name',               'Type',     'Default',                      'Description' ),
                ( 'idle.time',          'Text',     _getDefaultIdleTimeFormat(),    'Time format (strftime compatible)'),
                ( 'idle.date',          'Text',     _getDefaultIdleDateFormat(),    'Date format (strftime compatible)'),
                ( 'idle.text',          'Text',     _getDefaultIdleText(),          'Title text'),
                ( 'idle.subtext',       'Text',     _getDefaultIdleSubText(),       'Text for details area, between left and right image (IT51 only)' ),
                ( 'idle.image.left',    'Image',    'Image of card or biometric reader', 'Left image for details area (IT51 only)' ),
                ( 'idle.image.right',   'Image',    '',                             'Right image for details area (IT51 only)' ),
                ( 'idle.photo',         'Boolean',  'False',                        'Enable/disable camera photo (lower right corner of screen)' ),
                ( 'button.alignment',   'Text',     '',                             'Alignment of button text' )
                )
        return """
        Idle menu. 
        
        The *idle.menu* menu allows four buttons and a swipe, biometric and keypad 
        action to be configured. An idle menu is often used as the main menu
        of an application.
        
        The following properties can be defined to customise the menu.
        
        .. tabularcolumns:: |l|l|p{0.25\\linewidth}|p{0.35\\linewidth}|
        
        """ + '\n        '.join(_mktable(tbl)) + """
        
        Example::
        
            <buttons startmenu="idle.menu">
                <menu name="idle.menu">
                
                    <properties>
                        <property name="idle.text">Super-Clock</property>
                        <property name="idle.subtext">
                            Please select option or present card.
                        </property>
                    </properties>
                
                    <button>
                        <pos>1</pos>
                        <action>
                            <emp.options.menu />
                        </action>
                    </button>
                    <swipe>
                        <action>
                            <emp.options.menu />
                        </action>
                    </swipe>                    
                </menu>
            </buttons>
                
        """


class ButtonsIdleMenuAction(dynButtons.Action):

    def getName(self):
        return 'idle.buttons'
    
    def getButtonText(self, actionParam, employee, languages):
        return 'Idle'

    def getDialog(self, actionParam, employee, languages):
        return ButtonsIdleMenuDialog(employee)

    def getHelp(self):
        tbl = ( ( 'Name',               'Type',     'Default',                      'Description' ),
                ( 'idle.rows',          'Number',   '4',                            'Number of rows of buttons' ),
                ( 'idle.cols',          'Number',   '2',                            'Number of columns of buttons' ),
                ( 'idle.time',          'Text',     _getDefaultIdleTimeFormat(),    'Time format (strftime compatible)'),
                ( 'idle.date',          'Text',     _getDefaultIdleDateFormat(),    'Date format (strftime compatible)'),
                ( 'idle.text',          'Text',     _getDefaultIdleText(),          'Title text'),
                ( 'idle.subtext',       'Text',     _getDefaultButtonsIdleSubText(), 'Text for details area, between left and right image (IT51 only)' ),
                ( 'idle.image.left',    'Image',    'Image of card or biometric reader', 'Left image for details area (IT51 only)' ),
                ( 'idle.image.right',   'Image',    '',                             'Right image for details area (IT51 only)' ),
                ( 'idle.photo',         'Boolean',  'False',                        'Enable/disable camera photo (lower right corner of screen)' ),
                ( 'button.alignment',   'Text',     '',                             'Alignment of button text' )
                )
        return """
        Idle menu with configurable buttons grid (IT51 only). 
        
        The *idle.buttons* menu allows multiple buttons and a swipe, biometric 
        and keypad action to be configured. An idle menu is often used as the 
        main menu of an application.
        
        The following properties can be defined to customise the menu.
        
        .. tabularcolumns:: |l|l|p{0.25\\linewidth}|p{0.35\\linewidth}|
        
        """ + '\n        '.join(_mktable(tbl)) + """

        Example::
        
            <buttons startmenu="idle.buttons">
                <menu name="idle.buttons">
                
                    <properties>
                        <property name="idle.text">Super-Clock</property>
                        <property name="idle.subtext">
                            Please select option or present card.
                        </property>
                    </properties>
                
                    <button>
                        <pos>1</pos>
                        <action>
                            <emp.options.menu />
                        </action>
                    </button>
                    <swipe>
                        <action>
                            <emp.options.menu />
                        </action>
                    </swipe>                    
                </menu>
            </buttons>
                
        """


class KeypadIdleMenuAction(dynButtons.Action):

    def getName(self):
        return 'idle.keypad'
    
    def getButtonText(self, actionParam, employee, languages):
        return 'Idle'

    def getDialog(self, actionParam, employee, languages):
        return KeypadIdleMenuDialog(employee)

    def getHelp(self):
        tbl = ( ( 'Name',                   'Type',     'Default',                      'Description' ),
                ( 'idle.time',              'Text',     _getDefaultIdleTimeFormat(),    'Time format (strftime compatible)'),
                ( 'idle.date',              'Text',     _getDefaultIdleDateFormat(),    'Date format (strftime compatible)'),
                ( 'idle.text',              'Text',     _getDefaultIdleText(),          'Title text'),
                ( 'idle.subtext',           'Text',     _getDefaultKeypadIdleSubText(), 'Text for details area, between left and right image (IT51 only)' ),
                ( 'idle.image.left',        'Image',    'Image of card or biometric reader', 'Left image for details area (IT51 only)' ),
                ( 'idle.image.right',       'Image',    '',                             'Right image for details area (IT51 only)' ),
                ( 'idle.numpad.digitsonly', 'Boolean',  'False',                        'Hide star and hash keypad buttons' ),
                ( 'idle.numpad.password',   'Boolean',  'False',                        'Conceal entered text' ),
                ( 'idle.numpad.prompt.text','Text',     '',                             'Prompt shown in keypad input when no data is entered' ),
                ( 'idle.numpad.prompt.color','Text',    _getDefaultKeypadIdlePromptColor(), 'Colour for keypad input text' ),
                ( 'idle.numpad.image',      'Image',    '',                             'Image shown below keypad' ),
                ( 'idle.photo',             'Boolean',  'False',                        'Enable/disable camera photo (lower right corner of screen)' ),
                ( 'button.alignment',       'Text',     '',                             'Alignment of button text' )
                )
        return """
        Idle menu with built-in keypad. 
        
        The *idle.keypad* menu has no buttons but allows for a swipe, 
        biometric and keypad action to be configured. The keypad data 
        can be entered on the menu itself (e.g. without going to the
        identification dialog).
        An idle menu is often used as the main menu of an application.

        The following properties can be defined to customise the menu.
        
        .. tabularcolumns:: |l|l|p{0.25\\linewidth}|p{0.35\\linewidth}|
        
        """ + '\n        '.join(_mktable(tbl)) + """

        Example::
        
            <buttons startmenu="idle.keypad">
                <menu name="idle.keypad">
                    <properties>
                        <property name="idle.text">Super-Clock</property>
                        <property name="idle.subtext">
                            Please present card.
                        </property>
                        <property name="numpad.text">Enter Code</property>
                    </properties>
                    <swipe>
                        <action>
                            <emp.options.menu />
                        </action>
                    </swipe>                    
                    <keypad>
                        <action>
                            <emp.options.menu />
                        </action>
                    </keypad>                    
                </menu>
            </buttons>
                
        """


def loadPlugin():
    dynButtons.registerAction(IdleMenuAction())
    dynButtons.registerAction(ButtonsIdleMenuAction())    
    dynButtons.registerAction(KeypadIdleMenuAction())


def getSettings():
    sectionName = 'Screensaver'
    sectionComment = 'These are the settings for the Screensaver feature.'
    screensaverSection = SettingsSection(sectionName, sectionComment)
    TextSetting(screensaverSection,
            name     = 'scrnsvr_mediaurl', 
            label    = 'Media URL',
            data     = '',
            comment  = ('URL of ZIP file containing the screensaver images (e.g. http://host/screensaver.zip). '
                        'The URL can also be used to point to a directory with images on a USB memory device '
                        '(e.g. usb://IT-Screensaver). Instead of images, the ZIP file or directory may also '
                        'include (exactly) one MPEG4 video file (.mp4).'))
    NumberSetting(screensaverSection,
            name     = 'scrnsvr_timeout', 
            label    = 'Time', 
            data     = '300', 
            minValue = None, 
            maxValue = None, 
            units    = 'sec', 
            comment  = ('Time in seconds of inactivity before starting screensaver.'))
    NumberSetting(screensaverSection,
            name     = 'scrnsvr_time_per_image', 
            label    = 'Time per Image', 
            data     = '30', 
            units    = 'sec', 
            comment  = ('Time in seconds a single image is shown in screensaver.'))
    return [screensaverSection,]


class IdleMenuTouchDialog(_IdleMenuBase):
    
    def __init__(self, employee):
        super(IdleMenuTouchDialog, self).__init__()
        useTouchView = False
        self.loadProperties('idle.menu')
        if hasattr(itg, "IdleMenuTouchView"):
            view = itg.IdleMenuTouchView()
            useTouchView = True
        else:
            view = itg.IdleMenuView()
            
        self.populateButtons(view, 'idle.menu', employee)
        if (self.hasSwipeActionDialog()):
            self.setReaderCb(self.onCardRead)
        self.bioSyncCheckEnable()
        if (self.hasBioActionDialog()):
            self.bioIdentifyEnable()
        if (self.hasKeypadActionDialog()):
            if (updateit.get_type() == 'IT5100'):
                view.addIcon('/tmp/theme/icons/default/keypad-icon.png', self.onKeypadReq)
            view.setKeypadRequestCb(self.onKeypadReq)
            
        if useTouchView and not _outOfDiskSpace:
            view.setTopItems([itg.ImageItem('/tmp/theme/icons/default/idle-smiley.png')])

        self.updateTimeDisplay(view, True)
        
        if useTouchView:
            if not _outOfDiskSpace:
                if self.hasSwipeActionDialog() or self.hasBioActionDialog() or self.hasKeypadActionDialog():
                    view.setBottomItems([
                        itg.ImageItem('/tmp/theme/images/idle-pointer.png'),
                        itg.TextItem(self.getMenuPropertyText('idle.subtext', 'Swipe badge or touch screen to continue'))
                        ])
                else:
                    view.setBottomItems([
                        itg.TextItem(self.getMenuPropertyText('idle.subtext', 'No XML loaded'))
                        ])
            else:
                view.setBottomItems([
                    itg.ImageItem('/tmp/theme/images/idle-pointer.png'),
                    # itg.TextItem(_('Touch screen to restart'))
                    ])
        
        busyIndicator.setIconView(view)
        # healthMonitor.getAppHealthMonitor().setIconView(view)
        self.enableScreensaver(getAppSetting('scrnsvr_timeout'), getAppSetting('scrnsvr_time_per_image'))
        if (self.getMenuPropertyBoolean('idle.photo', False)):
            self.enableIdlePhoto()
        self.addView(view)

    def updateTimeDisplay(self, view=None, forceUpdate=False):
        if self.isShown() or forceUpdate:
            currentTime = datetime.now()
            
            if (currentTime.hour >= 0 and currentTime.hour < 12):
                info1 = _('Good morning')
            elif (currentTime.hour >= 12 and currentTime.hour < 18):
                info1 = _('Good afternoon')
            else:
                info1 = _('Good evening')
    
            info2 = self.getMenuPropertyText('idle.date', _getDefaultIdleDateFormat())
            info3 = self.getMenuPropertyText('idle.text', _getDefaultIdleText())
            
            if _outOfDiskSpace:
                info1 = '<span size="small">' + _("Out of disk space") + '</span>'
                info2 = '<span size="x-small">' + "Device %s" % cfg.get(cfg.CFG_PARTNO) + '</span>'
                info3 = '<span size="x-small">' + _("Contact support") + '</span>'
                if view is None:
                    view = self.getView()
                if view is not None:
                    view.setTouchCb(self.onTouch)
    
            # On IT11, decrease the font-size of the greeting text, otherwise it won't fit
            if (updateit.get_type() == 'IT1100'):
                info1 = '<span size="small">' + info1 + '</span>'
    
            if view is None:
                view = self.getView()
        
            if view is not None:                                
                view.setText(info1, info2, info3)

        # Update the display every minute
        itg.runIn(60, self.updateTimeDisplay)

    def onShow(self):
        super(IdleMenuTouchDialog, self).onShow()
        # Allow time for the language to switch back to the default, then 
        # update the idle-screen text
        itg.runIn(1, self.updateTimeDisplay)

    def onEmployeeMenu(self):
        if not _outOfDiskSpace:
            dlg = dynButtons.getActionDialogByName('emp.options.menu')
            self.runDialog(dlg)        
    
    def onTouch(self, _):
        resID = itg.msgbox(itg.MB_OK_CANCEL, 'Restart application?')
        if (resID == itg.ID_OK):
            restartManager.restartFromUI(timeout=0)
        