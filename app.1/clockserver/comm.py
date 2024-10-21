# -*- coding: utf-8 -*-
#
# Copyright 2011 Grosvenor Technology
#

import log
import base64
import httplib
import socket
import netinfo
import updateit
import cfg
import ssl
from applib.db import tblSettings
from applib.utils import netTrace
from applib.utils.timeUtils import TimeMeasure
from applib.db.tblSettings import getAppSetting
from proxyServer import useProxyServer


def getCommForFunction(function):
    clksrv1Functions = tblSettings.getAppSetting('clksrv_functions')
    clksrv2Functions = tblSettings.getAppSetting('clksrv2_functions')
    if (clksrv1Functions != None and function in clksrv1Functions):
        return getCommForPrefix('clksrv', 'primary')
    elif (clksrv2Functions != None and function in clksrv2Functions):
        return getCommForPrefix('clksrv2', 'secondary')
    return None

def getCommForPrefix(prefix, name):
    proto = tblSettings.getAppSetting('%s_proto' % prefix)
    host  = tblSettings.getAppSetting('%s_host' % prefix)
    path  = tblSettings.getAppSetting('%s_resource' % prefix)
    port  = tblSettings.getAppSetting('%s_port' % prefix)
    tout  = tblSettings.getAppSetting('%s_timeout' % prefix)
    psk   = tblSettings.getAppSetting('%s_psk' % prefix)
    skip  = tblSettings.getAppSetting('%s_skip_https_certificate_checking' % prefix)
    
    if (not host):
        log.warn('Host not configured for %s clockserver!' % name)
        return None

    comm = Comm(proto, host, path, port, psk, timeout=tout, skipCC=skip)
    comm.setName('%s clockserver' % name)
    comm.useTimeZoneOffset(tblSettings.getAppSetting('%s_tz_ofs' % prefix))

    clkid= tblSettings.getAppSetting('%s_id' % prefix)
    term = updateit.get_type()
    mac  = cfg.get(cfg.CFG_NET_ETHADDR)
    mac  = mac.replace(":", "").upper()
    serialNumber = cfg.get(cfg.CFG_PARTNO) 
    comm.setup(clkid, term, mac, serialNumber)
    return comm

# Cached SSL context for openHttpConnection
_sharedSSLContext = None

def _getProxyAuthorisationHeader():
    user = getAppSetting('proxy_auth_user')
    password = getAppSetting('proxy_auth_password')
    if getAppSetting('proxy_enabled') and (user != '') and (password != ''):
        auth = '%s:%s' % (user, password)
        return { 'Proxy-Authorization': 'Basic ' + base64.b64encode(auth) }
    else:
        return {}
        
