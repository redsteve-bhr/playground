# -*- coding: utf-8 -*-
#
# Copyright 2013 Grosvenor Technology
#
import itg
import clockserver
from engine import dynButtons


class TestLinkDialog(itg.PseudoDialog):
    
    def run(self):
        (_resID, errMsg) = itg.waitbox(_('Testing connection, please wait...'), clockserver.testConfiguredConnection)
        if (errMsg):
            itg.msgbox(itg.MB_OK, '%s (%s)' % (_('Failed'), errMsg))
        else:
            itg.msgbox(itg.MB_OK, _('Success'))        
        self.setResultID(itg.ID_OK)
        return itg.ID_OK
        

class TestLinkAction(dynButtons.Action):

    def getName(self):
        return 'ce.testlink'
    
    def getButtonText(self, actionParam, employee, languages):
        return _('Test link')
    
    def getDialog(self, actionParam, employee, languages):
        return TestLinkDialog()

    def getHelp(self):
        return """
        Test network connection to configured Custom Exchange server(s).
                
        Example::
        
            <button>
                <pos>1</pos>
                <action>
                    <ce.testlink />
                </action>
            </button>

        """


def loadPlugin():
    dynButtons.registerAction(TestLinkAction())

