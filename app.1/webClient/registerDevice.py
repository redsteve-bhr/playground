# -*- coding: utf-8 -*-

import xml.etree.cElementTree as ET
import commsHelper
import webConfig
from contextlib import closing
from applib.utils import jobs
from applib.db.tblSettings import getAppSettings
import log
import appit
import updateit
import bioReader

def _getReaderPartNo():
    try:
        partno = open('/var/run/reader.partno', 'r').read()
        partno =  partno.replace('PartNo = ', '').strip()
        if (partno == 'unknown'):
            return None
        return partno.split('~')[0]
    except Exception as e:
        log.warn('Error reading reader partno: %s' % e)
    return None

def _createRegistrationData(setup):
    appInfo = appit.AppInfo()
    topTag = ET.Element('registration')
    credentialTag = ET.SubElement(topTag, 'credentials')
    ET.SubElement(credentialTag, 'username').text    = setup.getUsername()
    ET.SubElement(credentialTag, 'password').text = setup.getPassword()
    deviceTag = ET.SubElement(topTag, 'device')
    ET.SubElement(deviceTag, 'deviceID').text   = setup.getDeviceID()
    ET.SubElement(deviceTag, 'deviceType').text = setup.getDeviceType()
    ET.SubElement(deviceTag, 'macAddress').text = setup.getMAC()
    ET.SubElement(deviceTag, 'ipAddress').text  = setup.getIP()
    ET.SubElement(deviceTag, 'firmware').text   = updateit.get_version()
    hardwareTag = ET.SubElement(deviceTag, 'hardware')
    readerType = _getReaderPartNo()
    if (readerType != None):
        readerTag = ET.SubElement(hardwareTag, 'reader')
        ET.SubElement(readerTag, 'type').text    = readerType
    if (bioReader.initialise()):
        readerTag = ET.SubElement(hardwareTag, 'biometric')
        ET.SubElement(readerTag, 'type').text    = bioReader.getModuleName()
    appTag = ET.SubElement(deviceTag, 'application')
    ET.SubElement(appTag, 'name').text    = appInfo.name()
    ET.SubElement(appTag, 'version').text = appInfo.version()
    return ET.tostring(topTag, 'utf-8')

def registerDevice():
    """ Send registration request and save token. """
    log.dbg('Registering device...')
    setup = webConfig.getAppWebClientSetup()
    deviceID = setup.getDeviceID()
    body = _createRegistrationData(setup)
    # send request
    with closing(commsHelper.openHttpConnection()) as conn:
        data = commsHelper.httpPost(conn, '/devices/%s' % (deviceID), body)
    tokenTag = ET.fromstring(data).find('token')
    if (tokenTag == None):
        raise Exception('registerDevice has not returned a token')
    setup.setToken(tokenTag.text)
    _resetRevisions()
    log.dbg('Device %s has been registered"' % (setup.getDeviceID(),))

def _resetRevisions():
    getAppSettings().set('webclient_buttons_revision', '')
    getAppSettings().set('webclient_itcfg_revision', '')
    getAppSettings().set('webclient_employees_revision', '')
    getAppSettings().set('webclient_employeeinfo_revision', '')
    getAppSettings().set('webclient_datacollection_revision', '')

   
class RegisterDeviceRequest(jobs.Job):
    """This class is designed to be called from the application wizard"""

    def __init__(self, host, ssl, resource, username, password, checkCertificate, deviceID):
        super(RegisterDeviceRequest, self).__init__()
        self.__registered = False
        self.__token = None
        self.__host = host
        self.__ssl = ssl
        self.__resource = resource
        self.__username = username
        self.__password = password
        self.__checkCertificate = checkCertificate
        self.__deviceID = deviceID

    def getToken(self):
        return self.__token
    
    def isRegistered(self):
        return self.__registered

    def execute(self):
        # NOTE: This is expected to work from the application
        # wizard, in which case application settings are not yet written.
        webConfig.overwriteAppWebClientSetup(self.__host, 
                                             self.__ssl, 
                                             self.__resource, 
                                             self.__username, 
                                             self.__password, 
                                             self.__checkCertificate,
                                             self.__deviceID)
        try:
            setup = webConfig.getAppWebClientSetup()
            body = _createRegistrationData(setup)
            # send request
            with closing(commsHelper.openHttpConnection()) as conn:
                data = commsHelper.httpPost(conn, '/devices/%s' % (self.__deviceID), body)             
            tokenTag = ET.fromstring(data).find('token')
            if (tokenTag == None):
                raise Exception('registerDevice has not returned a token')
            self.__token = tokenTag.text
            self.__registered = True
        finally:
            webConfig.resetAppWebClientSetup()




