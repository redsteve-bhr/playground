# -*- coding: utf-8 -*-
import httplib
import urllib
import base64
import log
import ssl

from applib.utils import netTrace
from applib.utils.timeUtils import TimeMeasure
from applib.db.tblSettings import getAppSetting
from webConfig import getAppWebClientSetup
from proxyServer import useProxyServer

class UnauthorisedException(Exception):
    pass

 
def _getAuthorisationHeader():
    setup = getAppWebClientSetup()
    devID    = setup.getDeviceID()
    devToken = setup.getToken()
    if (not devToken):
        return {}
    return { 'Authorization' : 'Basic %s' % base64.b64encode("%s:%s" % (devID, devToken)) }
    
def _getAdditionalHeaders():
    return {'x-gt-serialnumber': getAppWebClientSetup().getSerialNumber()}

def _getProxyAuthorisationHeader():
    user = getAppSetting('proxy_auth_user')
    password = getAppSetting('proxy_auth_password')
    if getAppSetting('proxy_enabled') and (user != '') and (password != ''):
        auth = '%s:%s' % (user, password)
        return { 'Proxy-Authorization': 'Basic ' + base64.b64encode(auth) }
    else:
        return {}
        
def httpStreamRequest(conn, method, resource, body=None, extraParams=None):
    # create dictionary with parameters
    params = {}
    if (extraParams != None):
        params.update(extraParams)
    # create header
    headers = {'Accept': 'application/xml', 'Content-Type': 'text/xml; charset=utf-8', "Connection": "Keep-Alive" }
    headers.update(_getAuthorisationHeader())
    headers.update(_getAdditionalHeaders())
    # create resource with parameters
    resource = getAppWebClientSetup().getResourcePrefix() + resource
    resource = resource.replace('//', '/')
    resource = urllib.quote(resource)
    if (params):
        resource += '?' + urllib.urlencode(params) 
    log.dbg( 'HTTP %s %s' % (method, resource))
    # Only set up the proxy server if this connection is not already established
    if useProxyServer() and not conn.sock:
        # Set the tunnel to point to the correct host (the connection object points
        # to the proxy server)
        host = getAppWebClientSetup().getHostOnly()
        port = getAppWebClientSetup().getPort()
        # Add the Proxy Authentication header if required
        headers.update(_getProxyAuthorisationHeader())
        conn.set_tunnel(host, port, headers)
        log.dbg("Calling %s via proxy server %s:%s" % (resource, conn.host, conn.port))
    if (body):
        netTrace.traceOutput(body)
    conn.request(method, resource, body, headers)
    response = conn.getresponse()
    # check status code
    if (response.status not in (httplib.OK, httplib.CREATED, httplib.ACCEPTED, httplib.NO_CONTENT)):
        data = response.read()
        if (response.status == httplib.UNAUTHORIZED):
            raise UnauthorisedException('Unauthorised: %s' % data)
        netTrace.traceInput(data)
        if ('<html' in data or len(data)>200):
            data = httplib.responses.get(response.status, 'unknown')
        raise httplib.HTTPException('HTTP %s Error (%s)' % (response.status, data))
    return response

def httpRequest(conn, method, resource, body=None, extraParams=None):
    with TimeMeasure('httpRequest([%s] %s)' % (method, resource)):
        response = httpStreamRequest(conn, method, resource, body, extraParams)
        # read data and return
        data = response.read()
        netTrace.traceInput(data)
        return data

def httpGet(conn, resource, extraParams=None):
    """ Execute HTTP GET request on connection *conn* 
        with *resource* and optional *extraParams*.
    """
    return httpRequest(conn, 'GET', resource, None, extraParams)

def httpPost(conn, resource, body, extraParams=None):
    """ Execute HTTP POST request on connection *conn* 
        with *resource*, *body* and optional *extraParams*.
    """
    return httpRequest(conn, 'POST', resource, body, extraParams)

def httpPut(conn, resource, body, extraParams=None):
    """ Execute HTTP PUT request on connection *conn* 
        with *resource*, *body* and optional *extraParams*.
    """
    return httpRequest(conn, 'PUT', resource, body, extraParams)

def httpPatch(conn, resource, body, extraParams=None):
    """ Execute HTTP PATCH request on connection *conn* 
        with *resource*, *body* and optional *extraParams*.
    """
    return httpRequest(conn, 'PATCH', resource, body, extraParams)

def httpDelete(conn, resource, extraParams=None):
    """ Execute HTTP DELETE request on connection *conn* 
        with *resource* and optional *extraParams*.
    """
    return httpRequest(conn, 'DELETE', resource, None, extraParams)

# Cached SSL context for openHttpConnection
_sharedSSLContext = None

def openHttpConnection(certFile=None):
    # Get settings for connection
    if useProxyServer():
        host = getAppSetting('proxy_host')
        port = getAppSetting('proxy_port')
    else:
        host = getAppWebClientSetup().getHostOnly()
        port = getAppWebClientSetup().getPort()
    isSSL   = getAppWebClientSetup().isSSL()
    skip    = not getAppWebClientSetup().checkCertificate()
    log.dbg('host={0}, port={1}, isSSL={2}, skipCertificate={3}'.format(host, port, isSSL, skip))
    
    try:
        timeout = int(getAppSetting('webclient_timeout'))
    except Exception as e:
        log.err('Invalid webclient_timeout value: %s' % str(e))
        timeout = 30
            
    # See if doing HTTPS
    if (isSSL):
        # See if not checking certificates
        if (skip):
            # Using HTTPS, but skipping certificate checking
            conn = httplib.HTTPSConnection(host, port, timeout=timeout, context=ssl._create_unverified_context())
        else:
            # Using HTTPS, with certificate checking against /etc/ssl/cert.pem
            global _sharedSSLContext
            if (_sharedSSLContext == None):
                with TimeMeasure('Creating SSL context'):
                    _sharedSSLContext = ssl._create_default_https_context()
            # Using HTTPS, with certificate checking against /etc/ssl/cert.pem
            with TimeMeasure('Creating HTTPSConnection'):
                conn = httplib.HTTPSConnection(host, port, timeout=timeout, context=_sharedSSLContext, cert_file=certFile)   
                        
    else:
        # Using HTTP
        conn = httplib.HTTPConnection(host, port, timeout=timeout)
    return conn

