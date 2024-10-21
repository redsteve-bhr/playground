# -*- coding: utf-8 -*-
#
# Copyright 2013 Grosvenor Technology
#
import itg
import log
import clockserver
import plugins
import emps
from engine import dynButtons, fileHandler
import appit
from applib.db.tblSettings import getAppSetting, getAppSettings
from applib.gui import msg
from applib.utils import resourceManager, healthMonitor
from applib import bio
from applib.bio.bioEncryption import BioEncryption
import webClient
import os
import appMonitor

_templatesPath = "/tmp/testEmpTemplate.json"
def _deleteLocalTemplates():
        """ Delete all local templates from terminal, including the /tmp/testEmpTemplate.txt fake template file under"""        
        # Delete testTemplate and force the user to enforce re-enrol the test template (when testing)        
        if os.path.exists(_templatesPath):
            try:
                os.remove(_templatesPath)
            except:
                pass        
        emps.getAppEmps().getTemplateRepository().deleteAllTemplates()
        # Reload all templates from server
        log.info("Reloading all employees info from server.")
        emps.getAppEmps().resetAllMD5s()
        getAppSettings().set('webclient_employees_revision', '')



class Dialog(itg.PseudoDialog):
    """ Main dialog."""
    
    def run(self):
        plugins.customThemes.updateTheme()
        
        """ Start background tasks."""
        # register icons
        resourceManager.addResourceDir('media/icons')
        resourceManager.addResourceDir('media/images')
        
        themeName = getAppSetting('theme_name')
        resourceManager.addResourceDir('/mnt/user/db/themes/%s/icons' % themeName)
        resourceManager.addResourceDir('/mnt/user/db/themes/%s/images' % themeName)

        # Application Monitor
        appMonitor.start()
        
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
        # Initialise biometric encryption
        BioEncryption.init(_deleteLocalTemplates)
        
        # start plug-ins
        plugins.start()
        
        # start communication
        clockserver.start()
        webClient.start() 
        
        # enable biometric identification?
        if (getAppSetting('emp_enable_bio_identify')):
            log.dbg('Enabling biometric identification')
            bio.setTemplateRepository(emps.getAppEmps().getTemplateRepository())
        
        # use health monitor
        if (getAppSetting('emp_limit_by') == 'table'):
            healthMonitor.getAppHealthMonitor().add(emps.getAppEmps())
        
        # configure default timeout
        msg.setDefaultPassTimeout(getAppSetting('emp_pass_msg_sec'))
        msg.setDefaultFailTimeout(getAppSetting('emp_fail_msg_sec'))

        appInfo = appit.AppInfo()
        if "rc." in appInfo.version():
            runTests = False # Set to True to run the tests for the Consents system
            if runTests:
                from plugins.consent.consentTests import Tests
                t = Tests()
                t.run()
        
        # start main plug-in
        startMenu = dynButtons.getAppButtons().getStartMenuName('idle.menu')
        dlg = dynButtons.getActionDialogByName(startMenu)
        if (dlg != None):
            dlg.run()
        else:
            itg.msgbox(itg.MB_OK, _('No main menu defined!'))

