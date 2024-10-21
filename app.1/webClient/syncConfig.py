# -*- coding: utf-8 -*-

import commsHelper
from contextlib import closing
import log
import updateit
from engine import fileHandler
from applib.utils import restartManager
from applib.db.tblSettings import getAppSettings
from webConfig import getAppWebClientSetup
import urllib
import xml.etree.cElementTree as ET


def _downloadConfigTypeIDToBuffer(configTypeID):
    rxData = ''
    # twice as fast as saving in one chunk
    with closing(commsHelper.openHttpConnection()) as conn:
        stream = commsHelper.httpStreamRequest(conn, 'GET', '/devices/%s/config/%s' % (getAppWebClientSetup().getDeviceID(), configTypeID))
        revision = stream.getheader('X-Revision')
        while True:
            data = stream.read(1024)
            if not data: break
            rxData += data
    return (revision, rxData)

def _importFile(filename, data, restartReqManager):
    for handler in fileHandler.getAllFileHandlersForFile(filename):
        handler.fileImport(filename, data, restartReqManager, isDefaultData=False)
    


def updateFirmware(remoteFilename):
    #updateit -f -p -u http://172.16.46.32:8080/api/devices/GB1111-1/config/IT5100-fw-IT5100.2.3.4-141010.bin update
    # http://username:password@172.16.46.32:8080/api/devices/GB1111-1/config/IT5100-fw-IT5100.3.0-beta1-150131.bin
    setup = getAppWebClientSetup()
    if (not setup.getToken()):
        unamePswd = ''
    else:
        unamePswd = "%s:%s@" % ( urllib.quote(setup.getDeviceID()),  urllib.quote(setup.getToken()) )
    proto = 'https' if setup.isSSL() else 'http'
    resource = urllib.quote('%s/devices/%s/config/%s' % (setup.getResourcePrefix(), setup.getDeviceID(), remoteFilename))
    url = '%s://%s%s%s' % (proto, unamePswd, setup.getHost(), resource)
    log.info('Updating firmware resource = %s' % url)
    result = updateit.update(url)
    if (result == updateit.SUCCESS):
        log.info('Firmware updated, rebooting terminal...')
        restartManager.reboot()
    else:
        raise Exception('Error updating firmware (%s,%s)' % (result, updateit.lastNetworkError()))    
    

def updateApplication(remoteFilename):
#     log.err('NOT INSTALLING APP DEBUG ONLY! (%s)' % remoteFilename)
#     return 
    restartReqManager = fileHandler.RestartRequestManager()
    (_revision, data) = _downloadConfigTypeIDToBuffer(remoteFilename)
    log.info('Updating application (%s)...' % remoteFilename)
    _importFile('application.app', data, restartReqManager)
    if (restartReqManager.isRebootRequested()):
        log.info('Application updated, rebooting terminal...')
        restartManager.reboot(30)
    elif (restartReqManager.isRestartRequested()):
        log.info('Application updated, restarting application...')
        restartManager.restart(30)
    

def updateButtons(restartReqManager):
    (revision, data) = _downloadConfigTypeIDToBuffer('buttons.xml')
    _importFile('buttons.xml', data, restartReqManager)
    getAppSettings().set('webclient_buttons_revision', revision)

    
def updateItcfg(restartReqManager):
    (revision, data) = _downloadConfigTypeIDToBuffer('itcfg.xml')
    _importFile('itcfg.xml', data, restartReqManager)
    getAppSettings().set('webclient_itcfg_revision', revision)


def updateDataCollection(restartReqManager):
    (revision, data) = _downloadConfigTypeIDToBuffer('dataCollection.xml')
    _importFile('dataCollection.xml', data, restartReqManager)
    getAppSettings().set('webclient_datacollection_revision', revision)
    
    
def _isCertificateGood(data):
    certFile = '/tmp/webclient-certificate.pem' 
    with open(certFile, 'w') as f:
        f.write(data)
    try:
        log.dbg('Checking new certificate file')
        with closing(commsHelper.openHttpConnection(certFile=certFile)) as conn:
            data = commsHelper.httpGet(conn, '/changes/%s' % getAppWebClientSetup().getDeviceID())
            _root = ET.fromstring(data)
            log.dbg('Certificate is valid')
            return True        
    except Exception as e:
        raise Exception('Error testing new certificate, %s' % e)
    return False
    

def updateCertificates(restartReqManager):
    (revision, data) = _downloadConfigTypeIDToBuffer('trusted_cacerts.crt')
    if _isCertificateGood(data):
        _importFile('trusted_cacerts.crt', data, restartReqManager)
        getAppSettings().set('webclient_ca_certs_revision', revision)
        
