# -*- coding: utf-8 -*-

import itg
import log
import emps
from engine import dynButtons
import threading
import os
import json
from applib.bio import bioFinger

_testEmpId = "99999"
_templatesPath = "/tmp/testEmpTemplate.json"

class _SimpleTestEmployee():
    
    def __init__(self, _testEmpId, forceCreateNew=False):        
        
        # Erase and create a new testEmpTemplate.json
        if forceCreateNew:    
            if os.path.exists(_templatesPath):
                try:
                    os.remove(_templatesPath)
                except:
                    pass
            f = open(_templatesPath,"w+")
            f.close()       
    
    def setTemplates(self, templates):        
        """ Create a templates file in /tmp. """
        with open(_templatesPath, "w") as templs: 
            json.dump(templates, templs)
        
    def getTemplates(self):
        try:           
            with open(_templatesPath, 'r') as templs:                
                return json.load(templs)
        except ValueError as e:
            log.err('Template File not there %s' % e)
            return []     
        
    def supportsTemplates(self):
        return (self.getProfileDataID() != None)
    
    def getProfileDataID(self):                
        return _testEmpId
    
    def getEmpID(self):
        return _testEmpId
    
    def hasTemplates(self):
        return os.path.exists(_templatesPath) and len(self.getTemplates()) !=0
    
    def setFingers(self, fingers):        
        # call all  _SimpleTestEmployee's setFinger internals to set templates locally but skip 'tinfo uploading' 
        if (not fingers):
            raise Exception(_('At least one finger must be enrolled!'))
        templates = []
        fingerInfo = []
        for finger in fingers:
            templates.extend(finger.getTemplates())
            fingerInfo.append({'code': finger.getFingerCode(), 'quality': finger.getQuality()})
        tInfo = { 'fingerInfo': fingerInfo, 'numTemplates': len(templates)}
        self.setTemplates({"Templates" :  templates, "Info" : tInfo})

    def getFingers(self):
        """ Return list of BioFinger objects or an empty list. """
        try:
            with open(_templatesPath, 'r') as templs:
                tmplData = json.load(templs)
                try:
                    if ('Templates' not in tmplData or 'Info' not in tmplData):
                        return []                    
                    templates = tmplData['Templates']
                    templInfo = tmplData['Info']
                    if (len(templates) != templInfo['numTemplates']):
                        log.warn('Template and info are out of sync (%s)' % self.getProfileDataID())
                        return []
                    tpf = templInfo['numTemplates'] / len(templInfo['fingerInfo'])
                    if (tpf not in (2,3)):
                        log.err('Invalid number of templates per finger (%s)' % tpf)
                        return []
                    fingers = []
                    for fingerIdx, info in enumerate(templInfo['fingerInfo']):
                        code = info['code']
                        quality = info['quality']
                        finger = bioFinger.BioFinger(code, templates[fingerIdx*tpf:fingerIdx*tpf+tpf], quality)
                        fingers.append(finger)
                    return fingers
                except Exception as e:
                    log.err('Error extracting template info: %s' % e)
                return []

        except ValueError as e:
            log.err('Template File not there %s' % e)
            return []
    
    def getName(self):        
        return _testEmpId
    
    def getLanguages(self):        
        return ['en']
    
    def getLanguage(self, useManagerIfAvailable=True):
        'en'

class TestBioAction(dynButtons.Action):
    
    def getName(self):
        return 'test.bio'
    
    def getButtonText(self, actionParam, employee, languages):
        return _('Test Bio')
    
    def getDialog(self, actionParam, employee, languages):
        return TestBioDialog()

    def isEmployeeRequired(self, actionParam):
        return False

    def getXsd(self):
        return """
            <xs:complexType>
                <xs:all>
                </xs:all>
            </xs:complexType>
        """

    def getHelp(self):
        return """
        Bio Test.

        Test Biometric templates
 
        This action is responsible for adding, deleting, getting info
        of biometric templates.
         
        This action is used by *tests.menu*
        
        Example::
        
            <button>
                <pos>2</pos>
                <label>Test Bio</label>
                <action>
                    <test.bio />
                </action>
            </button>    

        """        

class TestBioDialog(itg.Dialog):    
    """ Dialog for showing menu with data collection buttons """

    def __init__(self):
        
        super(TestBioDialog, self).__init__()                       
        view = itg.GridMenuView()
        
        # Add buttons to view
        view.setButton(0, 'Add Templates', 0, cb=self.__onAdd)        
        view.setButton(2, 'Get Templates\' Info', 2, cb=self.__onGetInfo)
        view.setButton(3, 'Enrol Template', 3, cb=self.__onEnrolTemplate)        
        view.setButton(7, 'Back', itg.ID_BACK, cb=self.quit)
        # Add view to dialog
        self.addView(view)
        
    def __onAdd(self, btnID):
        """ Setup and run wizard """
        log.dbg('__onAdd() btnID={0}'.format(btnID))
        dlg = _AddTemplatesDialog()
        dlg.run()
        
    def __onGetInfo(self, btnID):
        """ Setup and run wizard """
        log.dbg('__onGetInfo() btnID={0}'.format(btnID))
        dlg = _InfoTemplatesDialog()
        dlg.run()
        
    def __onEnrolTemplate(self, btnID):
        """ Setup and run wizard """
        log.dbg('__onEnrolTemplate() btnID={0}'.format(btnID))
        testEmployee = _SimpleTestEmployee(_testEmpId, forceCreateNew=True)
        dlg = _EnrolFingerDialog(testEmployee)
        dlg.run()


