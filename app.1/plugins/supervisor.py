# -*- coding: utf-8 -*-
#
# Copyright 2013 Grosvenor Technology
#
import itg
from engine import dynButtons


class Dialog(dynButtons.DynButtonsMixin, itg.Dialog):
    
    def __init__(self, emp=None):
        super(Dialog, self).__init__()
        self.loadProperties('supervisor.menu')
        btnAlignment = self.getMenuPropertyText('button.alignment')
        view = itg.MultiGridMenuView(btnAlignment)
        view.setBackCb(self.back)
        defaultXML = """
            <menu name="supervisor.menu">
                <button><pos>1</pos><action><profile.editor /></action><options><switchEmployee /></options></button>
                <button><pos>2</pos><action><clocking.review /></action><options><switchEmployee /></options></button>
                <button><pos>3</pos><action><ce.testlink /></action></button>
                <button><pos>5</pos><action><app.health /></action></button>
                <button><pos>6</pos><action><assistit.enable /></action></button>
                <button><pos>7</pos><action><diagnostics /></action></button>
                <button><pos>8</pos><action><app.exit /></action></button>
            </menu>        
        """
        self.populateButtons(view, 'supervisor.menu', emp, 7, defaultXML)
        self.addView(view)
        self.setTimeout(self.getMenuPropertyInteger('timeout', self.getDefaultTimeout()))
       


#
#
# Support functions for dynamic buttons
#
#
class SupervisorMenuAction(dynButtons.Action):
    
    def getName(self):
        return 'supervisor.menu'
    
    def getButtonText(self, actionParam, employee, languages):
        return _('Supervisor')
    
    def getDialog(self, actionParam, employee, languages):
        return Dialog(employee)

    def getHelp(self):
        return """
        Show supervisor menu.

        The supervisor menu is a configurable menu useful to group supervisor
        actions. It supports multiple pages and up to 7 buttons per page. 

        The following properties can be defined to customise the menu.
        
        .. tabularcolumns:: |l|l|p{0.25\\linewidth}|p{0.35\\linewidth}|
        
        +------------------------------+---------+----------------------+------------------------------------------+
        | Name                         | Type    | Default              | Description                              |
        +==============================+=========+======================+==========================================+
        | button.alignment             | Text    |                      | Alignment of button text                 |
        +------------------------------+---------+----------------------+------------------------------------------+        
        | timeout                      | Number  | 60                   | Dialog timeout in seconds                |
        +------------------------------+---------+----------------------+------------------------------------------+        
        
        It is optional to configure actions for this menu. The following actions
        are configured as default:
        
         - profile.editor
         - clockings.review
         - assistit.enable
         - ce.testlink
         - app.health
         - app.exit

        It is good practice to require the supervisor role for this action.

        .. important::
            This menu is automatically called when the local supervisor is
            identified.

        Below is a possible supervisor menu configuration::
        
            <menu name="supervisor.menu">

              <button>
                <page>1</page>
                <pos>1</pos>
                <action>
                  <profile.editor />
                </action>
              </button>

              <button>
                <page>1</page>
                <pos>3</pos>
                <action>
                  <assistit.enable />
                </action>
              </button>

              <button>
                <page>1</page>
                <pos>5</pos>
                <action>
                  <app.health />
                </action>
              </button>

              <button>
                <page>1</page>
                <pos>6</pos>
                <action>
                  <app.exit />
                </action>
              </button>

            </menu>

        """        




def loadPlugin():
    dynButtons.registerAction(SupervisorMenuAction())


