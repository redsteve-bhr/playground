# -*- coding: utf-8 -*-
#
# Copyright 2023 Grosvenor Technology
#
from applib.db.tblSettings import SettingsSection, TextSetting, BoolSetting, NumberSetting

def getSettings():
    
    sectionName = 'Cloud Storage'
    sectionComment = 'These are the settings for connecting to the Cloud Storage for uploading files'
    cloudStorageSection = SettingsSection(sectionName, sectionComment)

    BoolSetting(cloudStorageSection,
            name     = 'cs_use_cloud_storage', 
            label    = 'Enable Cloud Storage', 
            data     = 'False',
            comment  =  ('Enable/disable Cloud Storage. '))

    TextSetting(cloudStorageSection,
            name     = 'cs_host', 
            label    = 'Host', 
            data     = '', 
            comment  =  ('Cloud Storage host name'))

    BoolSetting(cloudStorageSection,
            name     = 'cs_ssl', 
            label    = 'Enable SSL', 
            data     = 'True',
            comment  =  ('Enable/disable SSL. If enabled, https rather than http will be used. '))

    NumberSetting(cloudStorageSection,
            name     = 'cs_port', 
            label    = 'Port', 
            data     = '443',
            length   = '5',  
            comment  = ('TCP/IP port'))

    TextSetting(cloudStorageSection,
            name     = 'cs_container', 
            label    = 'Container', 
            data     = 'devicediags', 
            comment  =  ('Cloud Storage container'))

    TextSetting(cloudStorageSection,
            name     = 'cs_sas_token', 
            label    = 'SAS Token', 
            data     = '', 
            comment  =  ('Cloud Storage SAS Token'))

    BoolSetting(cloudStorageSection,
            name     = 'cs_skip_https_cert_checking', 
            label    = 'Skip HTTPS Certificate Checking', 
            data     = 'False',
            comment  =  ('If enabled and using HTTPS, certificate checking will be skipped. '))

    return [cloudStorageSection]
