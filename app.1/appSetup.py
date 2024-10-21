# -*- coding: utf-8 -*-
#
# Copyright 2013 Grosvenor Technology
#
import itg
import log
import clockserver
import webClient
import plugins
import applib
import appSettings
import emps
from engine import dynButtons, fileHandler
from applib.utils import resourceManager
from applib import bio
from applib.db.tblSettings import getAppSetting


class Dialog(itg.PseudoDialog):
    """ Application setup dialog."""
    
    def run(self):
        # register icons
        resourceManager.addResourceDir('media/icons')
        resourceManager.addResourceDir('media/images')
        # load  plug-ins
        plugins.load()
        # initialise clockserver
        clockserver.load()
        # initialise webclient
        webClient.load()
        # import default files
        fileHandler.registerStandardHandlers()
        fileHandler.applyDefaults()
        fileHandler.loadStartupProject()        
        # enable biometric identification?
        if (getAppSetting('emp_enable_bio_identify')):
            log.dbg('Enabling biometric identification')
            bio.setTemplateRepository(emps.getAppEmps().getTemplateRepository())
        # start main plug-in
        setupMenu = dynButtons.getAppButtons().getSetupMenuName('app.setup')
        dlg = dynButtons.getActionDialogByName(setupMenu)
        if (dlg != None):
            dlg.run()
        else:
            itg.msgbox(itg.MB_OK, _('No setup menu defined!'))



def runAppSetup():
    applib.debugger.start()    
    app = applib.Application(Dialog, appSettings.getDefaultSettings())        
    app.run()

#
# Entry point for application
#
if __name__ == '__main__':
    runAppSetup()
