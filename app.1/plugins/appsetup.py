# -*- coding: utf-8 -*-
#
# Copyright 2013 Grosvenor Technology
#
import itg
from engine import dynButtons


class Dialog(dynButtons.DynButtonsMixin, itg.Dialog):
    
    def __init__(self, emp=None):
        super(Dialog, self).__init__()
        self.loadProperties('app.setup')
        btnAlignment = self.getMenuPropertyText('button.alignment')
        view = itg.MultiGridMenuView(btnAlignment)
        view.setBackCb(self.back)
        defaultXML = [ '<menu name="app.setup">' ]
        defaultXML.append('<button><pos>1</pos><action><app.settings /></action></button>')
        defaultXML.append('<button><pos>2</pos><action><relay.editor /></action></button>')
        if (dynButtons.hasAction('ce.transactions.replay')):
            defaultXML.append('<button><pos>3</pos><action><ce.transactions.replay /></action></button>')
        defaultXML.append('<button><pos>4</pos><action><bio.info /></action></button>')
        defaultXML.append('<button><pos>5</pos><action><usb.import /></action></button>')
        defaultXML.append('<button><pos>6</pos><action><usb.export /></action></button>')
        if (dynButtons.hasAction('ce.testlink.replay')):
            defaultXML.append('<button><pos>7</pos><action><ce.testlink /></action></button>')
        defaultXML.append('</menu>')
        self.populateButtons(view, 'app.setup', emp, 7, ''.join(defaultXML))
        self.addView(view)
        self.setTimeout(self.getMenuPropertyInteger('timeout', self.getDefaultTimeout()))        


#
#
# Support functions for dynamic buttons
#
#
class AppSetupMenuAction(dynButtons.Action):
    
    def getName(self):
        return 'app.setup'
    
    def getButtonText(self, actionParam, employee, languages):
        return 'Setup'
    
    def getDialog(self, actionParam, employee, languages):
        return Dialog(employee)

    def getHelp(self):
        return """
        Application setup menu action.

        The application setup action implements a configurable menu which is 
        used when the application setup is entered via the terminal setup 
        (unless another menu was configures via the *setupmenu* attribute).

        The following properties can be defined to customise the menu.
        
        .. tabularcolumns:: |l|l|p{0.25\\linewidth}|p{0.35\\linewidth}|
        
        +------------------------------+---------+----------------------+------------------------------------------+
        | Name                         | Type    | Default              | Description                              |
        +==============================+=========+======================+==========================================+
        | button.alignment             | Text    |                      | Alignment of button text                 |
        +------------------------------+---------+----------------------+------------------------------------------+        
        | timeout                      | Number  | 60                   | Dialog timeout in seconds                |
        +------------------------------+---------+----------------------+------------------------------------------+        
        
        
        The application setup menu supports multiple pages and up to 7 buttons
        per page. The following standard set of actions is used when this menu
        is not configured:
        
         - app.settings
         - relay.editor
         - ce.transactions.replay
         - ce.testlink
         - bio.info
         - usb.import
         - usb.export

        Below is a possible application setup menu configuration::
        
            <menu name="app.setup">
                <button>
                    <pos>1</pos>
                    <action>
                        <app.settings />
                    </action>
                </button>
                
                <button>
                    <pos>5</pos>
                    <action>
                        <usb.import />
                    </action>
                </button>
                
                <button>
                    <pos>6</pos>
                    <action>
                        <usb.export />
                    </action>
                </button>
            </menu>

        """        




def loadPlugin():
    dynButtons.registerAction(AppSetupMenuAction())


