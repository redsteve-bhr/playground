# -*- coding: utf-8 -*-
#
# Copyright 2010 Grosvenor Technology
#

"""
:mod:`healthMonitor` --- Health Monitor
=======================================

The health monitor provides a way of monitoring the health condition of
several software components. It is doing this by querying the health
status of registered components periodically. 

It can also display icons on a :class:`itg.IdleMenuView` in case a component
is reporting a health problem.

Example::

    class Dialog(itg.Dialog):
    
        def __init__(self):
            super(Dialog, self).__init__()
            view = itg.IdleMenuView()
            # [...]  
            self.addView(view)
            self.disableTimeout()
            # enable health monitor
            hm = healthMonitor.getAppHealthMonitor()
            hm.setIconView(view)
            hm.start()
            

The health monitor will monitor network, AC power and Wifi signal strength by default. 

It is possible to monitor additional components by adding them into the health monitor. The only requirement
is to implement a ``getHealth()`` and ``getWarnings()`` function::

    class HealthObject(object):
        
        def getWarnings(self):
            warnings = []
            if (self.__hasProblemA()):
                warnings.append( {'msg': _('Problem A occurred') })
            if (self.__hasProblemB()):
                warnings.append( {'msg': _('Problem B occurred') })            
            return warnings
    
        def getHealth(self):
            name    = _('Health Object')
            healthy = (not self.__hasProblemA() and not self.__hasProblemB())
            items = [ ('Status',  self.__getStatus()),
                      ('DetailA', self.__getDetailA()),
                      ('DetailB', self.__getDetailB()) ]                      
            return (name, healthy, items)

        # [...]

                
The :meth:`~HealthMonitor.add` function will add the HealthObject to the health monitor::

    hm = healthMonitor.getAppHealthMonitor()
    ho = HealthObject()
    hm.add(ho)
    
The health monitor expects an array of warnings from the ``getWarnings()`` function. In
case of no warnings, an empty array shall be returned. The array should contain 
a dictionary per warning with at least the 'msg' key set. In addition to this, a 
warning can also have its own icon::

    warnings = []
    if self.errorCondition:
        warnings.append( {'msg': 'My warning!', 'icon': 'mywarning.bmp' })
    return warnings

The ``getWarnings()`` function will be called periodically and must not block the program
flow (take too much time). 

The ``getHealth()`` function is expected to return a tuple with a name, the health status 
and a list of items to display (or None if there is nothing to display). The name will appear
in the health status overview. The state of each component will
be shown as either "good" or "bad" depending on the health status (second element in 
list). If the third element is not None, a sub menu will also display all items. This
can be used to show details of the component like transfered bytes or when the last 
error occurred.    


Polling Interval
----------------

.. versionadded:: 1.5

The default polling interval is a second, which means that ``getWarnings()`` is called
every second on all monitored objects. Some monitored objects may prefer a longer time
interval.
By defining ``healthMonitorUpdatePeriod``, each monitored object can customise its own
polling interval.

Example:: 

    class TblEmps(Table):
    
        healthMonitorUpdatePeriod = 20
     
In the example above, ``getWarnings()`` is only called every 20 seconds. 


"""

import os
import log
import threading
import netinfo
import hw
import itg
import cfg
import time
import weakref

from applib.utils import resourceManager
from applib.db.tblSettings import getAppSetting 

_appHealthMonitor = None

def getAppHealthMonitor():
    global _appHealthMonitor
    if (_appHealthMonitor == None):
        _appHealthMonitor = HealthMonitor()
    return _appHealthMonitor


