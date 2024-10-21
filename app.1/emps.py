# -*- coding: utf-8 -*-
#
# Copyright 2013 Grosvenor Technology
#
import re
from applib.db.table import Table
from applib.db.database import getAppDB
from applib.db.tblSettings import getAppSetting, SettingsSection, TextSetting, ListSetting, NumberSetting, BoolSetting, MultiListSetting
from applib.utils import nls
from applib.bio import bioFinger
from applib import bio
from engine import empVerifyDlg
import log
import itg
import json
import base64
import webClient
from applib.utils import crashReport
from applib.bio.bioEncryption import BioEncryption
from plugins.consent.consentManager import ConsentStatus, ConsentConfig, ConsentManager, ConsentMessages
from plugins.consent.consentDialog import ConsentDialog
import miscUtils

_appEmps = None
_appEmpDisplayItems = None
_appEmpHomeJobCodes = None


def getAppEmps():
    """ Return global employee table. """
    global _appEmps
    if (_appEmps == None):
        _appEmps = _TblEmps()
        _appEmps.open()
    return _appEmps

def getAppEmpDisplayItems():
    """ Return global Display Items handler """
    global _appEmpDisplayItems
    if (_appEmpDisplayItems == None):
        _appEmpDisplayItems = _DisplayItems()
    return _appEmpDisplayItems

def getAppEmpHomeJobCodes():
    """ Return global Home Job Codes Items handler """
    global _appEmpHomeJobCodes
    if (_appEmpHomeJobCodes == None):
        _appEmpHomeJobCodes = _HomeJobCodes()
    return _appEmpHomeJobCodes

def getEmpByBadgeCode(badgeCode):
    """ Return existing employee by badge code or None. """
    appEmps = getAppEmps()
    if (appEmps == None):
        return None
    return appEmps.getEmpByBadgeCode(badgeCode)
        
def createEmployeeFromBadgeCode(badgeCode, isLocalSupervisor=False):
    """ Create non-database employee based on badge code. """
    return _Employee( {
            'EmpID'      : badgeCode,
            'ExternalID' : None,
            'Name'       : badgeCode,
            'Language'   : None,
            'Roles'      : None,
            'VerifyBy'   : None,
            'KeypadID'   : badgeCode,
            'PIN'        : None,
            'BadgeCode'  : badgeCode}, 'badgeCode', isLocalSupervisor)

def getEmpByTmplID(tmplID):
    """ Return existing employee by template ID or None. """
    appEmps = getAppEmps()
    if (appEmps == None):
        return None
    return appEmps.getEmpByTmplID(tmplID)

def createEmployeeFromTmplID(tmplID, isLocalSupervisor=False):
    """ Create non-database employee based on template ID. """
    return _Employee( {
            'EmpID'      : tmplID,
            'ExternalID' : None,
            'Name'       : tmplID,
            'Language'   : None,
            'Roles'      : None,
            'VerifyBy'   : None,
            'KeypadID'   : tmplID,
            'PIN'        : None,
            'BadgeCode'  : tmplID}, 'bio', isLocalSupervisor)

def getEmpByKeypadID(keypadID):
    """ Return existing employee by keypad ID or None. """
    appEmps = getAppEmps()
    if (appEmps == None):
        return None
    return appEmps.getEmpByKeypadID(keypadID)

def createEmployeeFromKeypadID(keypadID, isLocalSupervisor=False):
    """ Create non-database employee based on keypad ID. """    
    return _Employee( {
            'EmpID'      : keypadID,
            'ExternalID' : None,
            'Name'       : keypadID,
            'Language'   : None,
            'Roles'      : None,
            'VerifyBy'   : None,            
            'KeypadID'   : keypadID,
            'PIN'        : None,
            'BadgeCode'  : keypadID}, 'keypadID', isLocalSupervisor)



