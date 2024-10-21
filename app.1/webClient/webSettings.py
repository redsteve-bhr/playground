# -*- coding: utf-8 -*-
#
# Copyright 2015 Grosvenor Technology
#
from applib.db.tblSettings import SettingsSection, TextSetting, NumberSetting, BoolSetting, ListSetting


def getSettings():
    # Web Client Section Settings
    sectionName = 'Web Client'
    sectionComment = 'These are the settings for connecting to the Web Service for sending transactions etc.'
    webClientSection = SettingsSection(sectionName, sectionComment)
    
    TextSetting(webClientSection,
            name     = 'webclient_host', 
            label    = 'Host', 
            data     = '', 
            comment  =  ('Web service host name or IP Address. The port number can be specified if it is not 80.'
                         'For example: 172.16.46.163:8080'))
    BoolSetting(webClientSection,
            name     = 'webclient_ssl', 
            label    = 'Enable SSL', 
            data     = 'True',
            comment  =  ('Enable/disable SSL. If enabled, https rather than http will be used. '))
    TextSetting(webClientSection,
            name     = 'webclient_resource', 
            label    = 'Resource', 
            data     = '/api', 
            comment  =  ('Web service resource prefix'))
    TextSetting(webClientSection,
            name     = 'webclient_username', 
            label    = 'User name', 
            data     = '', 
            comment  =  ('Web service login user name'))
    TextSetting(webClientSection,
            name     = 'webclient_password', 
            label    = 'Password', 
            data     = '', 
            comment  =  ('Web service login password'))
    TextSetting(webClientSection,
            name     = 'webclient_trans_online_tail', 
            label    = 'Transaction Online Resource Tail', 
            data     = '/transaction/online',
            comment  =  ('Resource tail for Online transactions.'))
    TextSetting(webClientSection,
            name     = 'webclient_trans_offline_tail', 
            label    = 'Transaction Offline Resource Tail', 
            data     = '/transaction/offline',
            comment  =  ('Resource tail for Offline transactions.'))
    BoolSetting(webClientSection,
            name     = 'webclient_check_certificate', 
            label    = 'Check certificate', 
            data     = 'False', 
            comment  =  ('Enable/disable certificate checking'))
    NumberSetting(webClientSection,
            name     = 'webclient_timeout', 
            label    = 'Connection timeout in seconds', 
            data     = '30',
            length   = '4',
            units    = 'sec', 
            comment  = ('Connection timeout in seconds'))
    NumberSetting(webClientSection,
            name     = 'webclient_retry_time', 
            label    = 'Retry time', 
            data     = '300',
            length   = '4',  
            units    = 'sec', 
            comment  = ('Retry time in seconds'))    
    NumberSetting(webClientSection,
            name     = 'webclient_changes_sync_period', 
            label    = 'Changes sync period', 
            data     = '30',
            units    = 'secs', 
            comment  = ('Frequency in seconds, changes are synchronised from web service'))    
    NumberSetting(webClientSection,
            name     = 'webclient_trans_warn_level', 
            label    = 'Trans Warning Level', 
            data     = '10',
            units    = '', 
            comment  = ('Minimum number of unsent transactions to show a warning'))    
    NumberSetting(webClientSection,
            name     = 'webclient_trans_max_level', 
            label    = 'Max Transactions', 
            data     = '2000',
            units    = '', 
            comment  = ('Maximum number of unsent transactions allowed in transaction buffer'))    
    NumberSetting(webClientSection,
            name     = 'webclient_trans_keep_time', 
            label    = 'Trans. keep time', 
            data     = str( 7 * 24 * 60 * 60 ),
            units    = 'sec', 
            comment  = ('Time (in seconds) to keep sent transactions in database'))  

    s = TextSetting(webClientSection,
            name     = 'webclient_employees_revision', 
            label    = 'Employees revision', 
            data     = '', 
            comment  =  ('Last employee revision loaded. This setting '
                         'does not need changing, but can be reset to force reloading.'))
    s.setAllowEdit(False)
    s.setHideInEditor(True)

    s = TextSetting(webClientSection,
            name     = 'webclient_employeeinfo_revision', 
            label    = 'EmployeeInfos revision', 
            data     = '', 
            comment  =  ('Last employee info revision loaded. This setting '
                         'does not need changing, but can be reset to force reloading.'))
    s.setAllowEdit(False)
    s.setHideInEditor(True)

    s = TextSetting(webClientSection,
            name     = 'webclient_buttons_revision', 
            label    = 'Buttons revision', 
            data     = '', 
            comment  =  ('Last buttons (buttons.xml) revision loaded. This setting '
                         'does not need changing, but can be reset to force reloading.'))
    s.setAllowEdit(False)
    s.setHideInEditor(True)

    s = TextSetting(webClientSection,
            name     = 'webclient_ca_certs_revision', 
            label    = 'Certificates revision', 
            data     = '', 
            comment  =  ('Last certificate (trusted_cacerts.crt) revision loaded. This setting '
                         'does not need changing, but can be reset to force reloading.'))
    s.setAllowEdit(False)
    s.setHideInEditor(True)

    s = TextSetting(webClientSection,
            name     = 'webclient_itcfg_revision', 
            label    = 'Itcfg revision', 
            data     = '', 
            comment  =  ('Last configuration (itcfg.xml) revision loaded. This setting '
                         'does not need changing, but can be reset to force reloading.'))
    s.setAllowEdit(False)
    s.setHideInEditor(True)

    s = TextSetting(webClientSection,
            name     = 'webclient_datacollection_revision', 
            label    = 'Data collection revision', 
            data     = '', 
            comment  =  ('Last data collection revision loaded. This setting '
                         'does not need changing, but can be reset to force '
                         'reloading of all data collection definitions. '))
    s.setAllowEdit(False)
    s.setHideInEditor(True)

    s = TextSetting(webClientSection,
            name     = 'webclient_schedules_revision', 
            label    = 'Schedules revision', 
            data     = '', 
            comment  =  ('Last schedules (schedules.xml) revision loaded. This setting '
                         'does not need changing, but can be reset to force reloading.'))
    s.setAllowEdit(False)
    s.setHideInEditor(True)

    s = TextSetting(webClientSection,
            name     = 'webclient_job_codes_revision',
            label    = 'Job Codes revision',
            data     = '',
            comment  =  ('Last job codes (jobCodes.xml) revision loaded. This setting '
                         'does not need changing, but can be reset to force reloading.'))
    s.setAllowEdit(False)
    s.setHideInEditor(True)

    s = TextSetting(webClientSection,
            name     = 'webclient_job_categories_revision',
            label    = 'Job Categories revision',
            data     = '',
            comment  =  ('Last job categories (jobCategories.xml) revision loaded. This setting '
                         'does not need changing, but can be reset to force reloading.'))
    s.setAllowEdit(False)
    s.setHideInEditor(True)

    NumberSetting(webClientSection,
            name     = 'webclient_ui_timeout', 
            label    = 'UI Timeout', 
            data     = '5',
            units    = 'sec', 
            comment  = ('User interface timeout (in seconds) for real time web service requests (online tasks,etc).'))    

    s = TextSetting(webClientSection,
            name     = 'webclient_auth_token', 
            label    = 'Auth-Token', 
            data     = '', 
            comment  =  ('Authentication token received from web service after registration.'))
    s.setAllowEdit(False)
    s.setHideInEditor(True)
    
    # Wizard Section Settings
    sectionName = 'Wizard Settings'
    sectionComment = 'These are the settings for changing the setup wizard for the terminal.'
    wizSection = SettingsSection(sectionName, sectionComment)
    s = BoolSetting(wizSection,
            name     = 'wiz_webclient_prompt_host',
            label    = 'Prompt for web client host',
            data     = 'True', # TODO: Change to False for release
            comment  = ('If True, ask for web client host.'))
    s.setAllowEdit(False)
    s.setHideInEditor(True)
    s = ListSetting(wizSection,
            name     = 'wiz_webclient_register', 
            label    = 'Webclient registration', 
            data     = 'optional', 
            comment  = ('Define if registration is required or optional.'))
    s.setAllowEdit(False)
    s.setHideInEditor(True)
    s.addListOption('never', 'Never')
    s.addListOption('optional', 'Optional')
    s.addListOption('required', 'Required')

    return [webClientSection, wizSection]
