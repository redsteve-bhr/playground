# -*- coding: utf-8 -*-
#
# Copyright 2015 Grosvenor Technology
#
from applib.db.tblSettings import SettingsSection, TextSetting, NumberSetting, BoolSetting, ListSetting, MultiListSetting

# This flag should be True for EasyClock-ws, False for EasyClock-ce
# The rest of the file should be the same
heartbeatOnly = True


def getClockserver1Settings():
    # Custom Exchange Section Settings
    sectionName = 'CustomExchange 1'
    if (heartbeatOnly):
        sectionComment = ('These are the settings for connecting to a Custom Exchange if required. '
                          'Custom Exchange is only used for Terminal Management and Heartbeats, '
                          'Transaction will be sent via the Web Service see Web Client section.')
    else:
        sectionComment = ('These are the settings for connecting to a Custom Exchange '
                          'Custom Exchange can be used for Heartbeats, Transactions, Enquiries, and Data Distribution.')                           
    section = SettingsSection(sectionName, sectionComment)

    s = MultiListSetting(section,
            name     = 'clksrv_functions', 
            label    = 'Functions', 
            data     = 'hb' if heartbeatOnly else 'hb|trans|enq|ddistr', 
            comment  = ('Select functionality. Transactions, enquiries and data distribution must only be selected for one clockserver'))
    s.addListOption('hb', 'Heartbeat')
    if (not heartbeatOnly):
        s.addListOption('trans', 'Transactions')
        s.addListOption('enq', 'Enquiries')
        s.addListOption('ddistr', 'Data Distribution')

    TextSetting(section,
            name     = 'clksrv_id', 
            label    = 'Device ID',
            data     = None,
            comment  = ('Unique Device ID (e.g. GB1234-1) of terminal for CustomExchange'))

    s = ListSetting(section,
            name     = 'clksrv_id_creation',
            label    = 'Device ID creation method',
            data     = 'partno',
            comment  = ('Select how to initially create Device ID of terminal.' ))
    s.addListOption('promptCountryCode', 'Prompt with country code')
    s.addListOption('prompt', 'Prompt')
    s.addListOption('default', 'Use default')
    s.addListOption('systemid', 'Use system ID')
    s.addListOption('ethaddr', 'Use MAC')
    s.addListOption('partno', 'Use part number')
    s.addListOption('uuid', 'Create UUID')
    s.setAllowEdit(False)
    s.setHideInEditor(True)

    s = TextSetting(section,
            name     = 'clksrv_id_default', 
            label    = 'Device ID default',
            data     = '0',
            comment  = ('Used to set Device ID of terminal when creation method is "Use default".'))
    s.setAllowEdit(False)
    s.setHideInEditor(True)

    s = ListSetting(section,
            name     = 'clksrv_proto',
            label    = 'Protocol',
            data     = 'http',
            comment  = ('Protocol to use for CustomExchange' ))
    s.addListOption('http')
    s.addListOption('https')
    s.addListOption('tcp')

    s = TextSetting(section,
            name     = 'clksrv_host', 
            label    = 'Host',
            data     = '',
            comment  = ('The CustomExchange server host name or IP Address'))
    s.addAlias('clksrv_url')

    NumberSetting(section,
            name     = 'clksrv_port', 
            label    = 'Port', 
            data     = '80',
            length   = '5',  
            comment  = ('CustomExchange TCP/IP port'))
    TextSetting(section,
            name     = 'clksrv_resource', 
            label    = 'Resource',
            data     = '/transactions/rs21.svc/postmessage',
            comment  = ('CustomExchange resource'))
    TextSetting(section,
            name     = 'clksrv_psk', 
            label    = 'Pre-shared key',
            data     = '',
            comment  = ('CustomExchange pre-shared key when using HTTPS'))
    NumberSetting(section,
            name     = 'clksrv_timeout', 
            label    = 'Timeout', 
            data     = '60',
            units    = 'sec',  
            comment  = ('CustomExchange connection timeout in seconds'))
    NumberSetting(section,
            name     = 'clksrv_hb_period', 
            label    = 'HB Period', 
            data     = '300',
            minValue = '15',
            units    = 'sec',  
            comment  = ('CustomExchange heartbeat period in seconds'))
    BoolSetting(section,
            name     = 'clksrv_hb_keep_alive', 
            label    = 'HB Keep-Alive', 
            data     = 'False', 
            comment  = ('If True the HB connection is re-used for file up-/downloads. This can improve download/upload speed.'))
    BoolSetting(section,
            name     = 'clksrv_hb_show_stats', 
            label    = 'HB Statistics', 
            data     = 'False', 
            comment  = ('If True statistic information of the HB are logged.'))
    NumberSetting(section,
            name     = 'clksrv_hb_warn_level', 
            label    = 'HB Warning Level', 
            data     = '1800',
            units    = 'sec',  
            comment  = ('Time (in seconds) of constant heartbeat failures before showing a warning'))
    BoolSetting(section,
            name     = 'clksrv_tz_ofs', 
            label    = 'Use TZ info', 
            data     = 'True', 
            comment  = ('Enable/disable sending offset to UTC information'))
    BoolSetting(section,
            name     = 'clksrv_skip_https_certificate_checking', 
            label    = 'Skip HTTPS certificate checking', 
            data     = 'False', 
            comment  = ('When set True and using HTTPS, certificate checking will be skipped'))
    BoolSetting(section,
            name     = 'clksrv_set_time_via_hb', 
            label    = 'Set time via HB', 
            data     = 'False', 
            comment  = ('When True, use time from heartbeat to set local time. It is recommended to use NTP for time synchronisation. NOTE: The NTP service must be disabled for this to work.'))
    if (not heartbeatOnly):
        NumberSetting(section,
                name     = 'clksrv_trans_warn_level', 
                label    = 'Trans. warn level', 
                data     = '10',
                comment  = ('Minimum number of unsent transactions to show a warning.'))
        NumberSetting(section,
                name     = 'clksrv_trans_max_level', 
                label    = 'Trans. max unsent', 
                data     = '20000',
                comment  = ('Maximum number of unsent transactions allowed in transaction buffer.'))
        NumberSetting(section,
                name     = 'clksrv_trans_keep_time', 
                label    = 'Trans. keep time', 
                data     = str( 7 * 24 * 60 * 60 ),
                units    = 'sec',
                comment  = ('Time (in seconds) to keep sent transactions in database.'))
        NumberSetting(section,
                name     = 'clksrv_distrdata_warn_level', 
                label    = 'Distr. warn level', 
                data     = '4',
                comment  = ('Minimum number of unsent data (templates, user pictures, etc.) to show a warning.'))
        NumberSetting(section,
                name     = 'clksrv_distrdata_max_level', 
                label    = 'Distr. max unsent', 
                data     = '100',
                comment  = ('Maximum number of unsent data allowed in distributed data buffer'))
    return section

      