class _Employee(object):
    
    def __init__(self, empTblRow, identifiedBy, isLocalSupervisor=False):
        for reqField in ('EmpID', 'ExternalID', 'Name', 'Language', 'Roles', 'VerifyBy', 'KeypadID', 'PIN', 'BadgeCode'):
            if (reqField not in empTblRow.keys()):
                raise Exception('Missing field in employee structure (%s)' % reqField)
        self.__photo = self.__voice = self.__manager = None
        self._emp = dict(empTblRow)
        self.__identifiedBy = identifiedBy
        self.__verifiedBy = 'unknown'
        self.__isLocalSupervisor = isLocalSupervisor
        if (isLocalSupervisor):
            self._emp['Name'] = 'Local Supervisor'
            self._emp['PIN']  = str(getAppSetting('local_supervisor_pin'))
            self._emp['VerifyBy'] = 'pin'
            self._emp['Roles'] = 'supervisor'
        self._startOnlineMessageJob()
        
        if self._emp['VerifyBy'] is None or len(self._emp['VerifyBy']) == 0:
            self._emp['VerifyBy'] = getAppSetting('emp_default_verify_methods')

        self.__appEmps = getAppEmps()
        self.__inTable = self.__appEmps.selectEmpByID(self._emp['EmpID']) is not None
        

        
    def getEmpID(self):
        return self._emp['EmpID']
    
    def getExternalID(self):
        return self._emp['ExternalID']
    
    def getBadgeCode(self):
        return self._emp['BadgeCode']
    
    def getKeypadID(self):
        return self._emp['KeypadID']
    
    def getPIN(self):
        return self._emp['PIN']
    
    def getName(self):
        return self._emp['Name']
    
    def getLanguage(self, useManagerIfAvailable=True):
        if (useManagerIfAvailable and self.__manager != None):
            return self.__manager.getLanguage()
        language = self._emp['Language']
        if language is None or language.strip() == '':
            log.dbg('Employee has no language assigned. Using system language.')
            # Use the system language, if any, otherwise fall back to English
            language = nls.getCurrentLanguage()
            if language is None:
                log.warn('No system language. Using "en".')
                language = 'en'
        return language

    def getLanguages(self, useManagerIfAvailable=True):
        if (useManagerIfAvailable and self.__manager != None):
            return self.__manager.getLanguages()
        languages = []
        lang = self.getLanguage(useManagerIfAvailable)
        if (lang):
            languages.append(lang.lower())
        lang = nls.getCurrentLanguage()
        if (lang and lang not in languages):
            languages.append(lang.lower())
        if ('en' not in languages):
            languages.append('en')
        return languages

    def getLocale(self):
        if (self.__manager != None):
            return self.__manager.getLocale()
        return None

    def Language(self):
        if (self.__manager != None):
            return self.__manager.Language()
        return nls.Language(self.getLanguage(), self.getLocale())

    def __fixedVerificationMethods(self, vMethIn):
        availableVerifyMethods= {} 
        for v in empVerifyDlg.getVerificationMethods():
            availableVerifyMethods[v.lower()] = v
        vMethOut = []
        for v in vMethIn:
            vl = v.lower()
            if (vl in availableVerifyMethods):
                vMethOut.append(availableVerifyMethods[vl])
            else:
                log.warn('Invalid verification method for employee %s: %s' % (self.getEmpID(), v))
        return vMethOut
    
    def getVerificationMethods(self):
        vMethods = self._emp['VerifyBy']
        if (vMethods == None):
            vMethods = getAppSetting('emp_default_verify_methods')
        if (vMethods):
            vMethodsList = [ p.strip() for p in vMethods.split(',') ]
        else:
            vMethodsList = []
        # The user verification method is the first verification 
        # method in this implementation and not added to this list
        # as with Custom Exchange data distribution.
        return self.__fixedVerificationMethods(vMethodsList) 
        
    def getVerifyBy(self):
        return self._emp['VerifyBy']
    
    def getRoles(self):
        rolesString = self._emp['Roles']
        if (not rolesString):
            return []
        roles = [ p.strip() for p in rolesString.split(',') ]

        # Enforce inTable required role when limit by = table, and not using local supervisor
        if (getAppSetting('emp_limit_by') == 'table' and not self.__isLocalSupervisor and self.__inTable):
            roles.append(u'inTable')

        return roles
    
    def isSupervisor(self):
        return 'supervisor' in self.getRoles()
    
    def isLocalSupervisor(self):
        return self.__isLocalSupervisor
    
    def setManager(self, manager):
        self.__manager = manager
    
    def getManager(self, default=None):
        if (self.__manager == None):
            return default
        return self.__manager
    
    def getUsedIdentificationMethod(self):
        return self.__identifiedBy
    
    def isIdentifiedByKeypad(self):
        return (self.__identifiedBy == 'keypadID')
    
    def isIdentifiedByReader(self):
        return (self.__identifiedBy == 'badgeCode')

    def isIdentifiedByBiometric(self):
        return (self.__identifiedBy == 'bio')

    def setUsedVerificationMethod(self, method):
        self.__verifiedBy = method
        
    def getUsedVerificationMethod(self):
        return self.__verifiedBy

    def setVerifyPhoto(self, data):
        self.__photo = data
        
    def getVerifyPhoto(self):
        return self.__photo

    def setVerifyVoice(self, data):
        self.__voice = data
        
    def getVerifyVoice(self):
        return self.__voice

    def getDisplayItems(self):
        items = self._emp['DisplayItems']
        if items is None or items.strip() == '':
            items = '{}'
        return items
    
    def setDisplayItems(self, jsonStr):
        self._emp['DisplayItems'] = jsonStr

    def getHomeJobCodes(self):
        items = self._emp['HomeJobCodes']
        if items is None or items.strip() == '':
            items = '{}'
        return items

    def setHomeJobCodes(self, jsonStr):
        self._emp['HomeJobCodes'] = jsonStr

    def asDict(self):
        """Creates and returns a dictionary object that is compatible with SQLite
        queries, and contains all the columns and values from the employee. The
        resulting dictionary can be amended and passed to Table.insert() to 
        insert or update an employee record in the database."""
        return {
            'EmpID'        : self.getEmpID(),
            'ExternalID'   : self.getExternalID(),
            'Name'         : self.getName(),
            'Language'     : self.getLanguage(),
            'Roles'        : ''.join(self.getRoles()),
            'VerifyBy'     : self.getVerifyBy(),
            'KeypadID'     : self.getKeypadID(),
            'PIN'          : self.getPIN(),
            'BadgeCode'    : self.getBadgeCode(),
            'DisplayItems' : self.getDisplayItems(),
            'HomeJobCodes' : self.getHomeJobCodes()
            }
    
    ##
    ## Online message
    ##
    ##
    def _startOnlineMessageJob(self):
        """ Start job to receive online message, e.g. for emp options dialog. """
        self.__loadOnlineMessageJob = None
    
    def getOnlineMessageJob(self):
        """ Return job for loading online message. """
        return self.__loadOnlineMessageJob    
    

