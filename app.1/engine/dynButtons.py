# -*- coding: utf-8 -*-
#
# Copyright 2010 Grosvenor Technology
#

import xml.etree.cElementTree
import itg
import log
import os
import led
import base64
import updateit
from applib.utils import nls, restartManager, resourceManager
from applib.db.tblSettings import getAppSetting
import empVerifyDlg
import empIdentifyDlg
from engine import identificationRequestQueue
from applib.gui import msg

_actions = { }
_genericMenus = { }
_btnActions = { 'btn.ok'    : (itg.ID_OK, lambda: _('OK')),
                'btn.back'  : (itg.ID_BACK, lambda: _('Back')),
                'btn.cancel': (itg.ID_CANCEL, lambda: _('Cancel')),
                }

_btnOptions = ( 'invokeCancel', 
                'invokeTimeout', 
                'returnAfter', 
                'keypadView', 
                'noKeypadOption',
                'preventRestart', 
                'needEmployee', 
                'switchEmployee',
                'dialogTimeout'
                )

_appButtons = None

def getAppButtons():
    global _appButtons
    if (_appButtons == None):
        _appButtons = XMLButtons()
    return _appButtons

def hasRequiredRole(availableList, requiredRoles):
    """Returns True if one of the roles in the list of availableRoles is 
    included in the comma-separated list of requiredRoles."""

    if requiredRoles is None:
        return True
    
    requiredList =  [role.strip() for role in requiredRoles.split(',')]
    for role in availableList:
        if role in requiredList:
            return True    
    return False
   
#
# Action class and functions
#
#

class Action(object):
    """ Action base class """
    
    def getButtonIcon(self, actionParam, employee, languages):
        return None

    def isEmployeeRequired(self, actionParam):
        return False
    
    def isVisible(self, actionParam, employee, languages):
        return True


def registerAction(action):
    """ Register new button action."""
    log.dbg('New action %s' % action.getName())
    for reqMethod in ('getName', 'getButtonText', 'getDialog'):
        if (not hasattr(action, reqMethod)):
            log.err('Action %s has no method "%s"' % (action.__class__.__name__, reqMethod))
            return
    for expMethod in ('isEmployeeRequired', ):
        if (not hasattr(action, expMethod)):
            log.warn('Action %s has no method "%s"' % (action.__class__.__name__, expMethod))
    for obsoleteMethod in ('getEmpDialog', 'isLocalSupervisorAllowed'):
        if (hasattr(action, obsoleteMethod)):
            log.warn('Action %s has obsolete method "%s"' % (action.__class__.__name__, obsoleteMethod))

    _actions[action.getName()] = action

def getAllActions():
    """ Returns the names of all actions."""
    return _actions.keys() + _btnActions.keys()

def getActionByName(name):
    """ Return action by name. """
    if (name in _actions):
        return _actions[name]
    return None

def getActionDialogByName(actionName, actionParam=None, employee=None):
    """ Get dialog to run action"""
    if (actionName not in _actions):
        return None
    action = _actions[actionName]
    return _ActionDialog(action, actionParam, employee)

def hasAction(actionName):
    """ Returns **True** if action exists. """
    return (actionName in _actions)


#
# Generic menu related stuff
#
#
def registerMenu(menuName, menuDialogClass, menuTitle='', menuHelp=''): 
    """ Register new generic menu. """
    if (not menuName.startswith('menu.') or not menuName.endswith('')):
        raise Exception('Generic menu names must start with menu.')
    log.dbg('New generic menu %s' % menuName)
    _genericMenus[menuName] = (menuDialogClass, menuTitle, menuHelp)
    if ('go.to.menu' not in _actions.keys()):
        registerAction(_MenuAction())

def getGenericMenuDialogByName(menuName):
    """ Find and return generic dialog class. """
    for menuPrefix, (menuDialogClass,_,_) in _genericMenus.iteritems():
        if (menuName.startswith(menuPrefix)):
            return menuDialogClass
    return None


#
# Identification + Verification dialogs
#
#

class IdentifyVerifyDialog(itg.PseudoDialog):
    """ Pseudo dialog running through identification and verification."""
    
    def __init__(self, empPhoto=None, useKeypadView=False, showKeypadOption=True, interceptLocalSupervisor=True, allowAutoEnrol=True):
        super(IdentifyVerifyDialog, self).__init__()
        self.__verifyPhoto = empPhoto
        self.__useKeypadView = useKeypadView
        self.__showKeypadOption = showKeypadOption
        self.__interceptLocalSupervisor = interceptLocalSupervisor
        self.__allowAutoEnrol = allowAutoEnrol
        self.__identifyTitle = _('Please identify')
        
    def setIdentifyTitle(self, title):
        self.__identifyTitle = title
        
    def run(self):
        log.dbg("IdentifyVerifyDialog.run()")
        self.__emp = None
        # Identify User
        identifyDlg = empIdentifyDlg.Dialog(self.__identifyTitle, self.__useKeypadView, self.__showKeypadOption)
        identifyDlg.allowAutoEnrol(self.__allowAutoEnrol)
        resID = identifyDlg.run()
        if (resID != itg.ID_OK and resID != itg.ID_KEYPAD):
            return itg.ID_CANCEL
        emp = identifyDlg.getEmployee()
        if (emp == None):
            return itg.ID_CANCEL
        # Check for consent
        if (not emp.isLocalSupervisor) and (not emp.checkConsent()):
            return itg.ID_CANCEL
        # Apply photo if there
        if (self.__verifyPhoto):
            emp.setVerifyPhoto(self.__verifyPhoto)
        # Verify User
        with emp.Language():
            verifyDlg = empVerifyDlg.Dialog(emp)
            verifyDlg.run()
            if (verifyDlg.verified()):
                if (emp.isLocalSupervisor() and self.__interceptLocalSupervisor):
                    self.__runSupervisorMenu(emp)
                    return itg.ID_CANCEL
                if (hasattr(emp, 'validate')):
                    notValidReason = emp.validate()
                    if (notValidReason):
                        msg.failMsg(notValidReason)
                        return itg.ID_CANCEL
                self.__emp = emp
                return itg.ID_OK
            return itg.ID_CANCEL

    def __runSupervisorMenu(self, emp):
        dlg = getActionDialogByName('supervisor.menu', employee=emp)
        if (dlg != None):
            dlg.run()
    
    def getEmployee(self):
        return self.__emp



class _ActionParam(object):
    
    def __init__(self, actionParam):
        self.__ap = actionParam 
        
    def getParam(self, name, default=None):
        p = self.__ap.find(name)
        if (p==None):
            return default
        return p.text

    def getText(self, name, languages, default=None):
        p = self.__ap.find(name)
        return _getText(p, languages, default)
    
    def getMultiLanguageText(self, name):
        p = self.__ap.find(name)
        return _getMultiLanguageText(p)
    
    def getInteger(self, name, default=0):
        p = self.__ap.find(name)
        return _getInteger(p, default)
    
    def getFloat(self, name, default=0):
        p = self.__ap.find(name)
        return _getFloat(p, default)
    
    def getBoolean(self, name, default=False):
        p = self.__ap.find(name)
        return _getBoolean(p, default)

    def getIcon(self, name, default=None):
        p = self.__ap.find(name)
        return _getImage(p, 'media/icons', default)

    def getImage(self, name, default=None):
        p = self.__ap.find(name)
        return _getImage(p, 'media/images', default)

    def getSound(self, name, languages, default=None):
        p = self.__ap.find(name)
        return _getSound(p, languages, default)
    
    def getList(self, path):
        return map(lambda e: e.text, self.__ap.findall(path))

    def getXMLElement(self, name=None):
        if (name == None):
            return self.__ap
        return self.__ap.find(name)



