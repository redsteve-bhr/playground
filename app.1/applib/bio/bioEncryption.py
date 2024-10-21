# -*- coding: utf-8 -*-
#
# Copyright 2020 Grosvenor Technology
#
import log
import os
import bioReader
from applib.db.tblSettings import getAppSetting
import suprema2
from applib.utils import crashReport

_supremaEncryption = "suprema-aes256"
_keyFile = '../db/'+_supremaEncryption

class BioEncryption(object):
    """ Class for initialising the encryption of biometric templates in the reader and the terminal database.
    
    .. versionadded:: 4.2
    
    """
    
    __instance = None
    __key = None
    __isBioSupremaEncryptionEnabled = False
    
    def __init__(self):
        log.dbg("BioEncryption object creation")

    @staticmethod
    def init(deleteLocalTemplatesCb):
        """ BioEncryption.init(_deleteLocalTemplates) must be called before any *getInstance()* call
         to construct and initialize the BioEncryption object.
         It can only be called once as any further calls to it would result in an exception.
         It accepts a *deleteLocalTemplatesCb* which is a callback function which must be provided
         to delete local terminal templates.
        """
        if BioEncryption.__instance != None:
            raise Exception("BioEncryption class is a singleton!, please use getInstance() to call it")
        else:
            BioEncryption.__initialise(BioEncryption(), deleteLocalTemplatesCb)

    @staticmethod
    def getInstance():
        """ BioEncryption singleton class static access method which 
        returns the single instance of BioEncryption.
        """
        if BioEncryption.__instance == None:
            raise Exception("please call 'BioEncryption.init(callbackFunction)' method first first")
        return BioEncryption.__instance
    
    def isBioSupremaEncryptionEnabled(self):
        """ return whether suprema encryption is enabled
        """
        return self.__isBioSupremaEncryptionEnabled
                
    def __initialise(self, deleteLocalTemplatesCb):                
        """ Retrieve *deleteLocalTemplatesCb*, a callback function to delete local terminal templates.
        It initialises the singleton instance as well as the encryption setting and enables/disables encryption accordingly.
        """
        BioEncryption.__instance = self     
        self.__isBioSupremaEncryptionEnabled = getAppSetting('app_bio_encrypt') == _supremaEncryption        
        try:
            # Make sure Bio Reader is connected
            if (not bioReader.isInitialised()):
                bioReader.initialise()  
        except:
            log.dbg("No Bio Reader plugged in the terminal")                    
                    
        # See if biometric templates should be encrypted
        if (self.__isBioSupremaEncryptionEnabled):
            try:
                self.__enableSupremaEncryption(deleteLocalTemplatesCb)
            except Exception as e:
                log.err("Failed to enable Suprema encryption {0}".format(e))                                      
                crashReport.createCrashReportFromException()
        else:
            try:
                self.__disableSupremaEncryption(deleteLocalTemplatesCb)
            except Exception as e:
                log.err("Failed to disable Suprema encryption {0}".format(e))                                      
                crashReport.createCrashReportFromException()
                      
        if (bioReader.isInitialised()):
            log.dbg('bioReader encryption enabled {0}'.format(bioReader.isEncryptionEnabled()))
    
    def encryptTemplates(self, templates): 
        """ Retrieve a list of base64 *templates*.
        If encryption is enabled it encrypts them and returns a list of **base64** encrypted
        version of the templates.
        If encryption is disabled it returns the list of **base64** templates intact as passed in.
        """
        if (self.__isBioSupremaEncryptionEnabled):
            encryptedTemplates = suprema2.encryptTemplates(self.__key, templates)
            return encryptedTemplates
        else:
            return templates 
            
    def decryptTemplates(self, templates): 
        """ Retrieve a list of base64 *templates*.
        If decryption is enabled it decrypts them and returns an a list of **base64** encrypted
        version of the templates.
        If decryption is disabled it returns the list of **base64** templates intact as passed in.
        """
        if (self.__isBioSupremaEncryptionEnabled):
            dencryptedTemplates = suprema2.decryptTemplates(self.__key, templates)
            return dencryptedTemplates            
        else:
            return templates
    
    def __enableSupremaEncryption(self, deleteLocalTemplatesCb):
        # We are using Suprema AES256 encryption
        log.dbg('Suprema AES256 Encryption')
        # Check to see if key exists on terminal. If no key exists,create it & enableEncryption on the reader with that key 
        if not os.path.exists(_keyFile):
            # No Key, so generate one                    
            log.info("KeyFile not found. Creating Suprema encryption key. Please reload all existing templates")
                       
            # Create unique 64Hex Key (32bytes)
            self.__key =  os.urandom(32).encode('hex')                
            with open(_keyFile, 'w') as key:
                key.write(self.__key)
                            
            if (bioReader.isInitialised()):
                # Erase all templates from reader
                bioReader.deleteAllTemplates()
                # Set key in reader once
                bioReader.enableEncryption(self.__key)
            # Erase all templates from database, templates will need to be re-sent                
            deleteLocalTemplatesCb()
        else:
            # If key already there, just read it
            with open(_keyFile, 'r') as key:
                self.__key = key.read()
    
    def __disableSupremaEncryption(self, deleteLocalTemplatesCb):
        # Not using encryption
        log.dbg('No encryption')        
        # If reader's encryption enabled but app setting's encryption is set to None,
        # then probably the terminal was reset (and reader is still left to encryption mode ON)
        # so we ought to delete the reader's templates and disable ecryption on it
        if (bioReader.isInitialised()):
            if (bioReader.isEncryptionEnabled()):                                 
                bioReader.enableEncryption(None)
                bioReader.deleteAllTemplates()                      
        # Delete key in from terminal
        if os.path.exists(_keyFile):
            # Erase all templates from reader
            if (bioReader.isInitialised()):
                bioReader.deleteAllTemplates()            
            # Erase all templates from database, templates will need to be re-sent            
            deleteLocalTemplatesCb()
            os.remove(_keyFile)                
            log.info("KeyFile deleted. Please reload all existing templates")