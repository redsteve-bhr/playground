# -*- coding: utf-8 -*-
#
# Copyright 2013 Grosvenor Technology
#
from engine import dynButtons
from applib import bio


class BioInfoAction(dynButtons.Action):

    def getName(self):
        return 'bio.info'
    
    def isVisible(self, actionParam, employee, languages):
        return bio.hasTemplateRepository()
    
    def getButtonText(self, actionParam, employee, languages):
        return _('Biometric')
    
    def getDialog(self, actionParam, employee, languages):
        return bio.BioInfoDialog()

    def getHelp(self):
        return """
        Show information about biometric reader. The user also gets
        the option to re-synchronise the reader with the database.
        
        .. important::
            This action should only be used as part of the application setup menu.

        Example::
        
            <button>
                <pos>1</pos>
                <action>
                    <bio.info />
                </action>
            </button>

        """


def loadPlugin():
    dynButtons.registerAction(BioInfoAction())