class _ActionDialog(itg.PseudoDialog):
    
    def __init__(self, action, actionParam, employee=None, reqRole=None, empPhoto=None, btnOptions=None):
        super(_ActionDialog, self).__init__()
        self.__action = action
        self.__actionParam = actionParam
        self.__emp = employee
        self.__reqRole = reqRole
        self.__empPhoto = empPhoto
        self.__options = _ButtonOptions() if (btnOptions==None) else btnOptions 
        self.__returnTarget = None
    
    def getReturnTarget(self):
        return self.__returnTarget
    
    def setReturnTarget(self, target):
        self.__returnTarget = target
    
    def run(self):
        log.dbg("_ActionDialog.run()")
        emp = self.__emp
        resID = itg.ID_UNKNOWN
        needEmp = (self.__action.isEmployeeRequired(self.__actionParam) 
                   or self.__reqRole 
                   or self.__options.hasOption('needEmployee') 
                   or self.__options.hasOption('switchEmployee'))
        # identify employee if required
        if (emp == None and needEmp):
            useKeypadView = self.__options.hasOption('keypadView')
            showKeypadOption = not self.__options.hasOption('noKeypadOption')
            empDlg = IdentifyVerifyDialog(self.__empPhoto, useKeypadView, showKeypadOption)
            resID = empDlg.run()
            if (resID not in (itg.ID_OK, itg.ID_KEYPAD, itg.ID_NEXT)):
                return resID
            emp = empDlg.getEmployee()
            if (emp == None):
                return itg.ID_CANCEL
        # check role
        if (self.__reqRole and (emp == None or not hasRequiredRole(emp.getRoles(), self.__reqRole))):
            itg.msgbox(itg.MB_OK, _('Permission denied!'))
            return itg.ID_BACK
        # switch employee?
        if (self.__options.hasOption('switchEmployee')):
            dlg = empIdentifyDlg.Dialog(_('Identify employee'), useKeypadView=True)
            dlg.setManager(emp)
            res = dlg.run()
            if (res != itg.ID_OK and res != itg.ID_KEYPAD):
                return res
            newEmp = dlg.getEmployee()
            if (newEmp == None):
                return itg.ID_CANCEL
            if (newEmp.isLocalSupervisor()):
                itg.msgbox(itg.MB_OK, _('Local supervisor not allowed.'))
                return itg.ID_CANCEL
            newEmp.setManager(emp)
            emp = newEmp
        languages = emp.getLanguages() if emp else (nls.getCurrentLanguage(),'en')
        # run action dialog, switch language if user has changed
        with emp.Language() if (emp and emp != self.__emp) else DummyLock():
            with _ChangedDefaultDialogTimeout(self.__options.getIntOption('dialogTimeout')):
                dlg = self.__action.getDialog(self.__actionParam, emp, languages)
                if (dlg != None):
                    resID = dlg.run()
        self.setResultID(resID)
        # remember return target from actual dialog
        if (hasattr(dlg, 'getReturnTarget')):
            self.setReturnTarget(dlg.getReturnTarget())
        return resID
        

class DynButtonsMixin(object):

    def populateButtons(self, view, menuName, employee=None, buttonsPerPage=None, defaultXML=None):
        """ Add buttons to view. """
        self.__menuName = menuName
        self.__returnTarget = None
        self.__buttonAutoPositioning = None
        self.__buttonAutoPositions = {}
        self.__buttonData = {}
        self.__thisTerminal = updateit.get_type().lower()[:4]
        populatedButtons = 0
        buttons = getAppButtons()
        menu    = buttons.getMenu(menuName)
        if (menu == None and defaultXML != None):
            menu = self.__getMenuFromXML(menuName, defaultXML)
        if (menu == None):
            log.warn('No buttons for menu %s' % menuName)
            return 0
        self.__menuNameAliases = [ e.strip() for e in menu.get('alias', '').split(',') ]
        for buttonTag in menu:
            try:
                if (buttonTag.tag not in ('button', 'swipe', 'bio', 'keypad', 'touch')):
                    continue
                button = buttons.getButtonConfig(buttonTag)
                populatedButtons += self.__populateButton(button, view, buttonsPerPage, employee)
            except Exception as e:
                log.err('Error placing button (%s)' % e)
        return populatedButtons
    
    def __getMenuFromXML(self, menuName, xmlData):
        try:
            menu = xml.etree.cElementTree.fromstring(xmlData)
            if (menu.tag != 'menu'):
                log.warn('Menu %s default configuration does not start with "menu" tag!' % menuName)
                return None
            return menu
        except Exception as e:
            log.warn('Error loading default XML for menu %s: %s' % (menuName, e))
        return None
                    
    def __populateButton(self, button, view, buttonsPerPage, employee):                
        # hide buttons for employees without required roles
        if (employee and not button.requiredRoleFound(employee.getRoles())):
            return 0
        # hide button if not required terminal
        if (not button.requiredTerminalFound(self.__thisTerminal)):
            return 0
        actionName = button.getActionConfig().getName()
        actionParam = button.getActionConfig().getParam()
        # handle swipe, bio and keypad actions
        if button.isTouchAction() and not itg.isIT11():
            if (actionName in _actions):
                self.__buttonData['touch'] = (_actions[actionName], button, None)
                view.setTouchCb(self.__onTouch)                
            else:
                raise Exception('unknown touch action (%s)' % (actionName,))
        elif (button.isSwipeAction()):
            if (actionName in _actions):
                self.__buttonData[button.getSwipeAction()] = (_actions[actionName], button, None)                
            else:
                raise Exception('unknown swipe action (%s)' % (actionName,))
        else:
            # handle position and label
            languages   = employee.getLanguages() if employee else (nls.getCurrentLanguage(),'en')                    
            buttonText  = button.getLabel(languages)
            buttonColor = button.getLabelColor()
            buttonIcon  = button.getIcon()
            # place button
            if (actionName in _actions):
                action = _actions[actionName]
                if (not action.isVisible(actionParam, employee, languages)):
                    return 0
                if (buttonText == None):
                    buttonText = action.getButtonText(actionParam, employee, languages)
                if (buttonIcon == None):
                    buttonIcon = action.getButtonIcon(actionParam, employee, languages)
                if (not buttonText and not buttonIcon):    
                    raise Exception('button has no text or icon')
                pos = self.__calculateButtonPos(button.getPos(), button.getPage(), buttonsPerPage)
                if (pos in self.__buttonData):
                    log.warn('Overwriting button at position %d' % pos)
                self.__buttonData[pos] = (action, button, employee)
                self.__addButtonOrIcon(view, pos, buttonText, pos, self.__onButtonPress, buttonIcon, buttonColor)
            elif (actionName in _btnActions):
                (btnID, textCb) = _btnActions[actionName]
                if (buttonText == None):
                    buttonText = textCb()
                pos = self.__calculateButtonPos(button.getPos(), button.getPage(), buttonsPerPage)
                self.__addButtonOrIcon(view, pos, buttonText, btnID, self.quit, buttonIcon, buttonColor)                
            elif (actionName.startswith('menu.grid.') or actionName.startswith('menu.multigrid.') or actionName.startswith('menu.icon.')):
                if (not buttonText and not buttonIcon):
                    raise Exception('menu button has no text or icon')
                pos = self.__calculateButtonPos(button.getPos(), button.getPage(), buttonsPerPage)
                if (pos in self.__buttonData):
                    log.warn('Overwriting button at position %d' % pos)
                self.__buttonData[pos] = (_MenuAction(actionName), button, employee)                
                self.__addButtonOrIcon(view, pos, buttonText, pos, self.__onButtonPress, buttonIcon, buttonColor)
            else:
                raise Exception('unknown action (%s)' % actionName)
        return 1

    def __calculateButtonPos(self, pos, page, buttonsPerPage):
        if (self.__buttonAutoPositioning==None):
            self.__buttonAutoPositioning = (pos==None)
        if (self.__buttonAutoPositioning):
            if (pos != None):
                log.warn('Button position specified in auto positioning mode!')
            return self._getAutoButtonPos(pos, page, buttonsPerPage)
        if (pos == None):
            raise Exception('position not specified')
        elif (pos > 0):
            pos -= 1
        if (page > 1):
            if (buttonsPerPage == None):
                raise Exception('view does not support multiple pages')
            else:
                pos += (page-1) * buttonsPerPage
        return pos

    def _getAutoButtonPos(self, pos, page, buttonsPerPage):
        pos = self.__buttonAutoPositions[page] if (page in self.__buttonAutoPositions) else 0
        self.__buttonAutoPositions[page] = pos + 1
        if (page > 1):
            if (buttonsPerPage == None):
                raise Exception('view does not support multiple pages')
            else:
                pos += (page-1) * buttonsPerPage
        return pos
            
    def __addButtonOrIcon(self, view, pos, text, btnID, cb, icon, color):
        if (hasattr(view, 'setButton')):
            view.setButton(pos, text, btnID, cb, icon, color)
        elif (hasattr(view, 'setIcon')):
            (row,col) = divmod(pos, view.getNumColumns())
            view.setIcon(row, col, icon, text, cb, btnID)
        else:
            raise Exception('Unable to add button')

    def __processIdentifyRequests(self):
        if (not self.hasSwipeActionDialog() and not self.hasBioActionDialog()):
            if (self.getResultID() == itg.ID_UNKNOWN):
                # dialog still running but no swipe actions?
                # clear identification request queue!
                identificationRequestQueue.clear()
            return
        for readerInput in iter(identificationRequestQueue.getNext, None):
            if (readerInput.isCardReaderRequest() and self.hasSwipeActionDialog()):
                (valid, reader, decoder, data) = readerInput.getRequestData()
                emp = empIdentifyDlg.getIdentifiedEmpByCardRead(valid, reader, decoder, data)
                if (emp):
                    emp.setVerifyPhoto(readerInput.getEmpPicture())
                    self.runSwipeActionDialog(emp)
            elif (readerInput.isBiometricRequest() and self.hasBioActionDialog()):
                templID = readerInput.getRequestData()
                emp = empIdentifyDlg.getIdentifiedEmpByBiometric(templID)
                if (emp):
                    (action, _, _) = self.__buttonData["bio"]
                    # Check for consent
                    if emp.checkConsent():
                        emp.setVerifyPhoto(readerInput.getEmpPicture())
                        self.runBioActionDialog(emp)
        
    def __onButtonPress(self, btnID):
        """ Executes button action. """
        if (btnID not in self.__buttonData):
            raise Exception('DynButton without data (btnID=%s!' % btnID)
        if (hasattr(self, 'getIdlePhoto')):
            empPhoto = self.getIdlePhoto()
        else:
            empPhoto = None
        (action, button, emp) = self.__buttonData[btnID]
        self.__startAction(action, button, emp, empPhoto)
        self.__processIdentifyRequests()
    
    def __onTouch(self, enteredNumber):
        """ Executes button action. """
        (action, button, emp) = self.__buttonData['touch']
        self.__startAction(action, button, emp, None)
        self.__processIdentifyRequests()
        
    def _runSwipeKeypadOrBioActionDialog(self, employee, actionType):
        """ Runs swipe, keypad or bio action dialog. Also executes verification. """
        if (employee == None):
            return
        if (actionType not in self.__buttonData):
            itg.msgbox(itg.MB_OK, _('Action (%s) not defined!') % actionType)
            return
        with employee.Language():
            dlg = empVerifyDlg.Dialog(employee)
            dlg.run()
            if (dlg.verified()):
                if (employee.isLocalSupervisor()):
                    dlg = getActionDialogByName('supervisor.menu', employee=employee)
                    if (dlg != None):
                        dlg.run()
                        return
                elif (hasattr(employee, 'validate')):
                    notValidReason = employee.validate()
                    if (notValidReason):
                        msg.failMsg(notValidReason)
                        return
                (action, button, _emp) = self.__buttonData[actionType]
                self.__startAction(action, button, employee, None)

    def __startAction(self, action, button, emp, empPhoto):
        """ Run action dialog, which will optionally identify+verify and run
        actual dialog of action. """
        restartLock = restartManager.PreventRestartLock() if (button.hasOption('preventRestart')) else DummyLock()
        with restartLock:
            with button.getActionConfig().getLanguage():
                dlg = _ActionDialog(action, button.getActionConfig().getParam(), emp, button.getReqRole(), empPhoto, button.getOptions())
                resID = dlg.run()
                # go back to configured target
                returnTarget = dlg.getReturnTarget()
                if (returnTarget):
                    if ((returnTarget == self.__menuName) or (returnTarget in self.__menuNameAliases)):
                        return # we arrived
                    self.setReturnTarget(returnTarget)
                    self.quit(itg.ID_OK)
                    return
                # handle old button options
                if (button.hasOption('returnAfter')):
                    self.cancel()
                    return
                eh = button.getExecutedHandler()
                if (resID == itg.ID_CANCEL and eh.invokeCancel()):
                    self.cancel()
                elif (resID == itg.ID_BACK and eh.invokeBack()):
                    self.back()
                elif (resID == itg.ID_TIMEOUT and eh.invokeTimeout()):
                    self.timeout()
                else:
                    target = eh.getTargetForResultID(resID)
                    if (target != None):
                        log.dbg('Returning to %s' % target)
                        if ((target == self.__menuName) or (target in self.__menuNameAliases)):
                            return # already arrived
                        self.setReturnTarget(target)
                        self.quit(itg.ID_OK)

    def getReturnTarget(self):
        return self.__returnTarget
        
    def setReturnTarget(self, target):
        self.__returnTarget = target
     
    def runSwipeActionDialog(self, employee):
        """ Run swipe action dialog. """
        self._runSwipeKeypadOrBioActionDialog(employee, 'swipe')

    def hasSwipeActionDialog(self):
        """ Return **True** if a swipe action is defined. """
        return 'swipe' in self.__buttonData

    def runBioActionDialog(self, employee):
        """ Run bio action dialog. """
        self._runSwipeKeypadOrBioActionDialog(employee, 'bio')

    def hasBioActionDialog(self):
        """ Return **True** if a bio action is defined. """ 
        return 'bio' in self.__buttonData

    def runKeypadActionDialog(self, employee):
        """ Run keypad action dialog. """
        self._runSwipeKeypadOrBioActionDialog(employee, 'keypad')
        self.__processIdentifyRequests()

    def hasKeypadActionDialog(self):
        """ Return **True** if a keypad action is defined. """
        return 'keypad' in self.__buttonData

    def runSwipeAction(self, valid, reader, decoder, data, empPhoto=None):
        """ Run swipe action with card read data. """
        identificationRequestQueue.addCardReaderRequest(valid, reader, decoder, data, empPhoto)
        self.__processIdentifyRequests()

    def runBioAction(self, templID, empPhoto=None):
        """ Run bio action with template ID. """
        if (templID == None and 'bio' in self.__buttonData):
            itg.failureSound()
            led.on(led.LED_ALL | led.LED_STATUS, led.RED, 2*1000)
            self.__onButtonPress('bio')
        else:
            identificationRequestQueue.addBiometricRequest(templID, empPhoto)
            self.__processIdentifyRequests()


    #
    # Properties
    #
    
    def loadProperties(self, menuName):
        self.__menuProperties = None
        buttons = getAppButtons()
        menu = buttons.getMenu(menuName)
        if (menu == None):
            log.warn('No menu "%s" found for properties' % menuName)
        else:
            self.__menuProperties = buttons.getMenuProperties(menu)
        
    def getMenuPropertyText(self, name, default=None):
        """ Return menu property. Please note that 
            loadMenuProperties must be called first. 
        """
        return getAppButtons().getMenuPropertyText(self.__menuProperties, name, default)

    def getMenuPropertyInteger(self, name, default=None):
        """ Return menu property. Please note that 
            loadMenuProperties must be called first. 
        """
        return getAppButtons().getMenuPropertyInteger(self.__menuProperties, name, default)

    def getMenuPropertyBoolean(self, name, default=None):
        """ Return menu property. Please note that 
            loadMenuProperties must be called first. 
        """
        return getAppButtons().getMenuPropertyBoolean(self.__menuProperties, name, default)

    def getMenuPropertyImage(self, name, default=None):
        """ Return menu property image. Please note that 
            loadMenuProperties must be called first. 
        """
        return getAppButtons().getMenuPropertyImage(self.__menuProperties, name, default)

    def getMenuPropertyIcon(self, name, default=None):
        """ Return menu property icon. Please note that 
            loadMenuProperties must be called first. 
        """
        return getAppButtons().getMenuPropertyIcon(self.__menuProperties, name, default)

