# -*- coding: utf-8 -*-
#
# Copyright 2011 Grosvenor Technology
#


from applib.utils import healthMonitor, restartManager
from applib.db.tblSettings import SettingsSection, NumberSetting, TextSetting, ListSetting, MultiListSetting, BoolSetting
from engine import fileHandler
from clockserver.comm import getCommForPrefix, getCommForFunction
from clockserver.heartbeat import getAppPrimaryHeartbeat, getAppSecondaryHeartbeat, testConfiguredConnection, getAppHeartbeatForEnquiries
from clockserver.clockserverSettings import getClockserver1Settings, getClockserver2Settings, heartbeatOnly

if (not heartbeatOnly):
    from clockserver.transaction import getAppTransactions
    from clockserver.enquiry import EnquiryJob, getAppEnquiryQueue


def load():
    """Initialise clockserver module"""
    # create heartbeat and transaction tables
    getAppPrimaryHeartbeat()
    getAppSecondaryHeartbeat()
    if (not heartbeatOnly):
        getAppTransactions()

def start():
    """Start all background threads. """
    hm = healthMonitor.getAppHealthMonitor()
    hb1 = getAppPrimaryHeartbeat()    
    if (hb1):
        hb1.start(getCommForPrefix('clksrv', 'primary'))
        hm.add(hb1)
    hb2 = getAppSecondaryHeartbeat()
    if (hb2):
        hb2.start(getCommForPrefix('clksrv2', 'secondary'))
        hm.add(hb2)
    if (not heartbeatOnly):
        trans = getAppTransactions()
        if (trans):
            trans.open(getCommForFunction('trans'))
            hm.add(trans)
    restartManager.registerCleanup(stop)


def stop():
    """ Stop threads used by clockserver."""
    if (getAppPrimaryHeartbeat()):
        getAppPrimaryHeartbeat().stop()
    if (getAppSecondaryHeartbeat()):
        getAppSecondaryHeartbeat().stop()
    if (not heartbeatOnly):
        if (getAppTransactions()):
            getAppTransactions().close()
        if (getAppEnquiryQueue(False)):
            getAppEnquiryQueue().stop()


# def getHelp(appInfo):
#     return """
# Custom Exchange
# ===============
#  
# This is still to come...
#  
# """