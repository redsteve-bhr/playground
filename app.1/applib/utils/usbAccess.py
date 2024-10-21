# -*- coding: utf-8 -*-
#
# Copyright 2010 Grosvenor Technology
#
"""
:mod:`usbAccess` --- Access USB memory device
=============================================

.. versionadded:: 1.2


This module contains functions and classes to access
USB/MMC memory devices and make accessing it from different
parts of software easy.
  
    
.. versionchanged:: 2.4
  Support for multiple USB memory devices added
      
.. important::
  Especially since version 2.4, applications must not assume "/mnt/usb" 
  as mount point and always use :meth:`USBAccess.getPath`.
        
"""

import threading
import log
import os
import glob

_usbUsers = {}
_usbLock  = threading.Lock()


class USBAccess(object):
    """ Mount and lock USB memory device.

    This helper class makes it easy to use and share USB memory devices
    by different parts of the software. The USB memory device will be mounted
    when used first and automatically unmounted when not used anymore.
    
    Example::
    
        try:
            ua = USBAccess()
            with ua:
                fileName = os.path.join(ua.getPath(), 'fileOnUSB.txt')
                f = open(fileName, 'w')
                f.write('Hello World')
                f.close()
        except NoWorkingUSBDeviceFoundException as e:
            log.err('No USB device found (%s)!' % e)
        
    In the example above the USB device is unmounted when *ua* is freed by
    the garbage collector.
    
    If there is more than one USBAccess object, only the first will mount
    the USB device and only when freeing the last will the USB device get unmounted.

    .. versionadded:: 1.2
    
    .. versionchanged:: 2.4
        Added optional devNode parameter.
    
    """
        
    def __init__(self, devNode=None):
        self.__devNode = None
        self.__mountPoint = None
        with _usbLock:
            if (devNode != None):
                (self.__devNode, self.__mountPoint) = self.__acquire(devNode)
            elif (len(_usbUsers) > 0):
                # use already mounted device
                (self.__devNode, self.__mountPoint) = self.__acquire(_usbUsers.keys()[0])
            else:
                # no USB mounted, detect devices and try them
                for usbDev in getDevices():
                    for usbPart in usbDev.getPartitions():
                        try:
                            (self.__devNode, self.__mountPoint) = self.__acquire(usbPart.getDevNode())
                            return
                        except USBDeviceMountException:
                            pass
            if (self.__devNode == None):
                raise NoWorkingUSBDeviceFoundException('No working USB devices found')
            
    def __acquire(self, devNode):
        mountPoint = '/tmp/mnt_%s' % (devNode.replace('/', '_'))
        if ((devNode not in _usbUsers) or _usbUsers[devNode] == 0):
            self._mountUSB(devNode, mountPoint)
        if (not os.path.ismount(mountPoint)):
            log.warn("USB should be mounted, but it isn't!")
            self._mountUSB(devNode, mountPoint)
        if (not os.path.ismount(mountPoint)):
            raise USBDeviceMountException()
        if (devNode in _usbUsers):
            _usbUsers[devNode] += 1
        else:
            _usbUsers[devNode] = 1
        log.dbg('New USB user, now %d users, %d devices' % (_usbUsers[devNode], len(_usbUsers)))
        return (devNode, mountPoint)

    def getPath(self):
        """ Return the mountpoint of the USB memory device."""
        return self.__mountPoint
    
    def release(self):
        """ Release access and unmount USB device if no other access object
            is active. This method is called automatically when the access
            object is no longer needed, so it is normally not necessary to 
            call it.
            
            .. versionadded:: 2.4
            
        """
        if (self.__devNode == None):
            return
        with _usbLock:
            if (self.__devNode in _usbUsers):
                _usbUsers[self.__devNode] -= 1
                if (_usbUsers[self.__devNode] <= 0):
                    self._unmountUSB(self.__mountPoint)
                    del _usbUsers[self.__devNode]
                    log.dbg('Removed USB user and device, %d devices left' % len(_usbUsers))
                else:
                    log.dbg('Removed USB user, now %d users, %d devices' % (_usbUsers[self.__devNode], len(_usbUsers)))
            else:
                log.warn('USB user count invalid!')
            self.__devNode = None
    
    def __enter__(self):
        pass
        
    def __del__(self):
        self.release()

    def __exit__(self, exc_type, exc_value, traceback):
        self.release()

    def _mountUSB(self, devNode, mountPoint):
        log.dbg('Mounting %s to %s' % (devNode, mountPoint))
        if (not os.path.exists(mountPoint)):
            os.mkdir(mountPoint)
        if (os.path.ismount(mountPoint)):
            log.warn('Mount point is already in use, trying to unmount...')
            self._unmountUSB(mountPoint, removeMountPoint=False)
            if (os.path.ismount(mountPoint)): # Not sure on raising an exception...
                raise USBDeviceMountException('a device is already mounted')
        res = os.system('/bin/mount -tvfat -o sync %s %s' % (devNode, mountPoint))
        if (res != 0):
            os.rmdir(mountPoint)
            raise USBDeviceMountException('failed to mount device')

    def _unmountUSB(self, mountPoint, removeMountPoint=True):
        log.dbg('Unmounting %s' % (mountPoint,))
        if (not os.path.ismount(mountPoint)):
            return
        res = os.system('/bin/umount %s' % mountPoint)
        if (res == 0):
            if (removeMountPoint):
                os.rmdir(mountPoint)
        else:
            log.warn('Failed to unmount device!')    
            # don't raise exception
        