def getClockserver2Settings():
    section = SettingsSection('CustomExchange 2')

    s = MultiListSetting(section,
            name     = 'clksrv2_functions', 
            label    = 'Functions', 
            data     = '', 
            comment  = ('Select functionality. Transactions, enquiries and data distribution must only be selected for one clockserver'))
    s.addListOption('hb', 'Heartbeat')
    if (not heartbeatOnly):
        s.addListOption('trans', 'Transactions')
        s.addListOption('enq', 'Enquiries')
        s.addListOption('ddistr', 'Data Distribution')

    s = ListSetting(section,
            name     = 'clksrv2_id_creation',
            label    = 'DeviceID creation method',
            data     = 'same',
            comment  = ('Select how to initially create device ID.' ))
    s.addListOption('promptCountryCode', 'Prompt with country code')
    s.addListOption('prompt', 'Prompt')
    s.addListOption('default', 'Use default')
    s.addListOption('systemid', 'Use system ID')
    s.addListOption('ethaddr', 'Use MAC')
    s.addListOption('partno', 'Use part number')
    s.addListOption('uuid', 'Create UUID')
    s.addListOption('same', 'Same as Clock Server 1')
    s.setAllowEdit(False)
    s.setHideInEditor(True)

    s = TextSetting(section,
            name     = 'clksrv2_id_default', 
            label    = 'DeviceID default',
            data     = '0',
            comment  = ('Used to set Device ID when creation method is "Use default".'))
    s.setAllowEdit(False)
    s.setHideInEditor(True)

    TextSetting(section,
            name     = 'clksrv2_id', 
            label    = 'DeviceID',
            data     = None,
            comment  = ('Unique device ID (e.g. GB1234-1) of terminal for CustomExchange'))

    s = ListSetting(section,
            name     = 'clksrv2_proto',
            label    = 'Protocol',
            data     = 'http',
            comment  = ('Protocol to use for CustomExchange' ))
    s.addListOption('http')
    s.addListOption('https')
    s.addListOption('tcp')

    s = TextSetting(section,
            name     = 'clksrv2_host', 
            label    = 'Server',
            data     = '',
            comment  = ('CustomExchange host name'))
    s.addAlias('clksrv2_url')

    NumberSetting(section,
            name     = 'clksrv2_port', 
            label    = 'Port', 
            data     = '80',
            length   = '5',  
            comment  = ('CustomExchange TCP/IP port'))
    TextSetting(section,
            name     = 'clksrv2_resource', 
            label    = 'Resource',
            data     = '/transactions/rs21.svc/postmessage',
            comment  = ('CustomExchange resource'))
    TextSetting(section,
            name     = 'clksrv2_psk', 
            label    = 'Pre-shared key',
            data     = '',
            comment  = ('CustomExchange pre-shared key when using HTTPS'))
    NumberSetting(section,
            name     = 'clksrv2_timeout', 
            label    = 'Timeout', 
            data     = '60',
            units    = 'sec',  
            comment  = ('CustomExchange connection timeout in seconds'))
    NumberSetting(section,
            name     = 'clksrv2_hb_period', 
            label    = 'HB Period', 
            data     = '300',
            minValue = '15',
            units    = 'sec',  
            comment  = ('CustomExchange heartbeat period in seconds'))
    BoolSetting(section,
            name     = 'clksrv2_hb_keep_alive', 
            label    = 'HB Keep-Alive', 
            data     = 'False', 
            comment  = ('If True the HB connection is re-used for file up-/downloads. This can improve download/upload speed.'))
    BoolSetting(section,
            name     = 'clksrv2_hb_show_stats', 
            label    = 'HB Statistics', 
            data     = 'False', 
            comment  = ('If True statistic information of the HB are logged.'))
    NumberSetting(section,
            name     = 'clksrv2_hb_warn_level', 
            label    = 'HB Warning Level', 
            data     = '7200',
            units    = 'sec',  
            comment  = ('Time (in seconds) of constant heartbeat failures before showing a warning'))
    BoolSetting(section,
            name     = 'clksrv2_tz_ofs', 
            label    = 'Use TZ info', 
            data     = 'True', 
            comment  = ('Enable/disable sending offset to UTC information'))
    BoolSetting(section,
            name     = 'clksrv2_skip_https_certificate_checking', 
            label    = 'Skip HTTPS certificate checking', 
            data     = 'False', 
            comment  = ('When set True and using HTTPS, certificate checking will be skipped'))
    BoolSetting(section,
            name     = 'clksrv2_set_time_via_hb', 
            label    = 'Set time via HB', 
            data     = 'False', 
            comment  = ('When True, use time from heartbeat to set local time. It is recommended to use NTP for time synchronisation. NOTE: The NTP service must be disabled for this to work.'))
    if (not heartbeatOnly):
        NumberSetting(section,
                name     = 'clksrv2_trans_warn_level', 
                label    = 'Trans. warn level', 
                data     = '10',
                comment  = ('Minimum number of unsent transactions to show a warning.'))
        NumberSetting(section,
                name     = 'clksrv2_trans_max_level', 
                label    = 'Trans. max unsent', 
                data     = '20000',
                comment  = ('Maximum number of unsent transactions allowed in transaction buffer.'))
        NumberSetting(section,
                name     = 'clksrv2_trans_keep_time', 
                label    = 'Trans. keep time', 
                data     = str( 7 * 24 * 60 * 60 ),
                units    = 'sec',
                comment  = ('Time (in seconds) to keep sent transactions in database.'))
        NumberSetting(section,
                name     = 'clksrv2_distrdata_warn_level', 
                label    = 'Distr. warn level', 
                data     = '4',
                comment  = ('Minimum number of unsent data (templates, user pictures, etc.) to show a warning.'))
        NumberSetting(section,
                name     = 'clksrv2_distrdata_max_level', 
                label    = 'Distr. max unsent', 
                data     = '100',
                comment  = ('Maximum number of unsent data allowed in distributed data buffer'))
    return section