class _DatabaseEmployee(_Employee):

    _consentManager = None
    
    def reload(self):
        empTblRow = getAppEmps().selectEmpByID(self.getEmpID())
        if (empTblRow != None):
            self._emp.update(empTblRow)
    
    ##
    ##
    ## Profile related functions
    ##
    ## (comment-out unneeded methods)  


    #
    # Biometric templates
    #
    def supportsTemplates(self):
        return True
      
    def getTemplates(self):
        if (self.isLocalSupervisor()):
            return []        
        return getAppEmps().getTemplateRepository().getTemplates(self.getEmpID())        
  
    def _queueTemplateData(self, tmplData):
        """ Queue tmplData (JSON string) to be send to server. """
        updateQueue = webClient.getAppEmpUpdatesQueue()
        updateQueue.addTemplates(self.getEmpID(), tmplData)
        timeout = getAppSetting('webclient_ui_timeout')
        unsentCount = updateQueue.waitUntilDone(timeout)
        self.reload()
        if (unsentCount > 0):
            raise Exception('Unable to send changes. Changes will be sent when server is online.')
        
    def setTemplates(self, templates):
        if (templates):
            tmplData = json.dumps({'Templates': templates, 'Consents': self.getConsents().asJSON()})
        else:
            tmplData = ''
        # send data to server
        self._queueTemplateData(tmplData)
        
    def setFingers(self, fingers):
        # {"Templates": ["VWxOclRrWkpkM0ZXVlZsbFoxbERlRUo1YVVOTlMydFFSVUZRUVZoUmQzUkNVME5vUm5selJsRkxUMUpJV1Zkb1ZGRTBkRUl5UTJORFVsaElaMUZyVlVoalpXZFRXWE5zZVVoRGFRcHBRbXhKYzBGVFUwVnJiRUZhYUVsV1UxVkNZbXg1ZVVwblduRlJSa0Z0VVVWU1kyTnBaME40Um1rNVRHOWFRMDFNVFhkQ1RGcEpjV3BDUTFwclFsZE5XVkpaVTBsSmVIZHhVbmR0Q2tSSVEyTkVlVlpOYjBSTFQweEJNRkZuWjI5UFJGUkNlR2hvYTA1dlYxRmpRbmN6UVVwSlkwbHFiVUlyYVdodFQxbFdORlJNVVRkNFoxbFZVRVIzUm5sb2VGWlFUVVoxV0VWSksxRUtZbEZ2VUVRMlFWaG9lR2RTVVZGeFRVZHdSM2RDZDJOeWEySkJWRzE0VkZOQlYyZEtTVVpNUWtKUmIzRlZkRUZKYlZKNlV6aFhSVTR2THpoQlFWTlFMeTh2TDJkQlFra3dMeTh2WlFwQlFVVnFVQzh2WkRSQlJWTkpNU3M0TTJkQlVrbDZWRFoyVDBGQ1NYcFNabTA0TTJkRmVrNUdLM0o2VGtGVVRrWllObkU0TUVKTk1GSlhjWEoyVDBWclVsWmxZWEU0TkZOU1JsbzFDbkZ5ZWxGR1JsWnViV0YxT0VGVlZtNWxXbkUzZW1oU1YyUTBiWEYyVHk4dlpETXJZWFpQUkM4dk0yWXZkVGd6ZFM4dkx5OHZOM3BsTjNVM0x5OHZMMDE2WkROUUx5OHZMM3BPTTJNS0wzZEJRVUZCUVVGQlFVRkJRVUZCUVVGQlFVRkJRVUZCUVVGQlFVRkJRVUZCUVVGQlFVRkJRVUZCUVVGQlFVRkJRVUZCUVVGQlFVRUs=", "VWtNMFVVWnZZM0ZXVlZrMFFUTlpSVk5SVGpCRFZrbEhZbHBDWmtObVNWQllRWEJ0UTJvd1RTdDNWbVJIZFZWSFNWSTJSVU14V1hFMlFXYzNUREp6UzBKVWJXWkNhV2NyUjFKek53cFJiV05MVXpCUWJVSlVSa1pGVWtsd1UxbHBXbGRWZG1Ob1EyaE5SMEpaTkZRdk1GZFdSamRsUTNsMGFrbEtSa0paS3poUVpGZHVha014WkhFMlFWcHpZU3MwU1UxWGVVZHdhMDV6Q2pkb1FteGlSelJIVFROUFNteFJkREZ3YjA1TFpHWmhUbUZZWW05cWVEVTBielIzYzJWWU9GTmFORXczUWtKRFJHODBWbGxwVUdOS1JUUjVZMEpwY1ZCck5HTTBhMEZUU0ZaS1RVY0tRa1ZEVmtOdlpIVnRVVkZLUzBwelRtbENObVJvWjAxbmIwcFJSRGhQUVVGQlVrbHBMeTh2WlRkblFVSkZhVTB2THpnelpUUkJSVk5OTUM4dmVtUTNaMFZUU1hwU1VDOU5NMmRCVWdwSmFsSkdMemQ2VGpSQ1NXcE9SVlF2ZFRnelowVnFUVEJTVmlzM2VrNUJVMDB3VWxaaU4zVTRNMmhKZWxKR1ZuWjFOM3BQUldwU1JWWlhZWEYxT0RSVFRrVlNWbFpoY1hKNlVVa3dDbEpGVWxaeGNYVTRRVlJPUlZKRlUzRjFOM3BvU1hwTmVsSmhkVGQ2VVVWVFNXbEpNSEZ5ZW1WQlVrVm9SVk5UY25aT05FRkJRa1ZDUldGMU9ETjFRVUZCUVVGUUt6aDZaRGQxTjJjS1FVRXZMM3BOTTNVM2RUZDFOeTh2TDNwT00yUTNkVGN2THk4dk9IcE9lbVUzTHpoQlFVRkJRVUZCUVVGQlFVRkJRVUZCUVVGQlFVRUs=", "VWtSSlQwWktZM0ZXVlZsWlFrbEpUMWRCTjJaQlZXTldOSGRaTTBaMU5FdEJlWFZyUVd4WmRESkJXV3hNZGpKaVYwTTFVa0ozY3pOd1NXZHZUMEZCWWtoNmNVSnVRbEU1YlVwRmNRcFJWakJVU1RCUlNVeEdVa2RWVVU1TFUwNVJURXBGYkhkeWFrNU1NMmRqUkZNMkswWktWVFJXU2pGQ1QzcFJXbXRWVFZsT1NERkhTSFJIUWxKVlVrRk5WV0psU1V4V1VISnFWakZVQ25sNFNWWldjVmRNU1cxS2MzQnBaR3M0TkhkU1lUWnpURWh1VDBGeGVWb3dPRFZuTW1SMWExRkVibWwxUTJ4d05EUjNiMnhsZG5WTFNGaDFSVWg2WkRnNFdXOVdabkJuVmxJek4zRUtSRkp0UVdoQ2IydG5RVk5MVGxsWU0wUkRSMHRtZHpSd2FYWmhTRVkwZFZGcmFWTlFRbTl6Yld4UmJVbElTbUZGUTNZelpVRlRTWHBTVUM5Tk0yZEZhazVGVWxCNlRqUkNTVEJTUmdwWU4zcGxSVlJPUlZaV0t6ZDZhRWt3VWtaV1ZuVTRORk5PUlZaV1ZtRjJUa0V3VWxaV1ZsZHllbEpPUmxadFdtMXhjakJWVmxaYWJXUTFjVGxGTVZadFdqTmxXblpCVGtaYWJWcHRDbTFoTUZSU1ZsWldWbHB0ZEVrd1VrVlNSU3RhY2xOT1JWSkZVUzl0Y2pCVFRYcFNSRkEyY1RsQlUwbDZUWG9yY1hwblJWTkphVWwyS3pnd1FVVlRTV2t2THk5T05FRkZVa2d2THk4S0wyUkVaMFZtTHk5QlFVRkJRVUZCUVVGQlFVRkJRVUZCUVVGQlFVRkJRVUZCUVVGQlFVRkJRVUZCUVVGQlFVRkJRVUZCUVVGQlFVRUs=", "VWtSblQwWmFWWEZXVlZsMVFUTkpTVWRCVTBORWJHZFBNM2RGTTBaMU9FeFNlR0pxUTBGTmNuQkJVV3RNWjBOaVEzcHBiV2xUYXpRdlVtOWxUMjlMWWtaVU1saHJhWEJDV0ZKRmFncFNRV2QwVmtWa1ZFSkdaRWg2ZDFadFVqRkZURmd3YmxSRWJIUktWVkZ6YWxOdVQzWkxWVzlCUmxGU1MzTkpZM2xUZERCSFZWVjBVRUV3T1U5NWQxbG1WVmxMTTBSR1J6TnBRMlJTQ2prMVpHdFZjMWxPVEZaUWNXcHJNVlF4VVd4YVZUZzRURVpXVjJScVZuUldWMmMxYlZoT1kxTkZiWEZ6UlZJMWVtZExWV3hrVUU5aFQwaGliR3BDVmpWdFFuZFJaV0UyVDFoSWJtMEtRMU5TTmk5SmMySmxOSFZoVGxoMmVXcHJaVU0yYnpSWlp6UjVZVTVKV0RORVFYRkpiM2RqY0dsMllVaEhTWEZLYkVaNVR6ZHZaMlpyVWxsU1RWcGFObWhxYVZnNVNWbDFiVkpOU3dwTVNqRXZRMll6WjBGVFRYcFNVQzlOTTJkRmFrNUZVbEI2VGpSQ1NUQlNSbGczZW1WQlZFNUZWbFpYTjNwb1NUQlNSbFpXZFRnMFUwNUZWbFpXWVhaT1JUQlNWbFpXWVhKNlVrNUdDbFpYV20xeGNqQlZVbFpXYlZvMWNUbEdSbFpXV201bFduWlNUa1pXVjFwdWJXRTBWRkpXVmxaV2NHMTBTVEJTUlZKRlYxcHlVMDVGVWtWUk1IRnlNRk5OZWsxNlVEWnhLMEZUU1hvS1RYb3JjbnBuUlZOSmFVbDJjVGcwUVVWVFJXbE1MM1pPTkVGRlVrVlNMeTkyWlVGQ1JWSkVMeTh2TDJkQlFrVlFMM2RCUVVGQlFVRUs="], 
        #  "Info": {"fingerInfo": [{"code": "ri", "quality": 70}, {"code": "rm", "quality": 76}], 
        #                        "numTemplates": 4}}}        
        if (fingers):
            templates = []
            fingerInfo = []
            for finger in fingers:
                templates.extend(finger.getTemplates())
                fingerInfo.append({'code': finger.getFingerCode(), 'quality': finger.getQuality()})
            tInfo = { 'fingerInfo': fingerInfo,
                      'numTemplates': len(templates) }
            tmplData = json.dumps({"Templates" :  templates, "Info" : tInfo, "Consents": self.getConsents().asJSON()})
            # send data to server
            self._queueTemplateData(tmplData)
        else:
            tmplData = ''
            empID = self.getEmpID()
            consents = self.getConsents()
            consentStr = consents.getActiveConsent().asJSONStr()
            base64ConsentData = base64.b64encode(consentStr)
            message = ConsentMessages.deleteFinger(empID, base64ConsentData)
            consents.queueConsentData(empID, message)

    def getFingers(self):
        if (self.isLocalSupervisor()):
            return []        
        return getAppEmps().getTemplateRepository().getFingers(self.getEmpID())        

    def hasTemplateInfo(self):
        if (self.isLocalSupervisor()):
            return False        
        return getAppEmps().getTemplateRepository().hasTemplateInfo(self.getEmpID())        

    def getTemplatesAndConsents(self):
        if (self.isLocalSupervisor()):
            return False
        return getAppEmps().getTemplateRepository().getTemplatesJSONString(self.getEmpID())

    def getConsents(self):
        """Returns ConsentManager with the list of Employee Consents"""
        if self._consentManager is None:
            self._consentManager = ConsentManager()
            self._consentManager.load(self)
        return self._consentManager

    def setConsents(self, manager):
        """Sets the consent manager for the employee"""
        self._consentManager = manager

    def isConsentRequired(self):
        """Returns True if the employee is identifying or verifying by
           biometric data (finger), and if consent is required before 
           continuing. 
        """
        log.dbg("Employee.isConsentRequired()")
        result = False
        if hasattr(self, "getConsents"):
            # Identify by Bio?
            if self.isIdentifiedByBiometric():
                if not self.getConsents().getStatus() in ConsentStatus.ACTIVE:
                    result = True
                    
            # Verify by Bio?
            if bio.employeeCanBeVerified(self):
                for vMethod in self.getVerificationMethods():
                    if vMethod == "bio":
                        if not self.getConsents().getStatus() in ConsentStatus.ACTIVE:
                            result = True
                    
        return result

    def checkConsent(self, forEnrol=False):
        """Returns True if consent is not required, or if consent has been 
        granted. Displays the Consent Dialog if necessary, to prompt the user
        for consent.
        """
        log.dbg("Employee.checkConsent(forEnrol={})".format(forEnrol))
        if self.isConsentRequired() or forEnrol:
            
            if forEnrol:
                status = ConsentStatus.PENDING
            else:
                status = None

            empLanguage = self.getLanguage(useManagerIfAvailable=False)
            html = ConsentConfig(empLanguage=empLanguage).getMessage()
            with nls.Language(empLanguage, self.getLocale()):
                consentDlg = ConsentDialog(html, self, overrideStatus=status, forEnrol=forEnrol)
                resId = consentDlg.run()
                status = consentDlg.getConsentStatus()
                # self.setIsConsentChanged(True)
    
                if (status in [ConsentStatus.PENDING, ConsentStatus.DECLINED, ConsentStatus.EXPIRED]) or (resId == itg.ID_CANCEL):
                    return False
        return True

    #
    # User Verification Method
    #
    def getUserVerificationMethod(self):
        if (self.isLocalSupervisor()):
            return None
        vMethods = self.getVerificationMethods()
        # the user verification method is the first verification method.
        if (vMethods):
            return vMethods[0]
        return None
  
    def setUserVerificationMethod(self, vMethod):
        vMethods = self.getVerificationMethods()
        if (not vMethods):
            # well, this is odd, shouldn't be possible?
            return
        vMethods[0] = vMethod
        updateQueue = webClient.getAppEmpUpdatesQueue()
        updateQueue.addVerificationbMethods(self.getEmpID(), ','.join(vMethods))
        updateQueue.waitUntilDone(5)
        self.reload()
        
    def setUserVerificationDefaultMethod(self):
        updateQueue = webClient.getAppEmpUpdatesQueue()
        updateQueue.addVerificationbMethods(self.getEmpID(), getAppSetting('emp_default_verify_methods'))
        updateQueue.waitUntilDone(5)
        self.reload()

    #
    # Language
    #
    def setUserLanguage(self, lang):
        updateQueue = webClient.getAppEmpUpdatesQueue()
        updateQueue.addLanguage(self.getEmpID(), lang)
        updateQueue.waitUntilDone(5)
        self.reload()
          
    def getUserLanguage(self):
        if (self.isLocalSupervisor()):
            return None        
        return self.getLanguage(useManagerIfAvailable=False)
      
    def deleteUserLanguage(self):
        updateQueue = webClient.getAppEmpUpdatesQueue()
        updateQueue.addLanguage(self.getEmpID(), '')
        updateQueue.waitUntilDone(5)
        self.reload()
 
    #
    # User PIN
    #
    def setPin(self, pin):
        updateQueue = webClient.getAppEmpUpdatesQueue()
        updateQueue.addPin(self.getEmpID(), pin)
        updateQueue.waitUntilDone(5)
        self.reload()
          
    def setBadgeCode(self, badgeCode):
        self._emp['BadgeCode'] = badgeCode
        getAppEmps().addOrUpdate(self._emp)
        updateQueue = webClient.getAppEmpUpdatesQueue()
        updateQueue.addBadgeCode(self.getEmpID(), badgeCode)
        updateQueue.waitUntilDone(5)
        self.reload()
        
    #
    # Profile Picture
    #
    def getProfilePicture(self):
        b64Data = getAppEmps().getEmpDataRepository().getBase64Data(self.getEmpID(), 'profilePicture')
        if (not b64Data):
            return None
        return itg.Base64JPEGImage(b64Data)

    def setProfilePicture(self, rawData):
        updateQueue = webClient.getAppEmpUpdatesQueue()
        updateQueue.addPhoto(self.getEmpID(), rawData)
        updateQueue.waitUntilDone(5)
        self.reload()

    def deleteProfilePicture(self):
        updateQueue = webClient.getAppEmpUpdatesQueue()
        updateQueue.addPhoto(self.getEmpID(), None)
        updateQueue.waitUntilDone(5)
        self.reload()
     