class DynListMixin(object):

    def populateList(self, view, menuName, employee=None, defaultXML=None):
        """ Add items to view. """
        self.__menuName = menuName
        self.__returnTarget = None
        self.__itemData = {}
        self.__thisTerminal = updateit.get_type().lower()[:4]
        view.setCancelButton(_('Cancel'), self.cancel)
        view.setOkButton(_('OK'),  cb=self.__onOK)        
        itemCount = 0
        items = getAppButtons()
        menu = items.getMenu(menuName)
        if (menu == None and defaultXML != None):
            menu = self.__getMenuFromXML(menuName, defaultXML)
        if (menu == None):
            log.warn('No items for menu %s' % menuName)
            return 0
        self.__menuNameAliases = [ e.strip() for e in menu.get('alias', '').split(',') ]
        for itemTag in menu:
            try:
                if (itemTag.tag == 'title'):
                    languages = employee.getLanguages() if employee else (nls.getCurrentLanguage(),'en')                    
                    view.setTitle(_getText(itemTag, languages, ''))
                    continue
                elif (itemTag.tag not in ('item', 'swipe', 'bio', 'keypad')):
                    continue
                item = items.getButtonConfig(itemTag)
                itemCount += self.__populateItem(item, view, employee)
            except Exception as e:
                log.err('Error adding item (%s)' % e)
        return itemCount
    
    def __populateItem(self, item, view, employee):                
        # hide buttons for employees without required roles
        if (employee and not item.requiredRoleFound(employee.getRoles())):
            return 0
        # hide button if not required terminal
        if (not item.requiredTerminalFound(self.__thisTerminal)):
            return 0
        actionName = item.getActionConfig().getName()
        actionParam = item.getActionConfig().getParam()
        # handle position and label
        languages   = employee.getLanguages() if employee else (nls.getCurrentLanguage(),'en')                    
        itemText  = item.getLabel(languages)
        itemID = len(self.__itemData)
        if item.isHidden():
            return 0
        # place button
        if (actionName in _actions):
            action = _actions[actionName]
            if (not action.isVisible(actionParam, employee, languages)):
                return 0
            if (itemText == None):
                itemText = action.getButtonText(actionParam, employee, languages)
            if (not itemText):    
                raise Exception('item has no text')
            self.__itemData[itemID] = (action, item, employee)
            self.__addItem(view, itemText)
        elif (actionName in _btnActions):
            (itemID, textCb) = _btnActions[actionName]
            if (itemText == None):
                itemText = textCb()
            self.__itemData[itemID] = (action, item, employee)
            self.__addItem(view, itemText)                
        elif (actionName.startswith('menu.list.')):
            if (not itemText):
                raise Exception('menu item has no text')
            self.__itemData[itemID] = (_MenuAction(actionName), item, employee)
            self.__addItem(view, itemText)
        else:
            raise Exception('unknown action (%s)' % actionName)
        return 1

    def __getMenuFromXML(self, menuName, xmlData):
        try:
            menu = xml.etree.cElementTree.fromstring(xmlData)
            if (menu.tag != 'menu'):
                log.warn('Menu %s default configuration does not start with "menu" tag!' % menuName)
                return None
            return menu
        except Exception as e:
            log.warn('Error loading default XML for menu %s: %s' % (menuName, e))
        return None

    def __addItem(self, view, text):
        view.appendRow(text)

    def __processIdentifyRequests(self):
        if (not self.hasSwipeActionDialog() and not self.hasBioActionDialog()):
            if (self.getResultID() == itg.ID_UNKNOWN):
                # dialog still running but no swipe actions?
                # clear identification request queue!
                identificationRequestQueue.clear()
            return
        for readerInput in iter(identificationRequestQueue.getNext, None):
            if (readerInput.isCardReaderRequest() and self.hasSwipeActionDialog()):
                (valid, reader, decoder, data) = readerInput.getRequestData()
                emp = empIdentifyDlg.getIdentifiedEmpByCardRead(valid, reader, decoder, data)
                if (emp):
                    emp.setVerifyPhoto(readerInput.getEmpPicture())
                    self.runSwipeActionDialog(emp)
            elif (readerInput.isBiometricRequest() and self.hasBioActionDialog()):
                templID = readerInput.getRequestData()
                emp = empIdentifyDlg.getIdentifiedEmpByBiometric(templID)
                if (emp):
                    emp.setVerifyPhoto(readerInput.getEmpPicture())
                    self.runBioActionDialog(emp)
        
    def __onOK(self, btnID):
        """ Executes button action. """
        itemID = self.getView().getSelectedRowPosition()
        
        if (hasattr(self, 'getIdlePhoto')):
            empPhoto = self.getIdlePhoto()
        else:
            empPhoto = None

        if (itemID not in self.__itemData):
            raise Exception('DynList item without data (itemID=%s!' % itemID)
        (action, item, emp) = self.__itemData[itemID]
        self.__startAction(action, item, emp, empPhoto)
        self.__processIdentifyRequests()
        
    def _runSwipeKeypadOrBioActionDialog(self, employee, actionType):
        """ Runs swipe, keypad or bio action dialog. Also executes verification. """
        if (employee == None):
            return
        if (actionType not in self.__itemData):
            itg.msgbox(itg.MB_OK, _('Action (%s) not defined!') % actionType)
            return
        with employee.Language():
            dlg = empVerifyDlg.Dialog(employee)
            dlg.run()
            if (dlg.verified()):
                if (employee.isLocalSupervisor()):
                    dlg = getActionDialogByName('supervisor.menu', employee=employee)
                    if (dlg != None):
                        dlg.run()
                        return
                elif (hasattr(employee, 'validate')):
                    notValidReason = employee.validate()
                    if (notValidReason):
                        msg.failMsg(notValidReason)
                        return
                (action, button, _emp) = self.__itemData[actionType]
                self.__startAction(action, button, employee, None)

    def __startAction(self, action, item, emp, empPhoto):
        """ Run action dialog, which will optionally identify+verify and run
        actual dialog of action. """
        restartLock = restartManager.PreventRestartLock() if (item.hasOption('preventRestart')) else DummyLock()
        with restartLock:
            with item.getActionConfig().getLanguage():
                dlg = _ActionDialog(action, item.getActionConfig().getParam(), emp, item.getReqRole(), empPhoto, item.getOptions())
                resID = dlg.run()
                # go back to configured target
                returnTarget = dlg.getReturnTarget()
                if (returnTarget):
                    if ((returnTarget == self.__menuName) or (returnTarget in self.__menuNameAliases)):
                        return # we arrived
                    self.setReturnTarget(returnTarget)
                    self.quit(itg.ID_OK)
                    return
                # handle old button options
                if (item.hasOption('returnAfter')):
                    self.cancel()
                    return
                eh = item.getExecutedHandler()
                if (resID == itg.ID_CANCEL and eh.invokeCancel()):
                    self.cancel()
                elif (resID == itg.ID_BACK and eh.invokeBack()):
                    self.back()
                elif (resID == itg.ID_TIMEOUT and eh.invokeTimeout()):
                    self.timeout()
                else:
                    target = eh.getTargetForResultID(resID)
                    if (target != None):
                        log.dbg('Returning to %s' % target)
                        if ((target == self.__menuName) or (target in self.__menuNameAliases)):
                            return # already arrived
                        self.setReturnTarget(target)
                        self.quit(itg.ID_OK)

    def getReturnTarget(self):
        return self.__returnTarget
        
    def setReturnTarget(self, target):
        self.__returnTarget = target
     
    def runSwipeActionDialog(self, employee):
        """ Run swipe action dialog. """
        self._runSwipeKeypadOrBioActionDialog(employee, 'swipe')

    def hasSwipeActionDialog(self):
        """ Return **True** if a swipe action is defined. """
        return 'swipe' in self.__itemData

    def runBioActionDialog(self, employee):
        """ Run bio action dialog. """
        self._runSwipeKeypadOrBioActionDialog(employee, 'bio')

    def hasBioActionDialog(self):
        """ Return **True** if a bio action is defined. """ 
        return 'bio' in self.__itemData

    def runKeypadActionDialog(self, employee):
        """ Run keypad action dialog. """
        self._runSwipeKeypadOrBioActionDialog(employee, 'keypad')
        self.__processIdentifyRequests()

    def hasKeypadActionDialog(self):
        """ Return **True** if a keypad action is defined. """
        return 'keypad' in self.__itemData

    def runSwipeAction(self, valid, reader, decoder, data, empPhoto=None):
        """ Run swipe action with card read data. """
        identificationRequestQueue.addCardReaderRequest(valid, reader, decoder, data, empPhoto)
        self.__processIdentifyRequests()

    def runBioAction(self, templID, empPhoto=None):
        """ Run bio action with template ID. """
        if (templID == None and 'bio' in self.__itemData):
            itg.failureSound()
            led.on(led.LED_ALL | led.LED_STATUS, led.RED, 2*1000)
            self.__onButtonPress('bio')
        else:
            identificationRequestQueue.addBiometricRequest(templID, empPhoto)
            self.__processIdentifyRequests()


    #
    # Properties
    #
    
    def loadProperties(self, menuName):
        self.__menuProperties = None
        buttons = getAppButtons()
        menu = buttons.getMenu(menuName)
        if (menu == None):
            log.warn('No menu "%s" found for properties' % menuName)
        else:
            self.__menuProperties = buttons.getMenuProperties(menu)
        
    def getMenuPropertyText(self, name, default=None):
        """ Return menu property. Please note that 
            loadMenuProperties must be called first. 
        """
        return getAppButtons().getMenuPropertyText(self.__menuProperties, name, default)

    def getMenuPropertyInteger(self, name, default=None):
        """ Return menu property. Please note that 
            loadMenuProperties must be called first. 
        """
        return getAppButtons().getMenuPropertyInteger(self.__menuProperties, name, default)

    def getMenuPropertyBoolean(self, name, default=None):
        """ Return menu property. Please note that 
            loadMenuProperties must be called first. 
        """
        return getAppButtons().getMenuPropertyBoolean(self.__menuProperties, name, default)

    def getMenuPropertyImage(self, name, default=None):
        """ Return menu property image. Please note that 
            loadMenuProperties must be called first. 
        """
        return getAppButtons().getMenuPropertyImage(self.__menuProperties, name, default)

    def getMenuPropertyIcon(self, name, default=None):
        """ Return menu property icon. Please note that 
            loadMenuProperties must be called first. 
        """
        return getAppButtons().getMenuPropertyIcon(self.__menuProperties, name, default)