class _AddTemplatesDialog(itg.Dialog):
    
    def onCreate(self):
        """ Create buttons for this wizard page """
        super(_AddTemplatesDialog, self).onCreate()
        view = itg.NumberInputView('How Many Employees\' Templates to Add')
        
        self.testEmployee = _SimpleTestEmployee( _testEmpId, forceCreateNew=False)        
        if not self.testEmployee.hasTemplates():
            view = itg.MsgBoxView()        
            view.setText('Please enrol A Template') 
            view.setButton(0, 'OK', itg.ID_OK, cb=self.quit)
        else:
            view.setButton(0, 'OK',     itg.ID_OK,   cb=self.__onOK)
            view.setButton(1, 'Cancel', itg.ID_CANCEL, cb=self.cancel)                
        self.addView(view)
        
    def __doActualWork(self, progressManager, event, numTemplates, testEmployee):
        
        added = 0
        
        # Search & find the first employee in tblEmps who doesn't have a corresponding template in tblTemplateRepos
        for i in xrange(numTemplates):
            if (event.isSet()):
                break
            progressManager.setText('Adding template #%d/%d' % ((i+1),numTemplates))
            progressManager.setProgress(i / numTemplates)
            
            tblEmps = emps.getAppEmps()                
            empsRows =  tblEmps.getAllEmps()
            
            templatesDict = tblEmps.getTemplateRepository().getUserIDsAndTemplateCount()             
            
            for emp in empsRows:
                    if emp['EmpID'] in templatesDict.keys():
                        # Already has a template registered associated with this employee
                        continue
                    else:                                                
                        if len(testEmployee.getTemplates()) != 0:              
                            
                            empl = emps.getEmpByTmplID(emp['EmpID'])
                            empl.setFingers(testEmployee.getFingers())
                            log.dbg("added templates for emp['EmpID'] %s"%(emp['EmpID']))
                            added += len(testEmployee.getTemplates())                                                          
                        else:                                    
                            log.dbg("Please Enrol a template!") 
                            added = -1                            
                        break                  
        if added !=-1:
            return str(added) + " Individual Templates Added"
        else:
            return "Please Enrol a template!"           
    
    def __onCancelWork(self, progressManager, event, numTemplates):
        event.set()  
    
    def __onOK(self, btnID):
        val = self.getView().getValue()
        try:
            empTemplates = self.testEmployee.getTemplates()            
            if len(empTemplates) != 0:            
                val = int(val)
                if (val >= 1 and val <= 9999):
                    val = int(val)
                    ev = threading.Event()
                    result = itg.progress( 'Please wait', self.__doActualWork, (ev,val,self.testEmployee), self.__onCancelWork)                      
                   
                    itg.msgbox(itg.MB_OK, result[1])
                    self.quit(btnID)
                else:
                    itg.msgbox(itg.MB_OK, _('Value must be between 1 and 9999'))
            else:
                itg.msgbox(itg.MB_OK, _("Please Enrol a template!"))
            
        except ValueError:
            pass        

class _InfoTemplatesDialog(itg.Dialog):
    
    def onCreate(self):        
        tblEmps = emps.getAppEmps()
        allTemplates = []
        try:
            templatesPerEmployee = tblEmps.getTemplateRepository().getUserIDsAndTemplateCount().values()[0]
            allTemplates = tblEmps.getTemplateRepository().getAllTemplates() * templatesPerEmployee
        except Exception as e:
            log.dbg('no templates added yet %s' % e)        
        
        log.dbg("allTemplates= %s" % (allTemplates))
        log.dbg("Total number of Individual templates %r" % (len(allTemplates)))
        view = itg.MsgBoxView()            
        view.setText(str(len(allTemplates)) + " Individual Templates Count")
        view.setButton(0, 'OK',     itg.ID_OK,     cb=self.quit)
        self.addView(view)
  
class _EnrolFingerDialog(itg.Dialog):
      
    def __init__(self, emp):
        super(_EnrolFingerDialog, self).__init__()
        self.__emp = emp        
   
        view = itg.MenuView(emp.getName())
        view.setBackButton(_('Back'), self.back)
        view.removeAllRows()
        view.appendRow(_('Enrol Finger'), hasSubItems=True, cb=self.__onEnrol)
        self.addView(view)
         
    
    def __onEnrol(self, pos, row):
        dlg = dynButtons.getActionDialogByName('profile.templates.enrol', employee=self.__emp)
        self.runDialog(dlg) 
        
# Global function to register the action

def loadPlugin():
    dynButtons.registerAction(TestBioAction())