class _TblEmps(Table):

    columnDefs = { 'EmpID'        : 'TEXT NOT NULL UNIQUE',
                   'ExternalID'   : 'TEXT NOT NULL DEFAULT ""',
                   'Name'         : 'TEXT NOT NULL',
                   'Language'     : 'TEXT',
                   'Roles'        : 'TEXT',
                   'VerifyBy'     : 'TEXT',
                   'KeypadID'     : 'TEXT',
                   'PIN'          : 'TEXT',
                   'BadgeCode'    : 'TEXT',
                   'Revision'     : 'TEXT',
                   'DisplayItems' : 'TEXT',
                   'HomeJobCodes' : 'TEXT',
                   'MD5'          : 'TEXT', }

    healthMonitorUpdatePeriod = 20
    
    def __init__(self, db=None, tableName='tblEmps'):
        if (db == None):
            db = getAppDB()
        super(_TblEmps, self).__init__(db, tableName)
        self.__templateRepository = _TemplateRepository(db)
        self.__empDataRepository = _EmployeeDataRepository(db)
    
    def open(self):
        super(_TblEmps, self).open()
        self.__templateRepository.open()
        self.__empDataRepository.open()
        
    def getTemplateRepository(self):
        return self.__templateRepository
    
    def getEmpDataRepository(self):
        return self.__empDataRepository
    
    def selectEmpByID(self, empID):
        sql = 'SELECT * FROM %s WHERE EmpID = ?' % self.tableName
        return self.runSelectOne(sql, (empID,))

    #def getEmpByID(self, empID):
    #    sql = 'SELECT * FROM %s WHERE EmpID = ?' % self.tableName
    #    empRow = self.runSelectOne(sql, (empID,))
    #    return _Employee(empRow) if empRow else None

    def getEmpByKeypadID(self, keypadID):
        sql = 'SELECT * FROM %s WHERE KeypadID = ?' % self.tableName
        empRow = self.runSelectOne(sql, (keypadID,))
        return _DatabaseEmployee(empRow, 'keypadID') if empRow else None

    def getEmpByBadgeCode(self, badgeCode):
        sql = 'SELECT * FROM %s WHERE BadgeCode = ?' % self.tableName
        empRow = self.runSelectOne(sql, (badgeCode,))
        return _DatabaseEmployee(empRow, 'badgeCode') if empRow else None


    def getEmpsByBadgeCode(self, badgeCode):
        sql = 'SELECT * FROM %s WHERE BadgeCode = ?' % self.tableName
        rows = self.runSelectAll(sql, (badgeCode,))
        return rows

    def getEmpByTmplID(self, tmplID):
        sql = 'SELECT * FROM %s WHERE EmpID = ?' % self.tableName
        empRow = self.runSelectOne(sql, (tmplID,))
        return _DatabaseEmployee(empRow, 'bio') if empRow else None

    #
    # The following functions are used for synchronising 
    #
    
    def getAllEmpIDsAndMD5s(self):
        sql = 'SELECT EmpID, MD5 FROM %s' % self.tableName
        rows = self.runSelectAll(sql)
        empIDs = {}
        for row in rows:
            empIDs[row['EmpID']] = row['MD5']
        return empIDs
    
    def resetAllMD5s(self):
        """ Force to update all MD5s of tblEmps to ''. """
        sql = 'update %s set MD5 = "%s"' % (self.tableName, '')
        self.runQuery(sql)
    
    def getAllEmps(self):
        sql = 'SELECT * FROM %s' % self.tableName
        rows = self.runSelectAll(sql)
        return rows

    def deleteByEmpID(self, empID):
        """ Delete employee. """
        # delete employee
        sql = 'DELETE FROM %s WHERE EmpID = ?' % self.tableName
        self.runQuery(sql, (empID,))
        # delete template
        self.getTemplateRepository().deleteTemplates(empID)
        # delete photo
        self.getEmpDataRepository().deleteData(empID, 'profilePicture')
    
    def __terminalSupportsTemplates(self):
        """ Return **True** if terminal supports biometric templates. """
        if (itg.isIT11()):
            return False
        return True
    
    def __terminalSupportsProfilePictures(self):
        """ Return **True** if terminal supports showing profile pictures. """
        return miscUtils.hasCameraSupport()
        
    def addOrUpdate(self, emp):
        """ Add or update employee. *emp* is a dictionary. """
        # extract templates and photos from employee dictionary
        templates = photo = None
        if ('Templates' in emp):
            templates = emp['Templates']
            del emp['Templates']
        if ('Photo' in emp):
            photo = emp['Photo']
            del emp['Photo']
        # insert employee
        self.insert(emp, replace=True)
        # insert templates and photos into DB
        if (self.__terminalSupportsTemplates()):
            # Templates are not supported on IT11
            if (templates):
                try:
                    self.getTemplateRepository().addJSONTemplData(emp['EmpID'], base64.b64decode(templates))
                except Exception as e:
                    raise Exception('Error parsing templates of employee %s: %s' % (emp['EmpID'], e))
            else:
                self.getTemplateRepository().deleteTemplates(emp['EmpID'])
        if (self.__terminalSupportsProfilePictures()):
            # Photos are only supported on IT51
            if (photo):
                self.getEmpDataRepository().addBase64Data(emp['EmpID'], 'profilePicture', photo)
            else:
                self.getEmpDataRepository().deleteData(emp['EmpID'], 'profilePicture')
    
    #
    # Health Monitor
    #

    def getWarnings(self):
        warnings = []
        if (self.count() == 0):
            warnings.append({ 'msg': _('No employees loaded')})
        return warnings

    def getHealth(self):
        name      = _('Employee data')
        employees = self.count()
        healthy   = (employees > 0)
        items   = ( 
            (_('Employees'),  employees),
            )
        return (name, healthy, items)