class HealthMonitor(threading.Thread):
    """Health monitor class.
    
    If *monitor_ac* is **True** the health monitor will monitor AC power
    and show a warning icon when the terminal is running on battery. If
    *monitor_link* is **True** the health monitor will monitor the network
    status as well and show a warning icon when there is no network link
    or no DHCP response. It will also show network details like IP address
    in :class:`applib.gui.health.HealthMonitorDialog`. If *signal_strength*
    is **True** and the wireless network interface is used the health monitor
    will show the signal strength or a warning icon if no wireless network 
    is connected. 
    
    .. note::
        :class:`HealthMonitor` is derived from *threading.Thread* and runs 
        in the background to monitor all objects. Call :meth:`HealthMonitor.start()`
        to start the thread. 
        
    .. versionchanged:: 4.0
        Add *monitor_diskspace* option.
        
    """

    def __init__(self, monitor_ac=True, monitor_link=True, signal_strength=True, monitor_diskspace=True):
        super(HealthMonitor, self).__init__()
        self.__stopEvent = threading.Event()
        self.__lock = threading.Lock()
        self.__objs  = {}
        self.__icons = set()
        self.__warnIcon = resourceManager.get('applib/icons/warn')
        self.__idleView = None
        self.__signalStrengthMonitor = None

        if (monitor_ac):
            self.add(_MonitorAC())
        if (monitor_link):
            self.add(_MonitorNetwork())
        if (signal_strength):
            if (cfg.get(cfg.CFG_NET_INTERFACE) == 'wlan'):
                self.__signalStrengthMonitor = _MonitorWLanSignalStrength()
        if (monitor_diskspace):
            self.add(_MonitorDiskSpace())

    def setIconView(self, iconView):
        """ Assign :class:`itg.IdleMenuView` for showing icons.
        
        .. versionchanged:: 1.6
          Only keeping a weak reference of ``iconView``.

        """
        self.__idleView = weakref.ref(iconView) if iconView != None else None

    def add(self, obj):
        """Add new object to monitor.
        
        The object must implement a getHealth() and getWarnings() method.
        """
        if (obj == None):
            return
        with self.__lock:
            if obj not in self.__objs:
                self.__objs[obj] = []

    def remove(self, obj):
        """Remove monitored object."""
        with self.__lock:        
            if obj in self.__objs:
                del self.__objs[obj]
            else:
                log.warn('Unable to remove object from health monitor (%s)' % obj)
            
    def run(self):
        log.dbg('HealthMonitor started')
        self.__stopEvent.clear()
        while (not self.__stopEvent.isSet()):
            self.__stopEvent.wait(1)
            with self.__lock:
                try:
                    self.__update()
                except Exception as e:
                    log.err('Error while updating health monitor (%s)' % e)
        log.dbg('HealthMonitor stopped')
    
    def start(self):
        if (not self.isAlive()):
            super(HealthMonitor, self).start()

    def stop(self):
        self.__stopEvent.set()
        self.join()

    def __update(self):
        icons = set()
        # go through all objects to monitor
        for o in self.__objs.keys():
            try:
                if not hasattr(o, 'getWarnings'):
                    continue
                if (self.__useLastWarnings(o)):
                    # get cached warnings
                    self.__objs[o] = o.healthMonitorLastWarnings
                else:
                    # get up-to-date warnings
                    self.__objs[o] = o.getWarnings()
                    if (hasattr(o, 'healthMonitorUpdatePeriod')):
                        o.healthMonitorLastUpdate = time.time()
                        o.healthMonitorLastWarnings = self.__objs[o]
                # add icon for each warning to icon set
                # (if icon is not set, use default)
                for warning in self.__objs[o]:
                    if 'icon' in warning:
                        icons.add(warning['icon'])
                    else:
                        icons.add(self.__warnIcon)
            except Exception as e:
                log.err('Error in HealthMonitor (%s)' % e)

        # adding or removing icons only works with idlemenu
        idleView = self.__idleView() if (self.__idleView != None) else None
        if not idleView:
            return
        
        # update signal strength
        if (self.__signalStrengthMonitor):
            self.__signalStrengthMonitor.updateSignalStrengthIcon(idleView) 

        # no new icons?
        if (icons == self.__icons):
            return

        # add new icons
        for i in (icons - self.__icons):
            itg.runLater(idleView.addIcon, (i, self.__onHealthStatus))

        # remove unused icons
        for i in (self.__icons - icons):
            itg.runLater(idleView.removeIcon, (i,))
        
        # remember currently used icons
        self.__icons = icons
        
    def __useLastWarnings(self, obj):
        if (hasattr(obj, 'healthMonitorUpdatePeriod') and hasattr(obj, 'healthMonitorLastUpdate') and hasattr(obj, 'healthMonitorLastWarnings')):
            lastTime = time.time() - obj.healthMonitorLastUpdate
            if (lastTime > 0 and lastTime < obj.healthMonitorUpdatePeriod):
                return True
        return False
        
    def __onHealthStatus(self):
        from applib.gui.health import HealthMonitorDialog
        HealthMonitorDialog().run()
        
    def getWarnings(self):
        """Get number of active warnings."""
        with self.__lock:
            w = 0
            for o in self.__objs.values():
                w += len(o)
            return w

    def getHealthStatus(self):
        with self.__lock:
            items = []
            for o in self.__objs.keys():
                if not hasattr(o, 'getHealth'):
                    continue
                items.append(o.getHealth())
            return items


