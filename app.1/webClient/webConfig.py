# -*- coding: utf-8 -*-
#
# Copyright 2011 Grosvenor Technology
#

from applib.db.tblSettings import getAppSetting, getAppSettings
from applib.utils import jobs
import updateit
import cfg
import netinfo
import log

_setup = None
_jobQueue = None

def getAppWebClientSetup():
    """ Return global web client configuration. """
    global _setup
    if (not _setup):
        _setup = _createAppCommSetup()
    return _setup
    
def _createAppCommSetup():
    setup = WebClientSetup(getAppSetting('webclient_host'),
                       getAppSetting('webclient_ssl'),
                       getAppSetting('webclient_resource'),
                       getAppSetting('webclient_username'),
                       getAppSetting('webclient_password'),
                       getAppSetting('webclient_check_certificate'),
                       getAppSetting('clksrv_id')
             )
    return setup

def _isAutoFirmwareUpdateEnable():
    if (hasattr(cfg, 'CFG_FIRMWARE_AUTO_UPDATE_MODE')): # FwVer 3 and above
        if (cfg.get(cfg.CFG_FIRMWARE_AUTO_UPDATE_MODE) in ('bugfix', 'minor', 'major')):  # @UndefinedVariable
            return True
    elif (cfg.get(cfg.CFG_FIRMWARE_AUTO_UPDATE) == '1'): # FwVer 2 and lower
        return True
    return False
    
def overwriteAppWebClientSetup(host, ssl, resource, username, password, checkCertificate, deviceID):
    """ Overwriting global web client configuration. """
    global _setup
    _setup = WebClientSetup(host, ssl, resource, username, password, checkCertificate, deviceID)

def resetAppWebClientSetup():
    """ Resets global web client setup (when it was overwritten by *overwriteAppWebClientSetup*. """
    global _setup
    _setup = None


class WebClientSetup(object):
    
    def __init__(self, host, ssl, resource, username, password, checkCertificate, deviceID):
        self.__host = host
        self.__ssl = ssl
        self.__resource = resource
        self.__username = username
        self.__password = password
        self.__checkCertificate = checkCertificate
        self.__deviceID = deviceID
        self.__mac = cfg.get(cfg.CFG_NET_ETHADDR)
        self.__token = getAppSetting('webclient_auth_token')
        self.__supportFirmwareUpdates = not _isAutoFirmwareUpdateEnable()
        self.__partno = cfg.get(cfg.CFG_PARTNO)
       
    def getHost(self):
        return self.__host
    
    def getHostOnly(self):
        """Extracts and returns the host portion of the host address, removing any
        port specification."""
        parts = self.__host.split(":")
        if len(parts) > 1:
            host = parts[0]
        else:
            host = self.__host
        return host

    def getPort(self):
        """Extracts and returns the port number, if any, from the host 
        address. If no port number is included, port 80 is returned, or 443 
        if SSL is active."""
        
        # Set up a default
        if self.isSSL():
            port = 443
        else:
            port = 80
            
        # Check for a port in the host string
        parts = self.__host.split(":")
        if len(parts) > 1:
            try:
                port = int(parts[-1])
            except:
                log.err('Could not extract port number from host %s' % self.__host)
                
        return port
                    
    def isSSL(self):
        return self.__ssl
    
    def getResourcePrefix(self):
        return self.__resource
    
    def getUsername(self):
        return self.__username
    
    def getPassword(self):
        return self.__password
    
    def getToken(self):
        return self.__token
    
    def checkCertificate(self):
        return self.__checkCertificate        
    
    def setToken(self, token):
        if (self.__token != token):
            self.__token = token
            getAppSettings().set('webclient_auth_token', token)
    
    def getDeviceType(self):
        return updateit.get_type()
    
    def getMAC(self):
        return self.__mac
        
    def getIP(self):
        return '.'.join( [ str(int(i,10)) for i in netinfo.get_info().ip4_addr.split(".") ] )        
        
    def getDeviceID(self):
        return self.__deviceID 
    
    def supportFirmwareUpdates(self):
        return self.__supportFirmwareUpdates

    def getSerialNumber(self):
        return self.__partno

def getJobQueue():
    global _jobQueue
    if (_jobQueue == None):
        _jobQueue = jobs.JobQueue('WebClientJobQueue')
    return _jobQueue


def getJobUITimeout():
    to = getAppSetting('webclient_ui_timeout')
    if (to == None):
        log.warn('Invalid UI timeout, using default of 10s')
        return 10
    return to