class _HomeJobCodes(object):
    """Class to handle the storage and retrieval of Home Job Codes. These are
    stored as JSON strings in the HomeJobCodes column of tblEmps."""

    def __init__(self):
        self.tableName = 'tblEmps'

    def getEmployeeRecord(self, employeeID):
        """Returns the database record for the currently-assigned employee.
        Returns None if the employee cannot be found in the database."""
        sql = 'SELECT * FROM %s WHERE EmpID = ?' % self.tableName
        empRow = getAppEmps().runSelectOne(sql, (employeeID,))
        return _DatabaseEmployee(empRow, 'EmpID') if empRow else None

    def store(self, employeeID, xmlData):
        """Stores the provided XML list of Home Job Codes against the specified
        employee and returns the JSON string that was stored."""
        jsonStr = self.compileToJSON(xmlData)
        employee = self.getEmployeeRecord(employeeID)
        if employee is not None:
            employee.setHomeJobCodes(jsonStr)
            getAppEmps().insert(employee.asDict(), replace=True)
        else:
            log.warn("Employee %s not found" % employeeID)
        return jsonStr

    def parseToDictList(self, employeeID):
        employee = self.getEmployeeRecord(employeeID)
        if employee is not None:
            return json.loads(employee.getHomeJobCodes())

    def compileToJSON(self, xmlData):
        """Compiles home job codes into a JSON string. The supplied XML Data
        is expected to be in the format returned from GTConnect."""

        itemList = []
        homeJobCodesTag = xmlData.findall('jobCode')
        for itemTag in homeJobCodesTag:
            try:
                if (itemTag.tag != 'jobCode'):
                    continue

                item = {}

                colLevel = itemTag.get('level')
                colJobCodeID = itemTag.text

                if colLevel is not None and colLevel != "":
                    colLevel = colLevel.strip()
                else:
                    raise Exception("Malformed XML -- no 'level' attribute in 'jobCode'")

                if colJobCodeID is None or colJobCodeID == "":
                    raise Exception("Malformed XML -- Empty 'jobCodeID' text in 'jobCode'")

                item['level'] = colLevel
                item['jobCodeId'] = colJobCodeID

                itemList.append(item)
            except Exception as e:
                log.err("Failed to compile home job codes: %s" % (e,))

        return json.dumps(itemList)



