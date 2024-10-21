# -*- coding: utf-8 -*-
#
# Copyright 2011 Grosvenor Technology
#

from applib.gui import appWizard
from applib.db.tblSettings import SettingsSection, TextSetting, BoolSetting
import webClient
import itg

class Dialog(appWizard.AppWizardDialog):
    
    def run(self):
        pages = (appWizard.AutoConfigPage(),
                 appWizard.WelcomePage() if not itg.isIT11() else appWizard.WelcomePageNonInteractive(),
                 appWizard.PreCfgPageNonInteractive(),
                 appWizard.RegionPage(),
                 appWizard.CountryPage(),
                 appWizard.LanguagePage(),
                 appWizard.TimezonePage(),
                 appWizard.DeviceIDPage(),
                 #appWizard.DeviceIDPage(_('Secondary DeviceID'), 'clksrv2'),
                 webClient.WebClientWizardHostPage(),
                 webClient.WebClientWizardRegisterPage(),
                 appWizard.FinishPageNonInteractive(),
                 appWizard.SaveProjectPage())
        self._runWizard(pages)
        return self.getResultID()
    
    
def getSettings():
    # Wizard Section Settings
    sectionName = 'Wizard Settings'
    sectionComment = 'These are the settings for changing the setup wizard for the terminal.'
    wizSection = SettingsSection(sectionName, sectionComment)
    s = TextSetting(wizSection,
            name     = 'wiz_supported_countries', 
            label    = 'Supported countries',
            data     = 'world',
            comment  = ('Comma-separated list of country codes and continents for specifying supported countries in application wizard.'))
    s.setAllowEdit(False)
    s.setHideInEditor(True)
    s = BoolSetting(wizSection,
            name     = 'wiz_prompt_language', 
            label    = 'Prompt for language', 
            data     = 'True', 
            comment  = ('If True, ask for language in application wizard.'))
    s.setAllowEdit(False)
    s.setHideInEditor(True)
    s = BoolSetting(wizSection,
            name     = 'wiz_prompt_timezone', 
            label    = 'Prompt for timezone', 
            data     = 'True', 
            comment  = ('If True, ask for timezone in application wizard.'))
    s.setAllowEdit(False)
    s.setHideInEditor(True)

    return [wizSection,]
            