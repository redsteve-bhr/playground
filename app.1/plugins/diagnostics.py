# -*- coding: utf-8 -*-
#
# Copyright 2023 Grosvenor Technology
#

import socket
from contextlib import closing
import itg
import cfg
import appit
import updateit
from applib.db.tblSettings import getAppSetting
from engine import dynButtons
from webClient import registerDevice, commsHelper
from webClient.webConfig import getAppWebClientSetup
import proxyServer
from clockserver.heartbeat import Heartbeat
from clockserver import comm

class Dialog(itg.Dialog):
    
    def __init__(self, emp=None):
        super(Dialog, self).__init__()
        self.terminalType = updateit.get_type().lower()[0:4]
        self.text = ''
        if self.terminalType in ['it51', 'it71']:
            view = itg.TextWithButtonsView(_('Diagnostics'), self.text, 'text/plain')
            view.setButton(0, _('Run Tests'), itg.ID_OK, self._startRun)
            view.setButton(1, _('Exit'), itg.ID_CANCEL, self.quit)
        else:
            view = itg.TextView(_('Diagnostics'), self.text, 'text/plain')
            view.setButton(_('Run Tests'), itg.ID_OK, self._startRun)
        self.addView(view)
        self._checkApplicationSettings()
        self._showText()
        self.setTimeout(60 * 5)

    def _startRun(self, btnId):
        """Runs the tests while showing a progress spinner"""
        self.text = ''
        self._runTests()
        self._showText()
        view = self.getView()
        if not self.terminalType in ['it51', 'it71']:
            view.setButton(_('Ok'), itg.ID_OK, self.quit)

    def _runTests(self):
        """Runs the complete suite of tests"""
        itg.waitbox(_('Checking Web-Client Registration. Please wait.'), self._checkRegistrationEndPoint)
        itg.waitbox(_('Checking Web-Client Sync Changes. Please wait.'), self._checkSyncChangesEndPoint)
        itg.waitbox(_('Checking Name Server. Please wait.'), self._checkNameServer)
        itg.waitbox(_('Checking Custom Exchange. Please wait.'), self._checkCustomExchangeHeartbeat)
        
    def _checkRegistrationEndPoint(self):
        """Attempts to call the Registration end-point, reporting any failures"""
        self._updateText('Checking Web-Client Registration')
        try:
            registerDevice.registerDevice()
            self._updateText('- Ok')
        except Exception as e:
            self._updateText('- ' + str(e))

    def _checkSyncChangesEndPoint(self):
        """Attempts to call the Sync Changes end-point, reporting any failures"""

        """ Send configuration request"""
        self._updateText('Checking Web-Client Sync Changes')
        appInfo = appit.AppInfo()
        extraParams = { 'AppRevision'            : '%s-%s.app' % (appInfo.name(), appInfo.version()),
                        'ButtonsRevision'        : getAppSetting('webclient_buttons_revision'),
                        'ItcfgRevision'          : getAppSetting('webclient_itcfg_revision'),
                        'CertificatesRevision'   : getAppSetting('webclient_ca_certs_revision') }
        try:
            with closing(commsHelper.openHttpConnection()) as conn:
                _ = commsHelper.httpGet(conn, '/changes/%s' % (getAppWebClientSetup().getDeviceID()), extraParams)
            self._updateText("- Ok")
        except Exception as e:
            self._updateText('- ' + str(e))
            
    def _checkCustomExchangeHeartbeat(self):
        self._updateText('Checking Custom Exchange')
        for (prefix, name) in ( ('clksrv', 'Primary Clockserver') , ('clksrv2', 'Secondary Clockserver')):
            try:
                proto = getAppSetting('%s_proto' % prefix)    
                host  = getAppSetting('%s_host' % prefix)
                port  = getAppSetting('%s_port' % prefix)
                path  = getAppSetting('%s_resource' % prefix)
                psk   = getAppSetting('%s_psk' % prefix)
                skip  = getAppSetting('%s_skip_https_certificate_checking' % prefix)
                clkid = getAppSetting('%s_id' % prefix)
                if (not host) or (host.strip() == ''):
                    self._updateText('- %s not enabled' % name)
                else:
                    result = self._sendTestCustomExchangeHeartbeat(clkid, proto, host, port, path, psk, skip)
                    if result:
                        self._updateText('- %s failed: %s' % (name, result))
                    else:
                        self._updateText('- %s Ok' % name)
            except Exception as e:
                self._updateText('- %s failed: %s' % (name, str(e))) 
    
    def _sendTestCustomExchangeHeartbeat(self, prefix, proto, host, port, path, psk, skip):
        try:
            term = updateit.get_type()
            mac  = cfg.get(cfg.CFG_NET_ETHADDR).replace(":", "").upper()
            serialNumber = cfg.get(cfg.CFG_PARTNO) 
            com  = comm.Comm(proto, host, path, port, psk, skipCC=skip)
            com.setup(prefix, term, mac, serialNumber)
            
            appInfo   = appit.AppInfo()
            version   = "%s,%s,%s" % (appInfo.version(),
                            updateit.get_version(),
                            updateit.get_build_date())
            hb = Heartbeat(120, version, updateTime=False)
            hb.comm = com
            hb.sendHeartbeat()
        except Exception as e:
            return str(e)
        
    def _checkNameServer(self):
        self._updateText('Checking DNS Lookup')
        
        try:
            hostName = 'example.com'
            ipAddress = socket.gethostbyname(hostName)
            self._updateText("- {}: {}".format(hostName, ipAddress))
        except Exception as e:
            self._updateText("- {}: {}".format(hostName, e))
            
        try:
            if proxyServer.useProxyServer():
                hostName = getAppSetting('proxy_host')
                ipAddress = socket.gethostbyname(hostName)
                self._updateText("- {}: {}".format(hostName, ipAddress))
        except Exception as e:
            self._updateText("- {}: {}".format(hostName, e))
        
        
    def _getAppSettingDefault(self, setting, default):
        value = getAppSetting(setting)
        if not value:
            value = default
        return value
    
    def _checkApplicationSettings(self):
        """Adds the basic application settings to the report"""
        appInfo = appit.AppInfo()
        self._updateText('App Version : %s-%s.app' % (appInfo.name(), appInfo.version()))
        self._updateText('')

        self._updateText('Webclient Settings')
        self._updateText('- Serial No.: %s' % getAppWebClientSetup().getSerialNumber())
        self._updateText('- Device ID: %s' % getAppWebClientSetup().getDeviceID())
        self._updateText('- Device Type: %s' % getAppWebClientSetup().getDeviceType())
        self._updateText('- IP: %s' % getAppWebClientSetup().getIP())
        self._updateText('- MAC: %s' % getAppWebClientSetup().getMAC())
        self._updateText('- Host: %s' % getAppWebClientSetup().getHostOnly())
        self._updateText('- Port: %d' % getAppWebClientSetup().getPort())
        self._updateText('- Username: %s' % getAppWebClientSetup().getUsername())
        self._updateText('- Password: %s' % getAppWebClientSetup().getPassword())
        self._updateText('- Resource API: %s' % getAppWebClientSetup().getResourcePrefix())
        self._updateText('- Certificate Checking: %s' % ('Yes' if getAppWebClientSetup().checkCertificate() else 'No'))
        self._updateText('- Proxy Host: %s' % getAppSetting('proxy_host'))
        self._updateText('- Proxy Port: %s' % getAppSetting('proxy_port'))
        self._updateText('- Proxy User: %s' % getAppSetting('proxy_auth_user'))
        self._updateText('- Proxy Password: %s' % getAppSetting('proxy_auth_password'))
        
        for (prefix, name) in ( ('clksrv', 'Primary Clockserver') , ('clksrv2', 'Secondary Clockserver')):
            self._updateText('')
            self._updateText('%s Settings' % name)
            proto = self._getAppSettingDefault('%s_proto' % prefix, '')    
            host  = self._getAppSettingDefault('%s_host' % prefix, '')
            port  = self._getAppSettingDefault('%s_port' % prefix, 80)
            path  = self._getAppSettingDefault('%s_resource' % prefix, '')
            skip  = self._getAppSettingDefault('%s_skip_https_certificate_checking' % prefix, '')
            clkid = self._getAppSettingDefault('%s_id' % prefix, '')
            fns   = self._getAppSettingDefault('%s_functions' % prefix, [])
            self._updateText('- Proto: %s' % proto)
            self._updateText('- Host: %s' % host)
            self._updateText('- Port: %d' % port)
            self._updateText('- Resource: %s' % path)
            self._updateText('- Device ID: %s' % clkid)
            self._updateText('- Functions: %s' % '|'.join([fn for fn in fns]))
            self._updateText('- Certificate Checking: %s' % ('No' if skip else 'Yes'))
        
    def _updateText(self, msg):
        """Adds the supplied msg text to the current on-screen text"""
        self.text += msg + '\n'
        
    def _showText(self):
        """Shows the current text"""
        view = self.getView()
        view.setText(self.text, mimeType='text/plain')
        
            
class DiagnosticsMenuAction(dynButtons.Action):
    
    def getName(self):
        return 'diagnostics'
    
    def getButtonText(self, actionParam, employee, languages):
        return _('Diagnostics')
    
    def getDialog(self, actionParam, employee, languages):
        return Dialog(employee)

    def getHelp(self):
        return """
        Show diagnostics menu.
        """        

def loadPlugin():
    dynButtons.registerAction(DiagnosticsMenuAction())