class _DisplayItems(object):
    """Class to handle the storage and retrieval of Display Items. These are 
    stored as JSON strings in the DisplayItems column of tblEmps."""

    def __init__(self):
        self.tableName = 'tblEmps'
      
    def getEmployeeRecord(self, employeeID):
        """Returns the database record for the currently-assigned employee. 
        Returns None if the employee cannot be found in the database."""
        
        sql = 'SELECT * FROM %s WHERE EmpID = ?' % self.tableName
        empRow = getAppEmps().runSelectOne(sql, (employeeID,))
        return _DatabaseEmployee(empRow, 'EmpID') if empRow else None 

    def parseJSONItemsToHTML(self, items):
        data = []
        if itg.isIT11() or itg.isIT31():
            template = "%s: %s"
        else:
            data.append("<html style='background-color: #009bc9'><body>")
            data.append("<table style='background-color: #009bc9; color: white; width: 100%; font-size: 1.5em'>")
            template = "<tr style='line-height: 2em'><td>%s</td><td>%s</td></tr>"
        for entry in items:
            for name, value in entry.iteritems():
                data.append(template % (name, value))
        if not (itg.isIT11() or itg.isIT31()):
            data.append("</table>")
            data.append("</body></html>")
        return data
        
    def parseToHTML(self, employeeID):
        """Retrieves the Display Items for the specified employee, 
        and returns them as an HTML-formatted string."""
        
        employee = self.getEmployeeRecord(employeeID)
        if employee is not None:
            items = json.loads(employee.getDisplayItems())
            data = self.parseJSONItemsToHTML(items)
            return data
        else:
            return []

    def parseToPango(self, employeeID):
        """Retrieves the Display Items for the specified employee, 
        and returns them as an Pango-marked-up string."""
        employee = self.getEmployeeRecord(employeeID)
        if employee is not None:
            items = json.loads(employee.getDisplayItems())
            data = []
            if itg.isIT11() or itg.isIT31():
                template = "%s: %s"
            else:
                template = '<span size="medium">%s: %s</span>'
                
            for entry in items:
                for name, value in entry.iteritems():
                    data.append(template % (name, value))
            return data
        else:
            return []
                
    def parseToCSV(self, employeeID):
        """Retrieves the Display Items for the specified employee,
        and returns them as a CSV-compatible string-field."""
        employee = self.getEmployeeRecord(employeeID)
        if employee is not None:
            items = json.loads(employee.getDisplayItems())
            data = []
            template = "%s: %s"

            for entry in items:
                for name, value in entry.iteritems():
                    data.append(template % (name, value))

            result = ";".join(data)
            result = re.sub(",", "_", result)
        else:
            return ""

    def store(self, employeeID, xmlData):
        """Stores the provided XML list of Display Items against the specified
        employee and returns the JSON string that was stored."""
        jsonStr = self.compileToJSON(xmlData)
        employee = self.getEmployeeRecord(employeeID)
        if employee is not None:
            employee.setDisplayItems(jsonStr)
            getAppEmps().insert(employee.asDict(), replace=True)
        else:
            log.warn("Employee %s not found" % employeeID)
        return jsonStr
        
    def compileToJSON(self, xmlData):
        """Compiles display items into a JSON string. The supplied XML Data 
        is expected to be in the format returned from ProSynergy."""
        
        itemList = []
        displayItemsTag = xmlData.find('items')
        for itemTag in displayItemsTag:
            try:
                if (itemTag.tag != 'item'):
                    continue
    
                item = {}
    
                colNameTag  = itemTag.find('name')
                colValueTag = itemTag.find('value')
                encoding = colValueTag.get('encoding')
                if colNameTag is not None:
                    colName = colNameTag.text
                else:
                    raise Exception("Malformed XML -- no 'name' element in 'item'")
                if colValueTag is not None:
                    if encoding == "base64":
                        colValue = base64.b64decode(colValueTag.text)
                    else:
                        colValue = colValueTag.text
                else:
                    raise Exception("Malformed XML -- no 'value' element in 'item'")
                item['Name'] = colName
                item['Value'] = colValue
    
                if (('Name' not in item) or 'Value' not in item):
                    log.err('Name or Value not specified!')
                else:
                    itemList.append({colName: colValue})
            except Exception as e:
                log.err("Failed to compile display items: %s" % (e,))
    
        return json.dumps(itemList)
    
