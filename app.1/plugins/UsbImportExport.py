# -*- coding: utf-8 -*-
#
# Copyright 2013 Grosvenor Technology
#
import itg
import appit
import os
import log
import hashlib
import time
import cfg
from engine import fileHandler, dynButtons
from applib.utils import restartManager
from applib.gui import usbDialog
from applib.db.tblSettings import getAppSetting




class ImportFromUSBDialog(itg.PseudoDialog):

    def run(self):
        usbMountDlg = usbDialog.USBMountDialog()
        usbMountDlg.run()
        ua = usbMountDlg.getUSBAccess()
        if (not ua):
            return itg.ID_BACK
        with ua:
            dlg = _ImportExplorerDialog(ua.getPath(), ua.getPath())
            return dlg.run()


class ImportFilesDialog(itg.PseudoDialog):
    
    def __init__(self, path, files):
        super(ImportFilesDialog, self).__init__()
        self.__path = path
        self.__files = files
    
    def run(self):
        resID = itg.msgbox(itg.MB_YES_NO, _('Do you want to import files from USB?'))
        if (resID != itg.ID_YES):
            return itg.ID_BACK
        usbMountDlg = usbDialog.USBMountDialog()
        usbMountDlg.run()
        ua = usbMountDlg.getUSBAccess()
        if (not ua):
            return itg.ID_BACK
        rrm = fileHandler.RestartRequestManager()
        with ua:
            path = os.path.join(ua.getPath(), self.__path.strip('/'))
            (_resID, errMsg) = itg.waitbox(_('Please wait while importing data...'), self.__importFile, (rrm,path))
        if (errMsg):
            itg.msgbox(itg.MB_OK, _('Error importing: %s' % errMsg))
        elif (rrm.isRebootRequested()):
            restartManager.rebootFromUI()
        elif (rrm.isRestartRequested()):
            restartManager.restartFromUI()
        else:
            itg.msgbox(itg.MB_OK, _('Import completed.'))

    def __importFile(self, restartReqManager, path):
        try:
            for filename in self.__files:
                log.dbg('Importing %s' % filename)
                fh = fileHandler.getFileHandlerForFile(filename)
                if (not fh):
                    raise Exception('no file handler for %s' % filename)
                elif (not hasattr(fh, 'fileImport')):
                    raise Exception('file handler for %s does not support import' % filename)
                data = open(os.path.join(path, filename), 'r').read()
                fh.fileImport(filename, data, restartReqManager)
        except Exception as e:
            return str(e)
        return None


class _ImportExplorerDialog(itg.Dialog):
    
    def __init__(self, base, path):
        super(_ImportExplorerDialog, self).__init__()
        self.__base = base
        self.__path = path
        view = itg.MenuView()
        view.setCancelButton(_('Cancel'), cb=self.quit)
        if (base != path):
            view.setBackButton(_('Back'), cb=self.quit)
        view.setTitle(str(self.__path).replace(base, 'USB:'))
        self.addView(view)
        self.__refresh()

    def __refresh(self):
        files = os.listdir(self.__path)
        files = filter(lambda f: (f[0] != '.'), files)
        files.sort()
        view = self.getView()
        view.removeAllRows()
        for f in files:
            absFile = os.path.join(self.__path, f)
            if (os.path.isdir(absFile)):
                cb = self.__onDirectory
            elif (fileHandler.getFileHandlerForFile(f) != None):
                cb = self.__onImportFile
            else:
                cb = None
            view.appendRow( f, hasSubItems=os.path.isdir(absFile), cb=cb, data=absFile)

    def __onDirectory(self, pos, row):
        path = row['data']
        self.runDialog(_ImportExplorerDialog(self.__base, path), invokeCancel=True)
    
    def __importFile(self, filename, fh, rrm):
        try:
            name = os.path.basename(filename)
            data = open(filename, 'r').read()
            fh.fileImport(name, data, rrm)
            return (True, None)
        except Exception as e:
            return (False, str(e))
        
    def __onImportFile(self, pos, row):
        filename = row['data']
        name = os.path.basename(filename)
        fh = fileHandler.getFileHandlerForFile(name)
        if not hasattr(fh, 'fileImport'):
            return
        resID = itg.msgbox(itg.MB_YES_NO, _('Do you want to import "%s"?') % name)
        if (resID == itg.ID_YES):
            rrm = fileHandler.RestartRequestManager()
            (_resID, (success, reason)) = itg.waitbox(_('Importing data, please wait...'), self.__importFile, (filename, fh, rrm))
            if (not success):
                itg.msgbox(itg.MB_OK, _('Import failed (%s)!') % reason)
            elif (rrm.isRebootRequested()):
                resID = itg.msgbox(itg.MB_YES_NO, _('Import completed. A terminal restart is required. Do you want to restart terminal now?'))
                if (resID != itg.ID_NO):
                    restartManager.rebootFromUI()
            elif (rrm.isRestartRequested()):
                resID = itg.msgbox(itg.MB_YES_NO, _('Import completed. An application restart is required. Do you want to restart application now?'))
                if (resID != itg.ID_NO):
                    restartManager.restartFromUI()
            else:
                itg.msgbox(itg.MB_OK, _('Import completed.'))
                

