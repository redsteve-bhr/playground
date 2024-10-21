# -*- coding: utf-8 -*-
#
"""
.. currentmodule:: applib.gui

:mod:`usbDialog` --- Dialogs for accessing USB/MMC devices
==========================================================

.. versionadded:: 2.4

The :mod:`usbDialog` module provides a dialog that can be used to mount a USB or
MMC memory device and acquire a :class:`~applib.utils.usbAccess.USBAccess` object.
The dialog prompts the user to select a device and partition before mounting the device and
acquiring a :class:`~applib.utils.usbAccess.USBAccess` object. The selection dialogs are 
omitted if there is only one item to choose from.

.. seealso::
    :mod:`applib.utils.usbAccess`
    

"""



import itg
import threading
from applib.utils import usbAccess

class USBMountDialog(itg.WizardDialog):
    """ Dialog to get :class:`~applib.utils.usbAccess.USBAccess` object of the selected USB/MMC memory
        device.
        
        Example::

            usbMountDlg = usbDialog.USBMountDialog()
            usbMountDlg.run()
            ua = usbMountDlg.getUSBAccess()
            if (not ua):
                return
            with ua:
                dlg = _ImportExplorerDialog(ua)
                dlg.run()


    """
    
    def run(self):
        self.__usbData = _USBWizardData()
        devs = usbAccess.getDevices()
        if (not devs):
            cancelEvent = threading.Event()
            itg.waitbox(_('Please plug-in USB memory device'), self.__waitForUsb, (devs, cancelEvent), self.__cancelWaiting)
        if (not devs):
            return
        self.__usbData.setDevices(devs)
        pages = (_SelectDevicePage(self.__usbData),
                 _SelectPartitionPage(self.__usbData),
                 _MountPartitionPage(self.__usbData))
        self._runWizard(pages)
        return self.getResultID()

    def __cancelWaiting(self, devs, cancelEvent):
        cancelEvent.set()
        
    def __waitForUsb(self, devs, cancelEvent):
        while not cancelEvent.isSet() and not devs:
            cancelEvent.wait(1)
            devs.extend(usbAccess.getDevices())
            
    def getUSBAccess(self):
        """ Return :class:`~applib.utils.usbAccess.USBAccess` object or **None**. """
        return self.__usbData.getUSBAccess()


class _USBWizardData(object):
    
    def __init__(self):
        self.__devs = []
        self.__dev  = None
        self.__part = None
        self.__ua   = None
    
    def setDevices(self, devices):
        self.__devs = devices
 
    def getDevices(self):
        return self.__devs
    
    def selectDevice(self, dev):
        self.__dev = dev
        
    def getSelectedDevice(self):
        return self.__dev
        
    def selectPartition(self, part):
        self.__part = part
        
    def getSelectedPartition(self):
        return self.__part

    def setUSBAccess(self, ua):
        self.__ua = ua
    
    def getUSBAccess(self):
        return self.__ua


class _SelectDevicePage(itg.Dialog):
        
    def __init__(self, usbData):
        super(_SelectDevicePage, self).__init__()
        self.__usbData = usbData
        view = itg.ListView(_('Please select device'))
        view.setOkButton(_('Next'), cb=self.__onOk)
        view.setCancelButton(_('Cancel'), cb=self.cancel)
        self.addView(view)

    def onRefreshData(self):
        view = self.getView()
        view.removeAllRows()
        for dev in self.__usbData.getDevices():
            name = dev.getName()
            if (dev.isInUse()):
                name += _(' (in use)')
            view.appendRow(name, data=dev)
        
    def __onOk(self, btnID):
        row = self.getView().getSelectedRow()
        self.__usbData.selectDevice(row['data'])
        self.quit(btnID)        
          
    def skip(self):
        if (len(self.__usbData.getDevices()) == 1):
            self.__usbData.selectDevice(self.__usbData.getDevices()[0])
            return True
        return False
    

class _SelectPartitionPage(itg.Dialog):
        
    def __init__(self, usbData):
        super(_SelectPartitionPage, self).__init__()
        self.__usbData = usbData
        view = itg.ListView(_('Please select partition'))
        view.setOkButton(_('Next'), cb=self.__onOk)
        view.setBackButton(_('Back'), cb=self.back)        
        view.setCancelButton(_('Cancel'), cb=self.cancel)
        self.addView(view)

    def onRefreshData(self):
        view = self.getView()
        view.removeAllRows()
        for p in self.__usbData.getSelectedDevice().getPartitions():
            name = p.getname()
            if (p.isInUse()):
                name += _(' (in use)')
            view.appendRow(name, data=p)
        
    def __onOk(self, btnID):
        row = self.getView().getSelectedRow()
        self.__usbData.selectPartition(row['data'])
        self.quit(btnID)
        
    def skip(self):
        parts = self.__usbData.getSelectedDevice().getPartitions()
        if (len(parts) == 1):
            self.__usbData.selectPartition(parts[0])
            return True
        return False


class _MountPartitionPage(itg.PseudoDialog):
    
    def __init__(self, usbData):
        super(_MountPartitionPage, self).__init__()
        self.__usbData = usbData
        
    def run(self):
        (_resID, errMsg) = itg.waitbox(_('Please wait...'), self.__mount)
        if (errMsg):
            itg.msgbox(itg.MB_OK, _('An error occurred: %s') % errMsg)
        return itg.ID_NEXT
    
    def __mount(self):
        try:
            ua = self.__usbData.getSelectedPartition().getUSBAccess()
            self.__usbData.setUSBAccess(ua)
        except Exception as e:
            return str(e)
    

