# -*- coding: utf-8 -*-
#
# Copyright 2017 Grosvenor Technology

import log
from applib.db.tblSettings import getAppSetting, SettingsSection, BoolSetting, TextSetting, NumberSetting

def useProxyServer():
    use = getAppSetting('proxy_enabled')
    if use:
        host = getAppSetting('proxy_host')
        if host.strip() == "":
            log.warn("Proxy Server enabled, but host not specified")
    return use
    
def getSettings():
    
    section = SettingsSection('ProxyServer')
    
    BoolSetting(section,
            name     = 'proxy_enabled', 
            label    = 'Enable Proxy Server', 
            data     = 'False',
            comment  =  ('Enable/disable Proxy Server'))
    TextSetting(section,
            name    = 'proxy_host', 
            label   = 'Proxy Server Host', 
            data    = '', 
            comment = ('Host name of proxy server'))
    NumberSetting(section,
            name    = 'proxy_port', 
            label   = 'Proxy Server Port', 
            data    = '3128', 
            comment = ('Port Number of Proxy Server'))
    TextSetting(section,
            name    = 'proxy_auth_user', 
            label   = 'Proxy Server Username', 
            data    = '', 
            comment = ('User name for proxy server authentication (leave blank if authentication is not required'))
    TextSetting(section,
            name    = 'proxy_auth_password', 
            label   = 'Proxy Server Password', 
            data    = '', 
            comment = ('Password for proxy server authentication (leave blank if authentication is not required'))

    return [section]
    