class ExportToUSBDialog(itg.PseudoDialog):
    
    def __init__(self, path=None, files=None):
        super(ExportToUSBDialog, self).__init__()
        self.__usbPath = path or os.path.join('IT-Exports', appit.AppInfo().name())
        self.__files = files
        if (not self.__files):
            self.__files = []
            for handler in fileHandler.getAll():
                if (hasattr(handler, 'fileExport') and hasattr(handler, 'getExportName')):
                    self.__files.append(handler.getExportName())

    def run(self):
        usbMountDlg = usbDialog.USBMountDialog()
        usbMountDlg.run()
        ua = usbMountDlg.getUSBAccess()
        if (not ua):
            return itg.ID_BACK
        # check directory
        path = os.path.join(ua.getPath(), self.__usbPath.strip('/'))
        if (os.path.exists(path)):
            resID = itg.msgbox(itg.MB_YES_NO, _('Export directory already exists, replace files with this export?'))
            if (resID != itg.ID_YES):
                return itg.ID_BACK
        (_resID, (success, reason)) = itg.waitbox(_('Exporting data to USB...'), self.__export, (path,))
        # manually release usb access object here before showing message
        ua.release()
        if (success):
            itg.msgbox(itg.MB_OK, _('Data was successfully exported to USB.'))
        else:
            itg.msgbox(itg.MB_OK, _('Failed to export data (%s).') % reason)
        return itg.ID_OK

    def __export(self, path):
        try:
            if (not os.path.exists(path)):
                os.makedirs(path)
            for filename in self.__files:
                handler =  fileHandler.getFileHandlerForFile(filename)
                if (handler != None and hasattr(handler, 'fileExport')):
                    data = handler.fileExport(filename)
                    if (data):
                        absFilename = os.path.join(path, filename)
                        with open(absFilename, 'w') as f:
                            f.write(data)
                            f.close()
                        open(absFilename + '.md5', 'w').write(hashlib.md5(data).hexdigest())
                elif (handler != None):
                    errMsg = 'file handler for %s does not support export' % filename
                    log.err(errMsg)
                    return (False, errMsg)
                else:
                    errMsg = 'no file handler for %s' % filename
                    log.err(errMsg)
                    return (False, errMsg)
        except Exception as e:
            log.err('Failed to export: %s' % str(e))            
            return (False, str(e))
        return (True, None)



def _getPlaceHolders():
    return  { '[DEVID]'      : getAppSetting('clksrv_id'),
              '[PARTNO]'     : cfg.get(cfg.CFG_PARTNO).replace('~', '-'),
              '[MAC]'        : cfg.get(cfg.CFG_NET_ETHADDR).replace(':', '').upper(),
              '[DATETIME]'   : time.strftime('%Y-%m-%d-%H%M%S') }