class NoWorkingUSBDeviceFoundException(Exception):
    pass

class USBDeviceMountException(Exception):
    pass


def getDevices():
    """ Return list of detected USB/MMC devices (:class:`USBDevice`). 
    
        .. versionadded:: 2.4
    
    """
    devs = []
    # check for USB
    usbDevs = sorted(glob.glob('/dev/sd[a-z]'))
    for dev in usbDevs:
        parts = glob.glob('%s[0-9]' % dev) 
        if (not parts):
            parts = [ dev, ]
        parts = [ USBDevicePartition(p) for p in parts]
        parts = sorted(parts, key=lambda i:i.getName())            
        devs.append( USBDevice(dev, parts) )
    # check for MMC
    mmcPartitions = [ USBDevicePartition(p) for p in glob.glob('/dev/mmcblk0p[0-9]') ]
    if (mmcPartitions):
        mmcPartitions = sorted(mmcPartitions, key=lambda i:i.getName())
        devs.append( USBDevice('/dev/mmcblk0', mmcPartitions) )
    return devs


class USBDevice(object):
    """ Class representing a USB or MMC device. 
    
        .. versionadded:: 2.4
    
    """
    
    def __init__(self, devNode, partitions):
        self.__devNode = devNode
        self.__name = self.__findName()
        self.__partitions = partitions
    
    def __findName(self):
        if (self.__devNode.startswith('/dev/mmcblk')):
            return 'MMC'
        devName = os.path.basename(self.__devNode)
        usbName = 'USB %d:' % (ord(devName[2])-ord('a')+1) 
        try:
            vendor = open('/sys/block/%s/device/vendor' % devName).read().strip()
            model  = open('/sys/block/%s/device/model' % devName).read().strip()
            return ' '.join( (usbName, vendor, model) )
        except:
            return usbName

    def getName(self):
        """ Return human readable name of device. """
        return self.__name
    
    def getPartitions(self):
        """ Return list of partitions (:class:`USBDevicePartition`). """
        return self.__partitions

    def isInUse(self):
        """ Return **True** if any of the partitions are mounted. """
        for part in self.__partitions:
            if (part.isInUse()):
                return True
        return False


class USBDevicePartition(object):
    """ Class representing a USB or MMC memory device partition.
    
        .. versionadded:: 2.4
    
    """
    
    def __init__(self, devNode):
        self.__devNode = devNode
    
    def getName(self):
        """ Return human readable name of partition. """
        if (self.__devNode.startswith('/dev/sd')):
            return 'Partition %s' % self.__devNode[8:]
        elif (self.__devNode.startswith('/dev/mmcblk')):
            return 'Partition %s' % self.__devNode[13:]
        return 'Partition (%s)' % self.__devNode
    
    def getDevNode(self):
        """ Return filename of device node (e.g. /dev/sda1). """
        return self.__devNode
    
    def getUSBAccess(self):
        """ Return USB access object. """
        return USBAccess(self.__devNode)
    
    def isInUse(self):
        """ Return **True** if mounted. """
        return (self.__devNode in _usbUsers)


