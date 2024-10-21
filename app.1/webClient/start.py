# -*- coding: utf-8 -*-
#
# Copyright 2015 Grosvenor Technology
#
from applib.utils import healthMonitor, periodicScheduler
from applib.db.tblSettings import getAppSetting

from syncChanges import syncChanges
from transaction import getAppTransactions
from employeeUpdates import getAppEmpUpdatesQueue
import onlineState


def load():
    """ Nothing to do, but keep here for compatibility """
    pass
    
def start():
    """ Start web client threads and background tasks. """
    hm = healthMonitor.getAppHealthMonitor()
    # start transaction thread
    trans = getAppTransactions()
    if (trans):
        trans.startThread()
        hm.add(trans)
    # start employee updates thread
    empUpdatesQueue = getAppEmpUpdatesQueue()
    if (empUpdatesQueue):
        empUpdatesQueue.startThread()
        hm.add(empUpdatesQueue)
    # start online state thread
    onlineStateThread = onlineState.OnlineState()
    onlineStateThread.start()
    hm.add(onlineStateThread)
    # start web sync 
    periodicScheduler.add('WebService Sync', 
                  syncChanges,
                  getAppSetting('webclient_changes_sync_period'), 
                  getAppSetting('webclient_retry_time'),
                  5, True)
    
