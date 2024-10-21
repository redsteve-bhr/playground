# -*- coding: utf-8 -*-
#
# Copyright 2023 Grosvenor Technology
#
"""Action and Dialog for Viewing and Resetting Revisions"""

import itg
from engine import dynButtons
from applib.db.tblSettings import getAppSetting, getAppSettings

class RevisionsDialog(itg.Dialog):
    
    def onCreate(self):
        super(RevisionsDialog, self).onCreate()
        view = itg.MenuView(_('Reset Revisions'))
        view.setCancelButton(_('Cancel'), self.cancel)
        view.setBackButton(_('Back'), self.back)
        self.__loadRevisions()
        view.appendRow('Reset All', cb=self.__onResetAll, data=None)
        for revision in self.revisions:
            label = '{label}: {revision}\n'.format(label=revision['label'], revision=revision['revision'])
            view.appendRow(label, cb=self.__onResetRevision, data=revision)
        self.addView(view)        

    def __loadRevisions(self):
        self.revisions = []
        self.revisions.append({'label': 'Buttons',         'setting': 'webclient_buttons_revision',        'revision': getAppSetting('webclient_buttons_revision')})
        self.revisions.append({'label': 'Data Collection', 'setting': 'webclient_datacollection_revision', 'revision': getAppSetting('webclient_datacollection_revision')})
        self.revisions.append({'label': 'Employee Info',   'setting': 'webclient_employeeinfo_revision',   'revision': getAppSetting('webclient_employeeinfo_revision')})
        self.revisions.append({'label': 'Employees',       'setting': 'webclient_employees_revision',      'revision': getAppSetting('webclient_employees_revision')})
        self.revisions.append({'label': 'Job Categories',  'setting': 'webclient_job_categories_revision', 'revision': getAppSetting('webclient_job_categories_revision')})
        self.revisions.append({'label': 'Job Codes',       'setting': 'webclient_job_codes_revision',      'revision': getAppSetting('webclient_job_codes_revision')})
        self.revisions.append({'label': 'Schedules',       'setting': 'webclient_schedules_revision',      'revision': getAppSetting('webclient_schedules_revision')})

    def __onResetRevision(self, pos, row):
        revision = row['data']
        resID = itg.msgbox(itg.MB_OK_CANCEL, _('Reset revision for "{}"?'.format(revision['label'])))
        if (resID == itg.ID_OK):
            getAppSettings().set(revision['setting'], '')
            revision['revision'] = ''
            self.__resetLabels()
            
    def __onResetAll(self, pos, row):
        resID = itg.msgbox(itg.MB_OK_CANCEL, _('Reset all revisions?'))
        if (resID == itg.ID_OK):
            for revision in self.revisions:
                getAppSettings().set(revision['setting'], '')
                revision['revision'] = ''
            self.__resetLabels()

    def __resetLabels(self):
        view = self.getView()
        for i in range(0, len(self.revisions)):
            revision = self.revisions[i]
            view.changeRow(i, 'label', '{label}: {revision}\n'.format(label=revision['label'], revision=revision['revision']))

#
#
# Support functions for dynamic buttons
#
#
class RevisionsAction(dynButtons.Action):
    
    def getName(self):
        return 'ws.revisions'
    
    def getButtonText(self, actionParam, employee, languages):
        return _('Revisions')
    
    def getDialog(self, actionParam, employee, languages):
        return RevisionsDialog()

    def isEmployeeRequired(self, actionParam):
        return False

    def getHelp(self):
        return """
        Revisions Action.
        
        This displays a list of current revisions, and allows them to be 
        reset (in order to force a re-load of the files).

        Example::
        
            <button>
                <pos>1</pos>
                <action>
                    <ws.revisions />
                </action>
            </button>

        """        


def loadPlugin():
    dynButtons.registerAction(RevisionsAction())
