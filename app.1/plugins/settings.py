# -*- coding: utf-8 -*-
#
# Copyright 2013 Grosvenor Technology
#
from engine import dynButtons
from applib.gui import settingsEditor




class AppSettingsMenuAction(dynButtons.Action):
    
    def getName(self):
        return 'app.settings'
    
    def getButtonText(self, actionParam, employee, languages):
        return _('Settings')

    def getDialog(self, actionParam, employee, languages):
        return settingsEditor.SettingsEditorDialog()

    def getHelp(self):
        return """
        Application settings editor.
        
        This action gives access to the application settings editor, which
        allows to see and change application settings.
        
        .. important::
            This action should only be used as part of the application setup menu.

                
        Example::
        
            <button>
                <pos>1</pos>
                <action>
                    <app.settings />
                </action>
            </button>

        """





def loadPlugin():
    dynButtons.registerAction(AppSettingsMenuAction())

