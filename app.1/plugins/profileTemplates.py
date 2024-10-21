# -*- coding: utf-8 -*-
#
# Copyright 2013 Grosvenor Technology
#
 
import itg
from engine import dynButtons
from applib.db.tblSettings import getAppSetting
from applib import bio
 
class Dialog(itg.Dialog):
     
    def __init__(self, emp):
        super(Dialog, self).__init__()
        self.__emp = emp
        if (hasattr(emp, 'getTemplates') and hasattr(emp, 'setTemplates')):
            view = itg.MenuView(emp.getName())
            view.appendRow(_('Info'), cb=self.__onInfo)
            view.appendRow(_('Enrol'), cb=self.__onEnrol)
            view.setBackButton(_('Back'), self.back)
            view.setCancelButton(_('Cancel'), self.cancel)
        else:
            view = itg.MsgBoxView()
            view.setText(_('Biometric templates are not supported.'))
            view.setButton(0, _('OK'), itg.ID_OK, self.quit)        
        self.addView(view)
     
    def __onInfo(self, pos, row):
        dlg = dynButtons.getActionDialogByName('profile.templates.info', employee=self.__emp)
        self.runDialog(dlg)
         
    def __onEnrol(self, pos, row):
        dlg = dynButtons.getActionDialogByName('profile.templates.enrol', employee=self.__emp)
        self.runDialog(dlg)
 
 
class InfoDialog(itg.Dialog):
     
    def __init__(self, emp):
        super(InfoDialog, self).__init__()
        view = itg.MsgBoxView()
        view.setButton(0, _('OK'), itg.ID_OK, self.quit)
        if (hasattr(emp, 'getTemplates')):        
            tmpls = emp.getTemplates()
            numTemplates = len(tmpls) if (tmpls != None) else 0
            view.setText(_('Templates enrolled: %d') % (numTemplates))
        else:
            view.setText(_('Biometric templates are not supported.'))            
        self.addView(view)
 
 
 
 
 
#
#
# Support functions for dynamic buttons
#
#
class TemplateMenuAction(dynButtons.Action):
     
    def getName(self):
        return 'profile.templates.menu'
     
    def getButtonText(self, actionParam, employee, languages):
        return _('Templates')
     
    def getDialog(self, actionParam, employee, languages):
        return Dialog(employee)
 
    def isEmployeeRequired(self, actionParam):
        return True
 
    def getHelp(self):
        return """
        Manage templates.
 
        This action brings up a menu which gives the employee the choice to:
        
         - see the number of enrolled templates
         - enrol new fingers
          
        This menu uses the following actions:
        
         - profile.templates.enrol
         - profile.templates.info
         
        Example::
         
            <button>
                <pos>1</pos>
                <action>
                    <profile.templates.menu />
                </action>
            </button>
 
        """        
 
 
 
class TemplateInfoAction(dynButtons.Action):
     
    def getName(self):
        return 'profile.templates.info'
     
    def getButtonText(self, actionParam, employee, languages):
        return _('Template info')
     
    def getDialog(self, actionParam, employee, languages):
        return InfoDialog(employee)
 
    def isEmployeeRequired(self, actionParam):
        return True
 
    def getHelp(self):
        return """
        View information about enrolled templates.
 
        This action brings up a dialog showing the number of templates
        enrolled for the employee.
         
        This action is used by *profile.templates.menu*.
         
        Example::
         
            <button>
                <pos>1</pos>
                <action>
                    <profile.templates.info />
                </action>
            </button>
 
        """        
 
 
class TemplateEnrolAction(dynButtons.Action):

    def getName(self):
        return 'profile.templates.enrol'
     
    def getButtonText(self, actionParam, employee, languages):
        return _('Enrol templates')
     
    def getDialog(self, actionParam, employee, languages):
        if (hasattr(employee, 'getTemplates') and hasattr(employee, 'setTemplates')):
            if (employee.checkConsent(forEnrol=True)):    
                return bio.BioEnrolDialog(employee, getAppSetting('emp_enrol_quality'), getAppSetting('emp_enable_bio_template_preview'))
            else:
                return None
                #return Dialog(employee) # this will just show the error message
        else:
            return Dialog(employee) # this will just show the error message
            
 
    def isEmployeeRequired(self, actionParam):
        return True
 
    def getHelp(self):
        return """
        Enrol new fingers.
 
        This action brings up the biometric enrolment dialog. The enrolled
        fingerprints are then distributed to other terminals in the group. 
         
        This action is used by *profile.templates.menu*.
         
        Example::
         
            <button>
                <pos>1</pos>
                <action>
                    <profile.templates.enrol />
                </action>
            </button>
 
        """        
 
 
 
def loadPlugin():
    dynButtons.registerAction(TemplateMenuAction())
    dynButtons.registerAction(TemplateInfoAction())
    dynButtons.registerAction(TemplateEnrolAction())