class _TemplateRepository(bio.BioTemplateRepository, Table):
    """ Template repository. """

    columnDefs = { 'EmpID'     : 'TEXT UNIQUE NOT NULL',
                   'TmplCount' : 'INTEGER NOT NULL',
                   'TmplData'  : 'TEXT NOT NULL' }

    def __init__(self, db=None, tableName='tblBioTemplateRepository'):
        if (db == None):
            db = getAppDB()
        super(_TemplateRepository, self).__init__(db, tableName)
        
    def __getCorrectedTemplates(self, empID, templates):
        """ It is possible that templates got b64 encoded twice. This method 
        returns raw templates as b64 encoded (once), i.e. it will decode the 
        templates (once) if they were encoded twice or just return the list
        of correctly-encoded templates.
        """
                    
        # First round of B64 decoding
        templatesFirstDecode = map(base64.b64decode, templates)
        
        isDoubleEncoded = False
        try:
            # Convert first decode to ascii.
            templatesFirstDecode = map(lambda s: s.decode('ascii'), templatesFirstDecode)
            # Check if can be decoded a second time. Does not mutate templatesFirstDecode.
            map(base64.b64decode, templatesFirstDecode)
            
            isDoubleEncoded = True
        except (UnicodeDecodeError, TypeError) as e:
            # Expected to happen for normal templates that are not double-encoded.
            pass
        except Exception as e:
            log.warn('Unexpected exception when testing templates: ' % (e))

        templateLengths = [str(len(templ)) for templ in templates]
        templateLengthsStr = ", ".join(templateLengths)
        
        if isDoubleEncoded:
            log.warn("Returning corrected b64 encoded templates. [%s] - EmpID: %s" % (templateLengthsStr, empID))
            return templatesFirstDecode # Single Encoded after first round of decoding - Because received double encoded
        else:
            log.dbg("Returning b64 encoded templates. [%s] - EmpID: %s" % (templateLengthsStr, empID))
            return templates            # Single Encoded from argument

    def getTemplates(self, empID):
        """ Return list of (b64 encoded) templates for user ID. """
        sql = 'SELECT TmplData FROM %s WHERE EmpID = ?' % self.tableName
        res = self.runSelectOne(sql, (empID,))
        if (res == None):
            return []
        if (res['TmplData']):
            tmplData = json.loads(res['TmplData'])
            if ('Templates' in tmplData):
                return self.__getCorrectedTemplates(empID, tmplData['Templates'])
            else:
                log.warn('Invalid templates for employee %s' % empID)
        return []
    
    def getTemplatesJSONString(self, empID):
        """Return a string of the templates and consents from the employee 
        record"""
        sql = 'SELECT TmplData FROM %s WHERE EmpID = ?' % self.tableName
        res = self.runSelectOne(sql, (empID,))
        if (res == None):
            return ""
        if (res['TmplData']):
            tmplData = res['TmplData']
        else:
            tmplData = ""
        return tmplData
        
    def getAllTemplates(self):
        sql = 'SELECT * FROM %s' % self.tableName        
        return self.runSelectAll(sql)
    
    def getFingers(self, empID):
        """ Return list of BioFinger objects or an empty list. """
        sql = 'SELECT TmplData FROM %s WHERE EmpID = ?' % self.tableName
        res = self.runSelectOne(sql, (empID,))
        if (res == None or not res['TmplData']):
            return []
        try:
            tmplData = json.loads(res['TmplData'])
            if ('Templates' not in tmplData or 'Info' not in tmplData):
                return []
            # Get base64-encoded templates
            templates = self.__getCorrectedTemplates(empID, tmplData['Templates'])
            templInfo = tmplData['Info']
            if (len(templates) != templInfo['numTemplates']):
                log.warn('Template and info are out of sync (%s)' % self.getProfileDataID())
                return []
            tpf = templInfo['numTemplates'] / len(templInfo['fingerInfo'])
            if (tpf not in (2,3)):
                log.err('Invalid number of templates per finger (%s)' % tpf)
                return []
            fingers = []
            for fingerIdx, info in enumerate(templInfo['fingerInfo']):
                code = info['code']
                quality = info['quality']
                finger = bioFinger.BioFinger(code, templates[fingerIdx*tpf:fingerIdx*tpf+tpf], quality)
                fingers.append(finger)
            return fingers
        except Exception as e:
            log.err('Error extracting template info: %s' % e)
        return []
    
    def hasTemplateInfo(self, empID):
        """ Return True if template info is available. """
        sql = 'SELECT TmplData FROM %s WHERE EmpID = ?' % self.tableName
        res = self.runSelectOne(sql, (empID,))
        if (res == None or not res['TmplData']):
            return False
        try:
            tmplData = json.loads(res['TmplData'])
            if ('Templates' in tmplData and 'Info' in tmplData):
                return True
        except Exception as e:
            log.err('Error checking for template info: %s' % e)
        return False

    def getUserIDsAndTemplateCount(self):
        """ Return dictionary with user IDs as keys and number of
        templates as values.
        """
        sql = 'SELECT EmpID, TmplCount FROM %s' % self.tableName
        res = self.runSelectAll(sql)
        userIDs = {}
        for row in res:
            userIDs[ row['EmpID'] ] = row['TmplCount']
        return userIDs

    def addJSONTemplData(self, empID, jTmplData):
        """ Replace existing JSON encoded tmplData for user and notify
        listener. 
        """
        tmplData = json.loads(jTmplData)
        try:
            encryptedData = (BioEncryption.getInstance().encryptTemplates(tmplData["Templates"]))
        except Exception as e:
            log.err("Failed to encrypt template {0}".format(e))    
            crashReport.createCrashReportFromException()
            return        
        
        tmplData["Templates"] = encryptedData
        jTmplData = json.dumps(tmplData)
        numTemplates = len(tmplData.get('Templates', []))
        sql = ('INSERT OR REPLACE INTO %s (EmpID, TmplCount, TmplData)'
               ' VALUES (?, ?, ?)') % self.tableName
        self.runQuery(sql, (empID, numTemplates, jTmplData))
        self.notifyTemplatesModified(empID, numTemplates)

    def deleteTemplates(self, empID):
        """ Delete templates from repository and notify listener. """
        sql = 'DELETE FROM %s WHERE EmpID = ?' % self.tableName
        res = self.runQuery(sql, (empID,))
        if (res): # only notify listeners if something was actually deleted
            self.notifyTemplatesDeleted(empID)
    
    def deleteAllTemplates(self):
        """ Delete all templates for all users. """
        sql = 'DELETE FROM %s' % self.tableName
        self.runQuery(sql)
        self.notifyTemplatesDeleted(None)