class _MenuAction(Action):
    """ Generic menu action. """
    
    def __init__(self, actionName=None):
        self.__actionName = actionName
    
    def getName(self):
        return 'go.to.menu'
    
    def getButtonText(self, actionParam, employee, languages):
        None
    
    def getXsd(self):
        return """
            <xs:complexType>
              <xs:attribute name="name" type="xs:IDREF" use="required" />
            </xs:complexType>
        """

    def getHelp(self):
        return """
        The *go.to.menu* action simply navigates to a generic menu. Generic 
        menus must start with *menu.* (see :ref:`generic_menus`).
        
        Example::

          <button>
            <pos>6</pos>
            <label>More</label>
            <action>
              <go.to.menu name="menu.grid.emp.options" />
            </action>
          </button>
        
        """
    
    def getDialog(self, actionParam, employee, languages):
        menuName = self.__actionName or actionParam.getXMLElement().get('name')
        menuClass = getGenericMenuDialogByName(menuName)
        if (menuClass != None):
            return menuClass(menuName, actionParam, employee, languages)


class XMLButtons(object):

    def __init__(self, filename='/mnt/user/db/buttons.xml'):
        self.__xml = None
        self.__actionIDs = {}
        try:
            if (os.path.exists(filename)):
                root = xml.etree.cElementTree.parse(filename).getroot()
                self.__removeNamespace(root)
                if (root.tag != 'buttons'):
                    log.err('Error parsing %s; expected tag "buttons" got "%s"' % (filename, root.tag))
                else:
                    self.__xml = root
                    self.__parseActionIDs()
            else:
                log.err('No buttons available!')
        except Exception as e:
            log.err('Error loading %s (%s)' % (filename, e))

    def __removeNamespace(self, doc, ns=None):
        """Remove namespace in the passed document in place."""
        for elem in doc.getiterator():
            if elem.tag.startswith('{'):
                uri, tagName = elem.tag[1:].split('}')
                if (ns == None):
                    elem.tag = tagName
                elif (ns == uri):
                    elem.tag = tagName

    def getStartMenuName(self, default=None):
        if (self.__xml == None):
            return default
        terminalType = updateit.get_type()[:4].lower()
        startmenu = self.__xml.get('startmenu_%s' % terminalType)
        if (startmenu != None):
            return startmenu
        return self.__xml.get('startmenu', default)
    
    def getSetupMenuName(self, default=None):
        if (self.__xml == None):
            return default        
        terminalType = updateit.get_type()[:4].lower()
        setupmenu = self.__xml.get('setupmenu_%s' % terminalType)
        if (setupmenu != None):
            return setupmenu
        return self.__xml.get('setupmenu', default)
    
    def getMenu(self, menuName):
        if (self.__xml == None):
            return None
        for menu in self.__xml:
            if (menu.tag != 'menu'):
                continue
            if (menu.get('name') == menuName):
                return menu
        return None
    
    def getMenuProperties(self, menu):
        return menu.find('properties')
    
    def getMenuProperty(self, properties, name):
        if (properties == None):
            return None
        for p in properties:
            if (p.tag != 'property'):
                continue
            if (p.get('name') == name):
                return p
        return None
     
    def getMenuPropertyText(self, properties, name, default=None):
        p = self.getMenuProperty(properties, name)
        return _getText(p, (nls.getCurrentLanguage(),'en'), default)

    def getMenuPropertyInteger(self, properties, name, default=None):
        p = self.getMenuProperty(properties, name)
        return _getInteger(p, default)

    def getMenuPropertyBoolean(self, properties, name, default=None):
        p = self.getMenuProperty(properties, name)
        return _getBoolean(p, default)

    def getMenuPropertyImage(self, properties, name, default=None):
        p = self.getMenuProperty(properties, name)
        return _getImage(p, 'media/images', default)

    def getMenuPropertyIcon(self, properties, name, default=None):
        p = self.getMenuProperty(properties, name)
        return _getImage(p, 'media/icons', default)
            
    def getButtonConfig(self, button):
        return _ButtonConfig(button)

    def __parseActionIDs(self):
        # Go through XML and remember all actions with an ID
        for menu in self.__xml:
            if (menu.tag != 'menu'):
                continue
            for button in menu:
                if (button.tag not in ('button', 'swipe', 'bio', 'keypad')):
                    continue
                action = button.find('action')
                if (action != None):
                    actionID = action.get('id')
                    if (actionID != None):
                        self.__actionIDs[actionID] = action
    
    def getActionByID(self, actionID):
        """ Return action by ID """
        if (actionID in self.__actionIDs):
            return self.__actionIDs[actionID]
        return None


