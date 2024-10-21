# -*- coding: utf-8 -*-
#
# Copyright 2011 Grosvenor Technology
#
import itg
import thread
import weakref
from engine import dynButtons
from plugins.clockings import tblLastClockings
import emps

def _waitForOnlineMessageJob(dlgref, job, emp):
    job.wait()
    dlg = dlgref()
    if (dlg):
        itg.runLater(dlg.updateDetails, (emp,))
        

class EmpOptionsDialog(dynButtons.DynButtonsMixin, itg.Dialog):
    """ Options dialog for employee, showing last local clockings and options."""
    
    def __init__(self, emp):
        super(EmpOptionsDialog, self).__init__()
        self.loadProperties('emp.options.menu')
        btnAlignment = self.getMenuPropertyText('button.alignment')
        view = itg.DetailsGridMenuView(emp.getName(), self.__getPicture(emp), self.__getDetails(emp), btnAlignment)
        view.setPrompt(self.getMenuPropertyText('emp.options.prompt', ''))
        numButtons = self.populateButtons(view, 'emp.options.menu', emp)
        if (numButtons == 0):
            view.setButton(0, _('Back'), itg.ID_BACK, self.quit)
        self.addView(view)
        self.setTimeout(self.getMenuPropertyInteger('timeout', self.getDefaultTimeout()))

    def __getPicture(self, emp):
        if (not hasattr(itg, 'ImageView')):
            return None
        if (hasattr(emp, 'getProfilePicture')):
            return emp.getProfilePicture() 
        else:
            return None

    def __getDetails(self, emp):
        clockings = []
        onlineMessageJob = emp.getOnlineMessageJob() if hasattr(emp, 'getOnlineMessageJob') else None
        if (onlineMessageJob):
            header = self.getMenuPropertyText('emp.options.messages.header', _('<b>Messages:</b>'))
            if (header):
                clockings.append(header)
            if (onlineMessageJob.hasFinished()):
                resp = onlineMessageJob.getResponse()
                if (resp):
                    clockings.append(resp)
                    clockings.append('')
                else:
                    clockings = []
            elif (onlineMessageJob.hasFailed()):
                clockings.append(_('Error: %s') % onlineMessageJob.getFailedReason())
                clockings.append('')
            else:
                clockings.append(_('<i>Loading...</i>\n'))
                thread.start_new_thread(_waitForOnlineMessageJob, (weakref.ref(self), onlineMessageJob, emp))
            
        itemList = emps.getAppEmpDisplayItems().parseToPango(emp.getEmpID())
        for item in itemList:   
            clockings.append(item)

        timeFormat = self.getMenuPropertyText('lastClockings.timeFormat')
        lastClockings = tblLastClockings.getAppLastClocking().selectLast(emp.getEmpID(), 6, timeFormat)
        if len(lastClockings) > 0:
            clockings.append('')
            header = self.getMenuPropertyText('emp.options.clockings.header', _('<b>Last clockings on this terminal:</b>'))
            if (header):
                clockings.append(header)
            for l in lastClockings:
                reviewText = l['Type']
                if (l['Labels'] != None):
                    labels = l['Labels']
                    for lang in emp.getLanguages():
                        if (lang in labels):
                            reviewText = labels[lang]
                            break
                clockings.append('%s - %s' % (l['LocalTime'], reviewText))
        return '\n'.join(clockings)

    def updateDetails(self, emp):
        self.getView().setDetails(self.__getDetails(emp))
        

#
#
# Support functions for dynamic buttons
#
#
class EmpOptionsMenuAction(dynButtons.Action):
    
    def getName(self):
        return 'emp.options.menu'
    
    def getButtonText(self, actionParam, employee, languages):
        return _('Options')
    
    def getDialog(self, actionParam, employee, languages):
        return EmpOptionsDialog(employee)

    def isEmployeeRequired(self, actionParam):
        return True
    
    def getHelp(self):
        return """
        Show local last clockings and offer options.

        This menu is normally used after the idle menu. It displays the name
        of the employee and an overview of his last clockings made on the 
        terminal.

        The following properties can be defined to customise the menu.
        
        .. tabularcolumns:: |l|l|p{0.25\\linewidth}|p{0.35\\linewidth}|
        
        +------------------------------+---------+----------------------+------------------------------------------+
        | Name                         | Type    | Default              | Description                              |
        +==============================+=========+======================+==========================================+
        | button.alignment             | Text    |                      | Alignment of button text                 |
        +------------------------------+---------+----------------------+------------------------------------------+        
        | timeout                      | Number  | 60                   | Dialog timeout in seconds                |
        +------------------------------+---------+----------------------+------------------------------------------+
        | emp.options.prompt           | Text    |                      | Text shown on IT11 terminals             |
        +------------------------------+---------+----------------------+------------------------------------------+        
        | emp.options.clockings.header | Text    | <b>Last clockings on | Text shown above last clockings.         |
        |                              |         | this terminal:</b>   |                                          |
        +------------------------------+---------+----------------------+------------------------------------------+        
        | emp.options.messages.header  | Text    | <b>Messages:</b>     | Text shown above online messages, if any.|
        +------------------------------+---------+----------------------+------------------------------------------+        
        
        6 buttons can be configured for this menu. A common configuration looks
        like this::
        
            <menu name="emp.options.menu">
            
              <button>
                <pos>2</pos>
                <action>
                  <clocking>...</clocking>
                </action>
              </button>
              
              <button>
                <pos>5</pos>
                <action>
                  <clocking>...</clocking>
                </action>
              </button>
              
              <button>
                <pos>3</pos>
                <action>
                  <btn.cancel />
                </action>
              </button>
    
            </menu>
        
        """


def loadPlugin():
    dynButtons.registerAction(EmpOptionsMenuAction())

