# -*- coding: utf-8 -*-
#
# Copyright 2012 Grosvenor Technology
#

import itg
import bioReader

from applib.bio.bioSyncDialog import BioSyncDialog
from applib.bio.bioTemplates import hasTemplateRepository, getTblBioTemplatesSyncStatus


class BioInfoDialog(itg.Dialog):
    """ Show information about number of loaded templates and give
    option to re-load all templates.
    
    .. note:: To see information related to biometric identification, a 
              template repository must have been assigned. 

    """        
    
    def __init__(self):
        super(BioInfoDialog, self).__init__()
        view = itg.MenuView(_('Biometric info'))
        view.setCancelButton(_('Cancel'), self.cancel)
        self.addView(view)
        self.__updateValues()
        
    def __updateValues(self):
        view = self.getView()
        view.removeAllRows()
        (_resID, (total, loaded, used)) = itg.waitbox(_('Please wait...'), self.__getData)
        view.appendRow(_('Total users'), total)
        if (hasTemplateRepository()):
            view.appendRow(_('Loaded users'), loaded)
            if (used != None):
                view.appendRow(_('Templates in reader'), used)
            view.appendRow(_('Sync templates'), hasSubItems=True, cb=self.__onReload)

    def __getData(self):
        tblSyncStatus = getTblBioTemplatesSyncStatus()
        total  = tblSyncStatus.getNumberOfUsers()
        loaded = tblSyncStatus.getNumberOfLoadedUsers()
        if (bioReader.isInitialised()):
            try:
                used = bioReader.getNumLoadedTemplates()
            except Exception as e:
                used = 'error (%s)' % e
        else:
            used = 'error'
        # NOTE: "used" is not updated properly by Suprema readers after re-synch! 
        return (total, loaded, used)
        
    def __onReload(self, pos, row):
        res = itg.msgbox(itg.MB_YES_NO_CANCEL, _('Reload ALL templates from database to reader?'))
        if (res == itg.ID_YES):
            itg.waitbox(_('Preparing templates for reloading...'), self.__reloadAll)
        elif (res != itg.ID_NO):
            return
        self.runDialog(BioSyncDialog(showWarnings=True))
        self.__updateValues()

    def __reloadAll(self):
        tblSyncStatus = getTblBioTemplatesSyncStatus()
        tblSyncStatus.reloadAll()
