# -*- coding: utf-8 -*-
#
# Copyright 2023 Grosvenor Technology
#
from engine import fileHandler, dynButtons
import consentManagement

class ManageConsentAction(dynButtons.Action):
    
    def getName(self):
        return 'manage.consent'
    
    def getButtonText(self, actionParam, employee, languages):
        return _('Manage Consent')
    
    def getDialog(self, actionParam, employee, languages):
        return consentManagement.ManageConsentDialog(employee)

    def isEmployeeRequired(self, actionParam):
        return True

    def getXsd(self):
        return ""

    def getHelp(self):
        return """
        Manage Consent.

        This action allows a user to renew or decline their currently
        active consent for biometric data.
        
        Example::
        
            <button>
                <pos>1</pos>
                <action>
                    <manage.consent>
                </action>
            </button>

        """        

def loadPlugin():
    dynButtons.registerAction(ManageConsentAction())
    
    helpTxt = """Handler for file containing finger consent."""
    fh = fileHandler.PersistentProjectFileHandler('consentfinger.xml', restart=False, helpText=helpTxt)
    fileHandler.register('^(consentfinger\.xml)$', fh, 'Finger Consent')