class _ButtonConfig(object):
    """ Helper class to hold information related to button configuration. """
    
    def __init__(self, button):
        self.__options      = _ButtonOptions(button.find('options'))
        self.__actionConfig = _ActionConfig(button.find('action'))
        self.__executedHandler = _ButtonActionExecutedHandler(button.find('onExit'),
                                            self.hasOption('invokeTimeout'),
                                            self.hasOption('invokeCancel'))
        self.__tag   = button.tag
        self.__label = button.find('label')
        self.__icon  = button.find('icon')
        self.__page  = _getInteger(button.find('page'), 1)
        self.__pos   = _getInteger(button.find('pos'), None)
        self.__reqRole = _getContent(button.find('requiredRole'))
        reqTerminalTag = button.find('requiredTerminal')
        if (reqTerminalTag == None):
            self.__reqTerminals = []
        elif (len(reqTerminalTag)!=0):
            self.__reqTerminals = [ o.tag for o in reqTerminalTag ]
        elif (reqTerminalTag.text):
            self.__reqTerminals = [ o.strip().lower()[:4] for o in reqTerminalTag.text.split(',') ]

    def isSwipeAction(self):
        return (self.__tag in ('swipe', 'bio', 'keypad', 'touch'))

    def isTouchAction(self):
        return (self.__tag == 'touch')
    
    def getSwipeAction(self):
        return self.__tag

    def getOptions(self):
        return self.__options
    
    def hasOption(self, option):
        return self.__options.hasOption(option)

    def getLabel(self, languages):
        return _getText(self.__label, languages)
    
    def getLabelColor(self):
        if (self.__label == None):
            return None
        return self.__label.get('color')
    
    def getIcon(self):
        return _getImage(self.__icon, 'media/icons')
        
    def getPage(self):
        return self.__page

    def getPos(self):
        return self.__pos
    
    def getReqRole(self):
        return self.__reqRole
    
    def requiredRoleFound(self, roles):
        return hasRequiredRole(roles, self.__reqRole)
    
    def getReqTerminals(self):
        return self.__reqTerminals

    def requiredTerminalFound(self, terminal):
        return ((not self.__reqTerminals) or (terminal in self.__reqTerminals))

    def getActionConfig(self):
        return self.__actionConfig
    
    def getExecutedHandler(self):
        return self.__executedHandler


class _ButtonOptions(object):
    """ Help class for button options. """
    
    def __init__(self, options=None):
        self.__options = {}
        if (options == None):
            pass
        elif (len(options)==0):
            for o in options.text.split(','):
                self.__options[o.strip()] = None
        else:
            for o in options:
                self.__options[o.tag] = o
        for o in self.__options:
            if (o not in _btnOptions):
                log.warn('Unknown button option (%s)' % o)
        for o in self.__options:
            if (o in ('invokeCancel', 'invokeTimeout', 'returnAfter')):
                log.warn('Button option %s is deprecated!' % (o,))

    def hasOption(self, option):
        return option in self.__options

    def getIntOption(self, option, default=None):
        try:
            if (option not in self.__options):
                return default
            optionTag = self.__options[option]
            return int(optionTag.text)
        except Exception as e:
            log.warn('Failed to retrieve integer option %s: %s' % (option, e))
            return default


class _ActionConfig(object):
    """ Helper class to hold information about action configuration. """
    
    def __init__(self, action):
        if (action != None):
            # Check for reference ID
            actionRefID = action.get('ref')
            if (actionRefID != None):
                action = getAppButtons().getActionByID(actionRefID)
        if (action == None):
            raise Exception('action tag missing or invalid in buttons.xml')
        # There are three ways to define an action in the XML
        # 1. action with name and string param
        # 2. action with name and XML param
        # 3. action with specific action tag including the params (preferred)
        self.__actionName     = _getContent(action.find('name'))
        if (self.__actionName == None):
            # Must be option 3
            if (len(action) != 1):
                raise Exception('action must have exactly one sub-element in buttons.xml!')
            actionTag = action[0]
            self.__actionName = actionTag.tag
            self.__actionLanguage = action.get('language')
            self.__actionLocale   = action.get('locale')
            self.__actionParam    = _ActionParam(actionTag)
        else:
            log.warn('Action <name> and <param> elements are deprecated (%s)!' % self.__actionName)
            self.__actionLanguage = _getContent(action.find('language'))
            self.__actionLocale   = _getContent(action.find('locale'))
            self.__actionParam = action.find('param')
            if (self.__actionParam == None):
                pass # no parameters
            elif (len(self.__actionParam)==0):
                # apply just the text (option 1)
                self.__actionParam = self.__actionParam.text 
            elif (len(self.__actionParam) == 1):
                # option 2, but we use the sub-element directly now
                self.__actionParam = _ActionParam(self.__actionParam[0]) 
            else:
                # also option 2, but very uncommon
                self.__actionParam = _ActionParam(self.__actionParam) 
    
    def getName(self):
        return self.__actionName
    
    def getParam(self):
        return self.__actionParam
    
    def getLanguage(self):
        return nls.Language(self.__actionLanguage, self.__actionLocale)        


class _ButtonActionExecutedHandler(object):
    
    def __init__(self, xml, invokeTimeout=False, invokeCancel=False, invokeBack=False):
        self.__targets = {}
        self.__invokeCancel  = invokeCancel
        self.__invokeBack    = invokeBack
        self.__invokeTimeout = invokeTimeout
        if (xml != None):
            self.__invokeCancel  = self.__text2Boolean(xml.get('invokeCancel'), self.__invokeCancel)
            self.__invokeBack    = self.__text2Boolean(xml.get('invokeBack'), self.__invokeBack)
            self.__invokeTimeout = self.__text2Boolean(xml.get('invokeTimeout'), self.__invokeTimeout)
            for returnToRule in xml.findall('returnTo'):
                target   = returnToRule.get('target')
                resultID = self.__text2ResultID(returnToRule.get('ifResultID'))
                if (not target):
                    log.err('target for return rule not specified!')
                elif (not resultID):
                    log.err('resultID for return rule not valid!')
                else:
                    self.__targets[resultID] = target
    
    def __text2Boolean(self, text, default):
        if (not text):
            return default
        return (text.strip().lower() == 'true')

    def __text2ResultID(self, text):
        if (text == None):
            return itg.ID_UNKNOWN
        resultIDs = { 'ok': itg.ID_OK, 'back': itg.ID_BACK, 'cancel': itg.ID_CANCEL, 'timeout': itg.ID_TIMEOUT }
        if (text in resultIDs):
            return resultIDs[text]
        log.warn('Unknown ResultID "%s"' % text)
        return None

    def invokeCancel(self):
        return self.__invokeCancel

    def invokeBack(self):
        return self.__invokeBack

    def invokeTimeout(self):
        return self.__invokeTimeout

    def getTargetForResultID(self, resID):
        if (resID in self.__targets):
            return self.__targets[resID]
        if (itg.ID_UNKNOWN in self.__targets):
            return self.__targets[itg.ID_UNKNOWN]
        return None


