# -*- coding: utf-8 -*-
#
# Copyright 2023 Grosvenor Technology
#
import re
import urllib
import cfg
import log
from collections import OrderedDict
from applib.db.tblSettings import getAppSetting

_config = None

def getCloudStorageConfig():
    """ Return global web client configuration. """
    global _config
    if (not _config):
        _config = _createCloudStorageConfig()
    return _config
    
def _createCloudStorageConfig():
    config = CloudStorageConfig()
    return config

class CloudStorageConfig(object):
    """Simple data class for accessing the Cloud Storage details"""
    
    def __init__(self):
        self.host = getAppSetting('cs_host')
        self.port = getAppSetting('cs_port')
        self.isSSL = getAppSetting('cs_ssl')
        self.container = getAppSetting('cs_container')
        
        # We cannot use urllib.unquote because the SAS Token contains embedded 
        # URL elements which must NOT be unquoted. Instead we simply replace 
        # any quoted ampersands, and leave the rest unchanged.
        # self.token = urllib.unquote(getAppSetting('cs_sas_token'))
        self.token = re.sub('%26', '&', getAppSetting('cs_sas_token'))
        
        self.skipCertificateCheck = getAppSetting('cs_skip_https_cert_checking')

        self.serialNumber = cfg.get(cfg.CFG_PARTNO)

    @property
    def params(self):
        """Returns the token split into a dictionary of params, as expected by
        the comms routines.
        """
        # Use an OrderedDict so that the parameters stay in the correct order
        params = OrderedDict()
        parts = self.token.split('&')
        for part in parts:
            subparts = part.split('=')
            if len(subparts) > 1:
                params[subparts[0]] = subparts[1]
            else:
                log.warn('Invalid token entry: %s' % part)

        return params

    @property
    def resource(self):
        return '/{}/{}/'.format(self.container, self.serialNumber)