class Comm(object):
    """A ClockServer Comm object can be created by specifying all 
    network parameters for HTTP.
    
    Before the newly created ClockServer Comm object can be used
    however, it is necessary to configure the parameters for the
    ClockServer message header. This can be done by using the setup()
    function.
    
    :param proto: is the protocol (e.g. http or https)
    :param host: is the host name or IP address of the server
    :param resource: is a path used for the HTTP POST request
    :param port is: the TCP port of the server (e.g. 80 or 8080)
    :param psk is: the HTTPS Pre-Shared Key
    :param timeout: specifies the connection timeout in seconds
    :param skipCC is: set True when using HTTPS, certificate checking will be skipped
    """

    def __init__(self, proto, host, resource, port, psk, timeout=10, skipCC=False):
        self.proto      = proto
        self.host       = str(host)
        self.resource   = str(resource)
        self.port       = str(port)
        self.psk        = str(psk)
        self.timeout    = int(timeout)
        self.skipCC     = skipCC
        self.useTZOffs  = False
        self.name       = 'clockserver'
    
    def setName(self, name):
        self.name = name
    
    def getName(self):
        return self.name

    def setup(self, clkid, device, mac, serialNumber):
        """Configure ClockServer message header.
        
        A ClockServer message header contains a number of informations which
        are the same for all messages. This function configures
        these informations. It is necessary to call this function before 
        calling send().
        
        :param clkid: is the ID of the terminal
        :param device: specifies the terminal type (e.g. 'IT3100' or 'IT4100')
        :param mac: is the MAC address of the terminal (e.g. '001122334455')
        """
        self.id = clkid
        self.device = device
        self.mac = mac
        self.serialNumber = serialNumber

    def useTimeZoneOffset(self, enable=None):
        """Configure how timezone should be send.
        
        If enable is None only the current setting will be returned.
        
        .. note:: The time is not part of the header. So this setting
                  is not used by the Comm object directly. Instead other
                  objects (e.g. the heartbeat or transaction class) will
                  query this information to find out whether to include
                  the timezone offset or not.
        
        :param enable: new setting or None if setting should stay unchanged
        :returns: current setting
        """
        if (enable != None):
            self.useTZOffs = enable
        return self.useTZOffs


    def getConnection(self, timeout=None):
        """ Return connection object """
        if (timeout == None):
            timeout = self.timeout
        else:
            timeout = int(timeout)
        
        if useProxyServer():
            host = getAppSetting('proxy_host')
            port = getAppSetting('proxy_port')
        else:
            host = self.host
            port = self.port
        
        log.dbg("Connecting to %s://%s:%s/%s" % (self.proto, self.host, self.port, self.resource))
        if (self.proto == 'https'):
            # See if skipping HTTPS certificate checking
            if (self.skipCC):
                # Using HTTPS, but skipping certificate checking
                conn = httplib.HTTPSConnection(host, port, timeout=timeout, context=ssl._create_unverified_context())
            else:
                # Create single SSL Context if not already done so, this is to save time
                global _sharedSSLContext
                if (_sharedSSLContext == None):
                    with TimeMeasure('Creating ClockServer SSL context'):
                        _sharedSSLContext = ssl._create_default_https_context()
                        
                # Using HTTPS, with certificate checking
                with TimeMeasure('Creating ClockServer HTTPSConnection'):
                    conn = httplib.HTTPSConnection(self.host, self.port, timeout=timeout, context=_sharedSSLContext)
        elif (self.proto == 'tcp'):
            # Using TCP
            conn = TCPConnection(self.host, self.port, timeout)
        else:
            # Using HTTP
            conn = httplib.HTTPConnection(host, port, timeout=timeout) 
        return conn


    def send(self, data, sendTerminalInfo=True, timeout=None, conn=None):
        """Send a message.
        
        This function will send a message to a ClockServer and return the
        response. 
        
        :param data: is the payload to send
        :param sendTerminalInfo: if true data will be send within the 
                                 terminal tag, if false the terminal tag will 
                                 be omitted
        :returns: the response
        """
        if (netinfo.eth_status() == netinfo.ETH_STATUS_NO_LINK):
            raise NameError, 'Network not functional (no link)';

        if (self.proto == 'https'):
            # Only send the psk field if https is enabled
            pskField = '  <psk>%s</psk>\n' % self.psk
        else:
            pskField = ''

        if (sendTerminalInfo):
            body = ('<interface>',
                    '<mac>%s</mac>' % self.mac,
                    '<device>%s</device>%s' % (self.device, pskField),                    
                    '<id>%s</id>' % self.id,
                    '<serialNumber>%s</serialNumber>' % self.serialNumber,
                    '<terminal>', '<unit>1</unit>', data.strip(), '</terminal>',
                    '</interface>','')
        else:
            body = ('<interface>',
                      '<mac>%s</mac>' % self.mac,
                      '<device>%s</device>%s' % (self.device, pskField),
                      '<id>%s</id>' % self.id,
                      '<serialNumber>%s</serialNumber>' % self.serialNumber,
                      data.strip(),
                    '</interface>','')
        closeConnection = (conn == None)
        # connect to webserver
        if (conn == None):
            conn = self.getConnection(timeout)

        body = '\r\n'.join(body)
        # send post request
        netTrace.traceOutput(body)
        headers = {"Content-Type": "text/plain", "Accept": "text/plain"}
        if useProxyServer():
            # Set the tunnel to point to the correct host (the connection object points
            # to the proxy server)
            host = self.host
            port = int(self.port)
            # Add the Proxy Authentication header if required
            headers.update(_getProxyAuthorisationHeader())
            conn.set_tunnel(host, port, headers)
            log.dbg("Calling %s via proxy server %s:%s" % (self.resource, conn.host, conn.port))
        conn.request('POST', self.resource, body, headers)

        # receive response
        response = conn.getresponse()

        # check response code
        if (response.status not in range(200, 300)):
            log.dbg("Response: %s" % response.read())
            raise NameError, 'HTTP %s' % response.status

        data = response.read()
        netTrace.traceInput(data)

        if (closeConnection):
            conn.close()
        return data


class TCPConnection(object):
    
    status = 200
    
    def __init__(self, host, port, timeout):
        self._socket = socket.create_connection( (host, port), timeout)
    
    def request(self, method, resource, body, headers):
        self._socket.sendall(body)
    
    def getresponse(self):
        return self
    
    def read(self):
        data = []
        while True:
            resp = self._socket.recv(4096)
            if (not resp):
                break
            data.append(resp)
        return ''.join(data)
    
    def close(self):
        self._socket.close()
        self._socket = None

    