#
# XML helper functions
#
def _getContent(tag, default=None, stripped=True):
    """ Find content or return default. """
    if (tag == None):
        return default
    if (tag.text == None):
        return default
    if (stripped):
        return tag.text.strip() or default
    return tag.text or default

def _getOptionForLanguage(tagName, tag, languages, default=None):
    """ Extract content of tag named tagName for given language. """
    if (tag == None):
        return default
    if (len(tag) == 0):
        return tag.text or ''
    for language in languages:
        for text in tag:
            if (text.tag != tagName):
                continue
            if (text.get('language').lower() == language):
                return text.text
    return default

def _getText(tag, languages, default=None):
    """ Find text for preferred language. """
    return _getOptionForLanguage('text', tag, languages, default)

def _getSound(tag, languages, default=None):
    value = _getOptionForLanguage('sound', tag, languages, None)
    if (value == None):
        return default
    soundFile = 'media/sounds/%s' % value
    if (os.path.exists(soundFile)):
        return soundFile
    else:
        try:
            b64Sound = base64.b64decode(value)
            filename = '/tmp/dynbuttonsSound.wav'
            f = open(filename, 'w')
            f.write(b64Sound)
            f.close()
            return filename
        except:
            pass
    log.warn('Sound file %s does not exist' % value)
    return default
    
def _getMultiLanguageText(tag):
    """ Find all text and return as dictionary with language as key. """
    textDict = {}
    if (tag == None):
        pass
    elif (len(tag) == 0):
        if (tag.text):
            textDict['en'] = tag.text
    else:
        for text in tag:
            if (text.tag != 'text'):
                continue
            lang =text.get('language', None).lower()
            if (lang and text.text):
                textDict[lang] = text.text
    return textDict

def _getInteger(tag, default=0):
    """ Return integer value from text of given tag. """
    if (tag == None):
        return default
    try:
        return int(tag.text.strip())
    except Exception as e:
        log.warn('Error reading integer in %s (%s): %s' % (tag.tag, tag.text, e))
        return default

def _getFloat(tag, default=0):
    """ Return float value from text of given tag. """
    if (tag == None):
        return default
    try:
        return float(tag.text.strip())
    except Exception as e:
        log.warn('Error reading integer in %s (%s): %s' % (tag.tag, tag.text, e))
        return default

def _getBoolean(tag, default=False):
    """ Return True or False from boolean expression from tag. """
    if (tag == None or not tag.text):
        return default
    value = tag.text.strip().lower()
    if (value in ('on', 'true', '1', 'yes', 'enable', 'sure', 'of course', 'ja')):
        return True
    elif (value in ('off', 'false', '0', 'no', 'disable', 'nein')):
        return False
    log.warn('Unsupported boolean expression in %s: %s' % (tag.tag, value))
    return default

def _getImage(tag, resourceDir, default=None):
    """ Return image filename or itg.Image from tag (None if no image). """
    if (tag == None):
        return default
    elif (tag):
        b64Img = tag.find(updateit.get_type()[:4].lower())
        if (b64Img == None):
            return default
        imgType = b64Img.get('type')
        if (imgType == 'image/png'):
            return itg.Base64PNGImage(b64Img.text)
        elif (imgType == 'image/jpeg'):
            return itg.Base64JPEGImage(b64Img.text)                
        elif (imgType == 'image/x-ms-bmp'):
            return itg.Base64BMPImage(b64Img.text)
        elif (imgType == None):                
            log.warn('Image type not specified: %s' % imgType)
        else:
            log.warn('Unsupported image type: %s' % imgType)
    elif (tag.text):
        # Get the last part of the path (usually 'icons' or 'images')
        subfolder = os.path.split(resourceDir)[1]
        # Construct the theme path
        themeDir = '/mnt/user/db/themes/%s/%s' % (getAppSetting('theme_name'), subfolder)
        image = resourceManager.get('%s/%s' % (themeDir, tag.text))
        # If we can't find the image in the theme, use the default resourceDir
        if image is None:
            image = resourceManager.get('%s/%s' % (resourceDir, tag.text)) or default
        return image
    return default


class _ChangedDefaultDialogTimeout(object):
    """ Helper class to change default dialog timeout. """
    
    def __init__(self, timeout):
        self.__newTimeout = timeout
        self.__oldTimeout = None

    def __enter__(self):
        try:
            if (self.__newTimeout != None):
                timeout = itg.Dialog().getDefaultTimeout()
                if (timeout != self.__newTimeout):
                    log.dbg('Changing default dialog timeout to %s' % self.__newTimeout)
                    self.__oldTimeout = timeout
                    itg.Dialog().setDefaultTimeout(self.__newTimeout)
        except Exception as e:
            log.warn('Error setting default dialog timeout: %s' % e)
        
    def __exit__(self, exc_type, exc_value, traceback):
        if (self.__oldTimeout != None):
            log.dbg('Reverting default dialog timeout back to %s' % self.__oldTimeout)
            itg.Dialog().setDefaultTimeout(self.__oldTimeout)
 

class DummyLock(object):
    
    def __enter__(self):
        pass
    
    def __exit__(self, exc_type, exc_value, traceback):
        pass


def _getIndentSize(text):
    for line in text.splitlines():
        if (not line.strip()):
            continue
        return len(line) - len(line.lstrip())
    return 0

def _unindentDocStr(text):
    return text.replace('\n%s' % (' ' * _getIndentSize(text)), '\n')

    
