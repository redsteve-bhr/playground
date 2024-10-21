# -*- coding: utf-8 -*-
#
# Copyright 2010 Grosvenor Technology
#

"""
:mod:`xmlTime` --- Time functions
=================================

This package contains functions, which make time handling and conversion
easier. 
 
 
"""

import time

xmlTimeFormat = "%Y-%m-%dT%H:%M:%S%z"

def getXMLTimestampNow():
    """Get the XML formated local time (plus UTC offset).
    
    The format is "%Y-%m-%dT%H:%M:%S%z", which is also used as time
    format in XML.
    
    :returns: the current time
    """
    return time.strftime(xmlTimeFormat)