class _MonitorNetwork(object):
    
    def __init__(self):
        self.__netInterface = cfg.get(cfg.CFG_NET_INTERFACE)
        
    def getWarnings(self):
        warnings = []
        # get link status
        nolink = (netinfo.eth_status() == netinfo.ETH_STATUS_NO_LINK)
        icon = resourceManager.get('applib/icons/nolink')
        if nolink:
            warnings.append( {'msg': _('No network link'), 'icon': icon })
        ni = netinfo.get_info()
        if (ni.mode == netinfo.MODE_DHCP and not ni.ip4_addr):
            warnings.append( {'msg': _('No IP address from DHCP server'), 'icon': icon})            
        return warnings

    def getHealth(self):
        name    = _('Network')
        (healthy, items) = self.__getNetHealth()
        if (self.__netInterface == 'wlan'):
            items.extend(self.__getWLanHealth())
        return (name, healthy, items)
    
    def __getNetHealth(self):
        ni = netinfo.get_info()
        if (netinfo.eth_status() == netinfo.ETH_STATUS_NO_LINK):
            status = 'no link'
            healthy = False
        elif (ni.mode == netinfo.MODE_DHCP and not ni.ip4_addr):
            status = 'DHCP failed'
            healthy = False
        else:
            status = 'has link'
            healthy = True
        mode  = 'DHCP' if (ni.mode == netinfo.MODE_DHCP) else 'Static IP'
        items = [ ('Status',  status),
                  ('Mode',    mode),
                  ('MAC',      ni.mac_addr),
                  ('IP Address', ni.ip4_addr),
                  ('Netmask',  ni.ip4_mask),
                  ('Gateway',  ni.ip4_gateway),
                  ('DNS 1',    ni.ip4_dns1),
                  ('DNS 2',    ni.ip4_dns2)]
        return (healthy, items)
    
    def __getWLanHealth(self):
        strength = netinfo.wlan_quality()
        if (strength < 0):
            return []
        else:
            return [ ('Link Quality', '%s/100' % strength)]
                

class _MonitorAC(object):
 
    def getWarnings(self):
        warnings = []
        # get AC status
        if hw.ac_off():
            icon = resourceManager.get('applib/icons/ac_off')
            warnings.append( { 'msg': _('No AC power'), 'icon': icon } )
        return warnings

    def getHealth(self):
        name    = _('Power')
        healthy = not hw.ac_off()
        return (name, healthy, None)
                

class _MonitorWLanSignalStrength(object):

    def __init__(self):
        self.__strengthIcon = [ resourceManager.get('applib/icons/signalStrength%d' % i) for i in xrange(6) ]
        self.__errorIcon = resourceManager.get('applib/icons/signalStrengthError')
        self.__curIcon = None
    
    def __getIcon(self):
        try:
            signalStrength = netinfo.wlan_quality()
            if (signalStrength < 0):
                return None
            elif (signalStrength == 0):
                return self.__errorIcon
            return self.__strengthIcon[int(6 * signalStrength / 101)]
        except:
            return self.__errorIcon

    def updateSignalStrengthIcon(self, idleView):
        newIcon = self.__getIcon()
        if (newIcon == self.__curIcon):
            return
        if (self.__curIcon != None):
            itg.runLater(idleView.removeIcon, (self.__curIcon,))
        if (newIcon != None):
            itg.runLater(idleView.addIcon, (newIcon,))
        self.__curIcon = newIcon

class _MonitorDiskSpace(object):

    def __init__(self):
        self.healthMonitorUpdatePeriod = 30
        self.minDiskSpace = getAppSetting('app_min_diskspace')
            
    def checkDiskSpace(self):
        # Note: Eclipse will mark statvfs as being undefined, because this 
        # function is POSIX-only and does not exist under Windows. It will
        # work correctly when run on the terminal.
        stat = os.statvfs('/mnt/user/')
        total_space = (stat.f_frsize * stat.f_blocks) / 1048576.00
        free_space = (stat.f_frsize * stat.f_bfree) / 1048576.00 # Free space in MB
        return (total_space, free_space)
        
    def getWarnings(self):
        warnings = []
        (_total_space, free_space) = self.checkDiskSpace()
        if free_space < self.minDiskSpace:
            icon = resourceManager.get('applib/icons/warn')
            warnings.append( { 'msg': '{}'.format(free_space), 'icon': icon } )

        return warnings
    
    def getHealth(self):
        name = _('Disk Space')
        (total_space, free_space) = self.checkDiskSpace()
        healthy = free_space >= self.minDiskSpace
        total_space_str = '{:.2f} MB'.format(total_space)
        free_space_str = '{:.2f} MB'.format(free_space)
        items = [ 
            ('Disk Size',  total_space_str), 
            ('Free Space', free_space_str ) 
        ]
        return (name, healthy, items)