class _EmployeeDataRepository(Table):
    """ Template repository. """

    columnDefs = { 'EmpID' : 'TEXT UNIQUE NOT NULL',
                   'Type'  : 'TEXT NOT NULL',
                   'Data'  : 'TEXT' }

    def __init__(self, db=None, tableName='tblEmployeeDataRepository'):
        if (db == None):
            db = getAppDB()
        super(_EmployeeDataRepository, self).__init__(db, tableName)

    def getBase64Data(self, empID, dataType):
        """ Return base64 encoded data object or None or ''. """
        sql = 'SELECT Data FROM %s WHERE EmpID = ? AND Type = ?' % self.tableName
        res = self.runSelectOne(sql, (empID,dataType))
        return res['Data'] if res else None

    def addBase64Data(self, empID, dataType, data):
        """ Add or replace base64 encoded data. """
        sql = ('INSERT OR REPLACE INTO %s (EmpID, Type, Data)'
               ' VALUES (?, ?, ?)') % self.tableName
        self.runQuery(sql, (empID, dataType, data))

    def deleteData(self, empID, dataType):
        """ Delete data. """
        sql = 'DELETE FROM %s WHERE EmpID = ? AND Type = ?' % self.tableName
        self.runQuery(sql, (empID,dataType))



def getSettings():
    # Employee Settings
    sectionName = 'Employee'
    sectionComment = 'Settings for employee features.'
    empSection = SettingsSection(sectionName, sectionComment)
    s = ListSetting(empSection,
            name    = 'emp_limit_by', 
            label   = 'Limit employees by', 
            data    = 'table', 
            comment = ('If set to table the employee can only clock if present in the database. '
                       'WARNING: When not set to table, then the badge code, keypad ID and template ID ' 
                       'are the same for users not found in the DB! E.g: The keypad input when '
                       'identifying by keypad is used as badge code and template ID. ' 
                       'When set to supervisor the employee can be enrolled at the terminal by the supervisor.'))
    s.addAlias('emp_limit_to_db')
    s.addListOption('none', 'None')
    s.addListOption('table', 'Table')
    BoolSetting(empSection,
            name    = 'emp_enable_bio_identify', 
            label   = 'Enable bio identify', 
            data    = 'False', 
            comment = ('Enable/disable biometric when identifying'))
    NumberSetting(empSection,
            name    = 'emp_last_clockings_keeptime', 
            label   = 'Review clockings up to', 
            data    = '7', 
            units   = 'days', 
            comment = ('Time (in days) local clockings are kept in database for reviewing.'))
    TextSetting(empSection,
            name    = 'emp_default_verify_methods', 
            label   = 'Verification methods', 
            data    = 'bio,pin,none', 
            comment = ('Verification methods if not specified in EmpDB'))
    s = MultiListSetting(empSection,
            name    = 'emp_verify_override_methods', 
            label   = 'Verification overrides', 
            data    = 'bio|pin|cam|voice|noneIfBadge|noneIfBio|bioNone|none|denied', 
            comment = ('Possible verification methods for override'))
    s.addListOption('bio', 'Biometric')
    s.addListOption('pin', 'PIN')
    s.addListOption('cam', 'Camera Picture')
    s.addListOption('voice', 'Voice')
    s.addListOption('noneIfBadge', 'Pass if identified by badge')
    s.addListOption('noneIfBio', 'Pass if identified by biometric')
    s.addListOption('bioNone', 'Biometric (always pass)')
    s.addListOption('none', 'Always pass')
    s.addListOption('denied', 'Always deny')        

    s = MultiListSetting(empSection,
            name    = 'emp_override_languages', 
            label   = 'Language overrides', 
            data    = 'en|de|fr|nl|us', 
            comment = ('Possible language overrides'))
    s.addListOption('en')
    s.addListOption('de')
    s.addListOption('fr')
    s.addListOption('nl')
    s.addListOption('us')
    NumberSetting(empSection,
            name     = 'emp_pass_msg_sec', 
            label    = 'Pass msg time', 
            data     = '2', 
            units    = 'sec', 
            comment  = ('Time (in seconds) employee pass msg is displayed'))
    NumberSetting(empSection,
            name     = 'emp_fail_msg_sec', 
            label    = 'Fail msg time', 
            data     = '5', 
            units    = 'sec', 
            comment  = ('Time (in seconds) employee fail msg is displayed'))
    NumberSetting(empSection,
            name     = 'emp_enrol_quality', 
            label    = 'Enrol Quality', 
            data     = '70', 
            maxValue = '100', 
            comment  = ('Show warning if enrol quality is below this level'))
    BoolSetting(empSection,
            name    = 'emp_enable_bio_template_preview', 
            label   = 'Bio template preview', 
            data    = 'True', 
            comment = ('Enable/disable biometric template preview when enrolling'))
 
    # Local Supervisor Settings   
    sectionName = 'Local Supervisor'
    sectionComment = 'Settings for the Local Supervisor feature.'
    localSupervisorSection = SettingsSection(sectionName, sectionComment)
    BoolSetting(localSupervisorSection,
            name    = 'local_supervisor_enabled', 
            label   = 'Enable local supervisor', 
            data    = 'True', 
            comment = ('Enable/disable local supervisor'))
    NumberSetting(localSupervisorSection,
            name    = 'local_supervisor_id', 
            label   = 'Local supervisor ID', 
            data    = '1905', 
            comment = ('ID for keypad entry to identify as local supervisor'))
    NumberSetting(localSupervisorSection,
            name    = 'local_supervisor_pin', 
            label   = 'Local supervisor PIN', 
            data    = '1905', 
            comment = ('PIN for local supervisor'))
    TextSetting(localSupervisorSection,
            name    = 'local_supervisor_emp_id', 
            label   = 'Local Supervisor Employee ID', 
            data    = '00000000-0000-0000-0000-000000000001', 
            comment = ('Emp ID to be used in transaction when identified as local supervisor'))

    return [empSection,localSupervisorSection]
    
    
    