def getHelp(appInfo):
    helpText = _unindentDocStr("""
    
    .. _buttons:

    Buttons
    #######
   
    The user interface flow of the application is configured by the
    "buttons.xml" file. It defines the start and setup menu, which 
    buttons to place on menus and what they should do (*actions*).
     
    In fact, the UI flow can be described by the following three terms:

     - Menus
     - Buttons
     - Actions
    
    A *menu* can have properties (see :ref:`menu_properties`) and 
    buttons. A *button* has a position and label and defines an
    *action* which is executed when the *button* is pressed. *Actions*     
    can be anything from a holiday booking, department transfer or clocking, 
    to things like showing the health monitor or profile details of a user. 
    There is a fixed list of *actions* to choose from (see :ref:`available_actions`).
    Some *actions* implement their own *menus*, they can be bound to *buttons* like 
    normal *actions* but can also contain new *buttons* them self.
    The special :ref:`action_go.to.menu` *action* can also be used to go to 
    :ref:`generic_menus`.
    
    The start menu is *idle.menu*, if not otherwise specified by the *startmenu*
    attribute of the *buttons* tag in the "buttons.xml" file. The application setup
    menu defaults to :ref:`action_app.setup` if not changed via the *setupmenu* attribute.
    
    Below is a simple buttons definition::
    
        <?xml version="1.0" encoding="utf-8"?>
        <buttons startmenu="idle.menu">
            <menu name="idle.menu">
                <button>
                    <pos>1</pos>
                    <action>
                        <app.health />
                    </action>
                </button>
                <button>
                    <pos>2</pos>
                    <action>
                        <app.exit />
                    </action>
                </button>
            </menu>
        </buttons>
    
    The example above configures two buttons for the main idle menu. The 
    configured actions will show the health monitor and exit the application.

    .. graphviz::
    
        digraph fig1 {
            size = "2";            
    
            start [shape=point];
            idle [shape=box, label="idle.menu"];
            health [label="app.health"];
            exit [label="app.exit"];

            start -> idle;
            idle -> health [label="'Health' button"];
            idle -> exit [label="'Exit' button"];
        }


    The next example is more complex, as it has two menus defined::

        <?xml version="1.0" encoding="utf-8"?>
        <buttons startmenu="idle.keypad">
            <menu name="idle.keypad">
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
        
            <menu name="emp.options.menu">
                <button>
                    <pos>2</pos>
                    <label>IN</label>
                    <action>
                        <clocking>...</clocking>
                    </action>
                </button>
                <button>
                    <pos>5</pos>
                    <label>OUT</label>
                    <action>
                        <clocking>..</clocking>
                    </action>
                </button>
            </menu>
        </buttons>

    The example configures a keypad idle menu. *emp.options.menu* menu is called
    after identification by keypad or card. The options menu has two buttons for 
    clocking IN and OUT. 

    .. graphviz::
    
        digraph fig2 {
            size = "2";
                    
            start [shape=point];
            idle [shape=box, label="idle.keypad"];
            options [shape=box, label="emp.options.menu"];
            clocking [label="clocking"];

            start -> idle;
            idle -> options [label="Keypad"];
            idle -> options [label="Swipe"];
            options -> clocking [label="'IN' button"];
            options -> clocking [label="'OUT' button"];
        }


    .. _button_position:
    
    Button Position
    ===============
    
    The placement of a button within a menu is defined by the *page* and
    *pos* tag. The *page* tag defines on which page the button should be 
    placed (only if the menu supports multiple pages).
    The *pos* tag defines the position on the menu.
    
    The example below places two buttons, each on a different page::
    
        <menu name="menu.multigrid.example">
            <button>
                <page>1</page>
                <pos>1</pos>
                <action>
                    <clocking.lastclockings />
                </action>
            </button>
            <button>
                <page>2</page>
                <pos>1</pos>
                <action>
                    <supervisor.menu />
                </action>
                <requiredRole>supervisor</requiredRole>
            </button>
        </menu>

    .. tip::
        Buttons are placed automatically if no positions are specified
        on all buttons of a menu.


    .. _button_labels:
            
    Button Labels
    =============
    
    Most actions have a default button label (e.g. "Exit App" for the
    *app.exit* action) and some actions may have dynamic button labels 
    which depend on their action parameters.
    It is possible to override the default button label by having a 
    *label* tag inside the button definition.
    
    The example below overrides the default button label::

        <button>
            <pos>1</pos>
            <label>
                <text language="en">Quit</text>
                <text language="de">Verlassen</text>
            </label>        
            <action>
                <app.exit />
            </action>
        </button>

    The *text* tags can be omitted, if a label text is only available in 
    one language::  

        <button>
            <pos>1</pos>
            <label>Quit</label>        
            <action>
                <app.exit />
            </action>
        </button>

    The *label* tag also allows to define colour of the label, e.g.::

        <label color="#00FF00">Green label</label>

    .. _button_icons:
    
    Button Icons
    ============
    
    It is also possible to configure icons for buttons. An icon can be specified in two ways.
    
     1. By using the default icons of the application and specifying the icon name.
     2. By supplying the Base64 encoded data of the icon per terminal type.
    
    Example of using the icon name::
    
        <button>
            <label>IN</label>
            <icon>clkin</icon>
            <pos>1</pos>
            <action>...</action>
        </button>
    
    Example of using a Base64 encoded icon for IT51 terminals::
    
        <button>
            <label>IN</label>
            <icon>
                <it51 type="image/png">
                 iVBORw0KGgoAAAANSUhEUgAAADAAAAAwCAYAAABXAvmHAAADrUlEQVRogdWa3W4TRxTHf8PHvZEi
                 0qJKRBHlqqILIYkDNDESAqkSif0EhCdo8gTFTxD6Bu4TJKRBVC2Sl6qtEF/ZBBA0BGcvKkTUSN3e
                 N3N6YRutd2eJ7R2vtn9ptJo5s+fsf858nJlZJSIMGuXZWQeoK6UKIhIAXittAN7K6qrXr26VBYG5
                 69eXFZQ/VkfABXyQDcC788Oa241uawQqc3MjND+yEJXp/f0bAiO9axUP8IENhXLvrMVJWSFQnp0t
                 AfUkud7fR0hvR6Fur969uxguO5RaKyBafyOiSU6C6PRJa70QtX3ECgGRQqSBPSBoZ7TWDkisa9mA
                 FQJa63B2Ze3evUq44OtrV+tAyYatKGx5IJz9LibXg5vp7BAIe0ARm9NFdLTIGux0odAH/vjT/SAm
                 z78HPv6BuffAQR84yNXe1iBeBMqI3DDKdc498HPd9QDvysx0zSTPvQfauP/gF99UPkgCPYcSMxem
                 lmcuFEu9vCNaW0upCExPFUsiUhahPj01uTRdnOwqPNAi1lIqApEAbUFE6l9NTji9vZcuRREbA5cm
                 zi+ASmrZk5G8A6xfmji/+OujJ7cTCXSuE27rOUJfe4ROxAiIyBK9x+5LF8fH5kSo/P7kaWwlDrfc
                 b4+fXga4OD52C/i2V0NRxLpQini9hMjO1NjZ2NYxXC+tnShMHkjTIAVguXjOqSEsPlz3gqjO4jmn
                 vXMbUag0tgAjASur5rwIDnDWoLP0wZaFbWaMgMXI0R8/88XfjzdfHMs0GrXkgQC4AvxrUacRtsdA
                 GwWAI0eP1izqNCJOwE7kGKDUzYfPvBWLOo0YhAdcoPLs5asP60G2HujfWABU11/9EVuRsyZQTawt
                 chKYN0g8lLrpvd4yHtJm2oW811u3kip/efpUiTiB6sbWduI7kKMNje6cDn2Fqmy+eXvg0bjOzaZe
                 xBchAGpKUd3cbsQCN+NreTlWeb694wPHejWS+2OVg5AbDyTh9Gcnlmhubqpbf75zo/LcDOIkiGiH
                 ZpRZ+PzEJ5ffvHsfROQ2zBhh+3TaQWTn1KfHO2amQ4cPOzZifxNsnU77oWyByF2AaI2oPBNoHi06
                 rWSS2zBjhNVr1tHhoZLRiFLtQZ4ab9//1eFKq9NoY3fPNZWPDg91teB1gZh+K7eUGcEDKtHCTBay
                 PtG+6XwA+I3dvZqpUlYEvsd8S+m3kgf8Q+t3g8bunt+t4kz+lQAYHR6ap3mU6AJBY3ev7x88wsiM
                 wKDwfxrERvwHrB38S0tBaw8AAAAASUVORK5CYII=
                </it51>
            </icon>
            <pos>1</pos>
            <action>...</action>
        </button>
    
    The following types are supported:
    
     - image/png
     - image/jpeg
     - image/x-ms-bmp
     
    
    .. _button_options:

    Button Options
    ==============
    
    Each button can have options to customise the way actions are
    executed.
    Options are put in the *options* tag as elements.
    Supported options are:
    
     - preventRestart (use PreventRestartLock while executing action)
     - dialogTimeout (change default dialog timeout while executing the action)
     - keypadView (use keypad view when identifying)
     - noKeypadOption (hide keypad option when identifying)
     - needEmployee (force identification/verification if not done yet)
     - switchEmployee (switch to another employee and become manager)
    

    Example to change the dialog timeout for all dialogs used by the action
    to 50 seconds::
     
        <button>

            ...
             
            <options>
                <dialogTimeout>50</dialogTimeout>
            </options>
        </button>
    
    The next example below shows the use of the *switchEmployee* option with the
    profile editor action::

        <menu name="menu.grid.example">
            <button>
                <pos>1</pos>
                <options><switchEmployee /></options>
                <action>
                    <profile.editor />
                </action>
            </button>
        </menu>

    The example is useful to allow users to change profile settings of
    other users. With the *switchEmployee* option, the current user will become 
    *manager* and a new user is identified (without verification). The action is 
    then executed within the scope of the newly identified user.
    
    Of course, normally not everyone is allowed to change anyones profile
    settings, which means that access to that menu should be restricted by
    requiring a role (see :ref:`button_roles`).


    .. _button_exit_behaviour:
    
    Exit behaviour
    ==============

    After an action is executed, the application will be back on the menu 
    which defined the button with that action.

    .. graphviz::
    
        digraph fig3 {
            size = "2";            
    
            start [shape=point];
            idle [shape=box, label="idle.menu"];
            options [shape=box, label="emp.options.menu"];
            clocking [label="clocking"];

            start -> idle;
            idle -> options;
            options -> clocking;
            clocking -> options;
        }

    
    The button can be customised to change this behaviour. The *onExit* tag can be
    used to define a target menu to return to, e.g.::

        <button>
            <pos>2</pos>
            <label>IN</label>
            <action>
                <clocking>...</clocking>
            </action>
            <onExit>
                <returnTo target="idle.menu"/>
            </onExit>
        </button>

    .. graphviz::
    
        digraph fig3 {
            size = "2";            
    
            start [shape=point];
            idle [shape=box, label="idle.menu"];
            options [shape=box, label="emp.options.menu"];
            clocking [label="clocking"];

            start -> idle;
            idle -> options;
            options -> clocking;
            clocking -> idle;
        }

    .. important::
        The target menu has to be one that was used in order to get to the 
        button (e.g. one of the parent menus). The application will exit 
        ungracefully if the target menu is not found.
    
    It is also possible to configure the *returnTo* tag to only return to
    the given target if the action returns with a specific return ID::
    
        <onExit>
            <returnTo target="idle.menu" ifResultID="ok" />
            <returnTo target="idle.menu" ifResultID="timeout" />
        </onExit>


    This is especially useful when an action provides a way for the user to 
    go back or cancel.

    .. graphviz::
    
        digraph fig3 {
            size = "2"; 
    
            start [shape=point];
            idle [shape=box, label="idle.menu"];
            options [shape=box, label="emp.options.menu"];
            clocking [label="clocking"];

            start -> idle;
            idle -> options;
            options -> clocking [label="clock"];
            clocking -> idle [label="ok"];
            clocking -> options  [label="back"];                
        }

    The *target* specifies the menu name or a menu name alias. The alias
    can be specified like this::
    
        <menu name="idle.keypad" alias="home"> ... </menu>

    The *onExit* tag also supports the following three boolean attributes:
    
     - *invokeCancel*
     - *invokeBack*
     - *invokeTimeout*
    
    If set to *true*, the menu will exit like the action, if the action was cancelled, 
    timed out or the user selected the back option.
    
    The following XML shows the *emp.options.menu* menu with a "More" button, which 
    leads to a dynamic grid menu. The dynamic menu itself has a back and a cancel 
    button. The user gets back to the *emp.options.menu* menu when he selects
    back. But if he selects cancel, the application will also cancel the *emp.options.menu* 
    menu.. 
    
    Example::
    
        <menu name="emp.options.menu">
            <button>
                <pos>6</pos>
                <label>More</label>
                <action>
                    <go.to.menu name="menu.grid.more" />
                </action>
                <onExit invokeCancel="true"></onExit>
            </button>
        </menu>
        
        <menu name="menu.grid.more">
            <button>
                <pos>4</pos>
                <action>
                    <btn.back />
                </action>
            </button>
            <button>
                <pos>8</pos>
                <action>
                    <btn.cancel />
                </action>
            </button>
          </menu>
   
    .. graphviz::
    
        digraph fig4 {
            size = "2"; 
    
            start [shape=point];
            idle [shape=box, label="idle.menu"];
            options [shape=box, label="emp.options.menu"];
            more [label="menu.grid.more"];

            start -> idle;
            idle -> options;
            options -> more [label="More"];
            more -> options [label="back"];
            more -> idle  [label="cancel"];                
        }


    .. _button_roles:
    
    Requiring a Role
    ================
    
    A button can specify a required role, in which case it is only visible to
    users with that role.
    
    Example::
    
        <button>
            <pos>1</pos>
            <action>
                <supervisor.menu />
            </action>
            <requiredRole>supervisor</requiredRole>
        </button>

    
    .. _button_terminal:
    
    Specifying a terminal type
    ==========================
    
    As some features may not be available on all terminals (e.g. IT51, IT31, IT11), 
    a button can be configured to only be visible on certain terminals.
    
    Example::
    
        <button>
            <pos>1</pos>
            <action>
                <idle.buttons />
            </action>
            <requiredTerminal><it51 /></requiredTerminal>
        </button>

    
    .. tip::
        It is also possible to specify a start or setup menu per 
        terminal type by defining the buttons attribute 
        *startmenu_<TERMINALTYPE>* and *setupmenu_<TERMINALTYPE>*, e.g.::
        
            <buttons startmenu="idle.menu" startmenu_it11="idle.keypad" >
                ...
            </buttons>
    
    
    .. _swipe_actions:
    
    Swipe Actions
    =============
    
    Some dialogs (e.g. *idle.menu*) support built-in methods for 
    identification (e.g. by swiping a card, using the biometric unit or 
    using the keypad / keypad icon).
    The *swipe*, *bio* and *keypad* tags can be used to bind an action 
    against these methods. 
    Swipe, biometric and keypad actions are configured like buttons but 
    without page, position and label. 

    Example::
    
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
    
        <bio>
            <action>
                <emp.options.menu />
            </action>
        </bio>

    .. _touch_actions:
    
    Touch Action
    ============
    
    The idle.menu dialog includes the option to allow the user to
    invoke an action by touching anywhere on the screen. Commonly
    this is used to automatically take the user to the main options
    screen.
    
    Example::
    
        <touch>
            <action>
                <emp.options.menu />
            </action>
        </touch>
        
    On terminals which do not support touch (e.g. IT11 and IT31)
    any button press will invoke the touch action.
    
    .. _button_actions:
    
    Button Actions
    ==============
    
    An *action* is defined within the *action* tag. Only one element is allowed
    and must be named after the *action*. Possible parameters are placed inside
    that tag.
    
    Example::
    
        <button>
            <pos>1</pos>
            <action>
                <transfer>absences</transfer>
            </action>
        </button>

    It is also possible to switch language for an action, although the 
    language of a user would be used instead if one was identified previously.
    
    Example of specifying language:: 

        <button>
            <pos>1</pos>
            <action language="de">
                <transfer>absences</transfer>
            </action>
        </button>

    
    On some menus it is necessary to place "back" or "cancel" buttons in 
    order to navigate back or to cancel the menu. This can be achieved 
    by using the following button actions, which will simply terminate the 
    menu with the appropriate exit code.
    
    The example below configures a cancel button::
    
        <button>
            <pos>3</pos>
            <action>
                <btn.cancel />
            </action>
        </button>

    Available button actions are:
    
     - """ + '\n     - '.join(_btnActions.keys()) + """
    
    .. _referencing_actions:
    
    Referencing actions
    ===================
    
    An action can be referenced, if it needs to be executed by different buttons or 
    swipe actions. This makes it unnecessary to define the action parameters multiple
    times.
    
    Example::
    
        <button>
            <pos>1</pos>
            <label>Clock</label>
            <action id="clockAction">
                <clocking>...</clocking>
            </action>
        </button>
    
        <swipe>
            <action ref="clockAction" />
        </swipe>
        
        <bio>
            <action ref="clockAction" />
        </bio>
    
    .. _menu_properties:
    
    Menu properties
    ===============
    
    Menu properties are defined inside the *properties* tag as *property* tags.
    Example::
    
        <menu name="idle.menu">
            <properties>
                <property name="idle.time">%H:%M:%S</property>
                <property name="idle.date">%d/%m/%Y</property>
                <property name="idle.text">Welcome</property>
                <property name="idle.subtext">Please present card</property>
            </properties>
        
            <button>
                ...
            </button>
        </menu>
    
    Multi-language text can be specified for properties that support it, in the same
    way as it is done for button labels (see :ref:`button_labels`)::

        <menu name="idle.menu">
            <properties>
                <property name="idle.text">
                    <text language="en">Welcome</text>
                    <text language="de">Willkommen</text>
                </property>
            </properties>
        
            <button>
                ...
            </button>
        </menu>

    Menu properties which refer to images or icons can also be configured similar to 
    button icons (see :ref:`button_icons`)::
    
        <menu name="idle.menu">
            <properties>
                <property name="idle.image.left">company-logo</property>
            </properties>
        
            <button>
                ...
            </button>
        </menu>

    
    .. _generic_menus:
    
    Generic menus
    =============
    
    It is possible to create generic menus which in turn can be dynamically 
    populated by buttons. This is very useful for grouping functionality 
    for example.
    
    Generic menus start with "menu." followed by the menu type and name 
    (e.g. *menu.grid.example*). The special :ref:`action_go.to.menu`
    action can be used to navigate to a generic menu.
    
    Example::

        <menu name="idle.menu">
            <button>
                <pos>1</pos>
                <action>
                    <go.to.menu name="menu.grid.example" />
                </action>
            </button>
        </menu>
    

        <menu name="menu.grid.example">
            <button>
                <pos>1</pos>
                <action>
                    <app.exit />
                </action>
            </button>
        </menu>

    The example above defines a button on the idle menu to go to the 
    generic *menu.grid.example* menu. The example menu has one button
    defined to exit the application.
    
    """)
    # Add help for generic menus
    genericMenuHelp = []
    for menuPrefix, (_, menuTitle, menuHelp) in _genericMenus.iteritems():
        if (menuTitle and menuHelp):
            genericMenuHelp.append('.. _generic_%s:' % menuPrefix[:-1].replace('.', '_'))
            genericMenuHelp.append('')
            genericMenuHelp.append('%s (%s\*)' % (menuTitle, menuPrefix))
            genericMenuHelp.append('-' * len(genericMenuHelp[-1]))
            genericMenuHelp.append('')
            genericMenuHelp.append(_unindentDocStr(menuHelp))
    helpText += '\n'.join(genericMenuHelp)
    # Add help for actions
    actionNames = filter(lambda a: not (hasattr(_actions[a], 'noHelp') and _actions[a].noHelp), _actions.keys())
    actionNames.sort()
    appInfo['numActions'] = len(actionNames)
    actionsHelp = [_unindentDocStr("""
    
    .. _available_actions:
    
    Actions
    #######
    
    This chapter lists all %(numActions)s actions of the %(appName)s application 
    together with a short description and example for each action.

    """ % appInfo) ]
    #    The following actions are defined:
    #    
    #     - %s
    #    
    #    """ % ('\n - '.join([ (':ref:`action_%s`' % a) for a in actionNames ]))]
    undocumentedActions = []
    for actionName in actionNames:
        action = _actions[actionName]
        if (hasattr(action, 'getHelp')):
            actionsHelp.append(".. _action_%s:\n\n%s\n%s\n%s" % (actionName, actionName, '=' * len(actionName), _unindentDocStr(action.getHelp())))
        else:
            undocumentedActions.append(actionName)
    if (undocumentedActions):
        print 'Actions with no help: %s' % ', '.join(undocumentedActions)
    helpText += '\n'.join(actionsHelp)
    return helpText