#
#
# Support functions for dynamic buttons
#
#
class UsbImportMenuAction(dynButtons.Action):
    
    def getName(self):
        return 'usb.import'
    
    def getButtonText(self, actionParam, employee, languages):
        return _('Import')
    
    def getDialog(self, actionParam, employee, languages):
        if (hasattr(actionParam, 'getParam')):
            path = actionParam.getParam('path')
            if (path):
                # get files and replace place holders
                placeHolders = _getPlaceHolders()
                files = []
                for f in actionParam.getList('files/file'):
                    for (p,v) in placeHolders.iteritems():
                        f = f.replace(p,v)
                    files.append(f)
                return ImportFilesDialog(path, files)
        return ImportFromUSBDialog()

    def getXsd(self):
        return """
            <xs:complexType>
                <xs:all>
                    <xs:element name="path" minOccurs="0" type="xs:string" />
                    <xs:element name="files" minOccurs="0">
                        <xs:complexType>
                            <xs:sequence maxOccurs="unbounded">
                                <xs:element name="file" type="xs:string" />
                            </xs:sequence>
                        </xs:complexType>
                    </xs:element>
                </xs:all>
            </xs:complexType>
        """

    def getHelp(self):
        return """
        Import application data from USB memory device.

        This action allows the user to browse a USB memory device
        and import supported files. This action is normally configured
        for the :ref:`action_app.setup` menu.
         
        
        Example::
        
            <button>
              <pos>1</pos>
              <action>
                <usb.import />
              </action>
            </button>
        
        This action can also be customised in a similar way to :ref:`action_usb.export`::

          <button>
            <pos>1</pos>
            <action>
              <usb.import>
                <path>/My-Exports</path>
                <files>
                  <file>tblEmps.xml</file>
                  <file>accountData.xml</file>
                </files>
              </usb.import>
            </action>
          </button>

        The example above configures the action to use a specific directory on a USB device
        and to import the given files.
        
        The same file place holders from :ref:`action_usb.export` can be used.

        """        

class UsbExportMenuAction(dynButtons.Action):
    
    def getName(self):
        return 'usb.export'
    
    def getButtonText(self, actionParam, employee, languages):
        return _('Export')
    
    def getDialog(self, actionParam, employee, languages):
        if (hasattr(actionParam, 'getParam')):
            path = actionParam.getParam('path')
            # get files and replace place holders
            placeHolders = _getPlaceHolders()
            files = []
            for f in actionParam.getList('files/file'):
                for (p,v) in placeHolders.iteritems():
                    f = f.replace(p,v)
                files.append(f)
            return ExportToUSBDialog(path, files)
        return ExportToUSBDialog()
    
    def getXsd(self):
        return """
            <xs:complexType>
                <xs:all>
                    <xs:element name="path" minOccurs="0" type="xs:string" />
                    <xs:element name="files" minOccurs="0">
                        <xs:complexType>
                            <xs:sequence maxOccurs="unbounded">
                                <xs:element name="file" type="xs:string" />
                            </xs:sequence>
                        </xs:complexType>
                    </xs:element>
                </xs:all>
            </xs:complexType>
        """

    def getHelp(self):
        return """
        Export application data to USB memory device.

        By default, the action allows the user to export all 
        exportable application data onto a USB memory device. The export
        will create an "IT-Exports" directory and a sub-directory
        with the application name. 
        
        This action is normally configured for the :ref:`action_app.setup` menu. 
        
        Example::
        
            <button>
              <pos>1</pos>
              <action>
                <usb.export />
              </action>
            </button>

        It is possible to specify action parameters to customise the behaviour::

          <button>
            <pos>1</pos>
            <action>
                <usb.export>
                  <path>/My-Exports</path>
                  <files>
                    <file>tblEmps.xml</file>
                    <file>accountData.xml</file>
                    <file>transactions-[DEVID]-[DATETIME].xml</file>
                  </files>
                </usb.export>
            </action>
          </button>
          
        The example above configures the action to use a different directory on the USB device.
        It also specifies which data to export and in which order.
        
        It is possible to put the following place holder tokens into the file names, which get 
        replaced by their actual value before the files are created.
        
         - *[DEVID]* - clockserver device ID (see :ref:`setting_clksrv_id`).
         - *[PARTNO]* - part number of terminal (e.g. "FP-IT51-LG-000020").
         - *[MAC]* - MAC address of terminal (e.g. "0001CE010E6F").
         - *[DATETIME]* - time stamp in "YYYY-mm-dd-HHMMSS" format.
        
        Example::
        
          <file>transactions-[DEVID]-[DATETIME].xml</file>

        """        




def loadPlugin():
    dynButtons.registerAction(UsbImportMenuAction())
    dynButtons.registerAction(UsbExportMenuAction())    


            
