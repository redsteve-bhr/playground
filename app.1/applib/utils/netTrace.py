# -*- coding: utf-8 -*-
#
# Copyright 2013 Grosvenor Technology
#


"""
:mod:`netTrace` --- Helper functions for logging network in/output 
==================================================================

.. versionadded:: 2.1

The :mod:`~applib.utils.netTrace` module provides the functions 
:func:`~applib.utils.netTrace.traceInput` and :func:`~applib.utils.netTrace.traceOutput`
to nicely log incoming and outgoing network data. The data is nicely formatted if possible
(XML and JSON). Only the start and end of the data is logged if there are too many
lines to prevent flooding the log buffer.

The data is also only logged (via :func:`log.net`) if network logging is enabled (see :mod:`log`). 

Example::

    conn = httplib.HTTPConnection(host)
    conn.request('GET', '/')
    # receive response
    response = conn.getresponse()
    # check response code
    if (response.status != httplib.OK):
        raise Exception('HTTP Error %s' % response.status)
    data = response.read()
    netTrace.traceInput(data)


        
"""

import log
import xml.etree.cElementTree

try:   
    import json
    jsonSupported = True
except ImportError:
    jsonSupported = False
    
def _indent(elem, level=0):
    i = "\n" + level*"  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for elem in elem:
            _indent(elem, level+1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i

def _fromXMLString(data):
    xmlData = xml.etree.cElementTree.fromstring(data)
    _indent(xmlData)
    lines = xml.etree.cElementTree.tostring(xmlData).split('\n')
    return lines

def _fromJSONString(data):
    return json.dumps(json.loads(data), sort_keys=True, indent=4).split('\n')

def _traceData(label, data, maxLines, maxWidth):
    try:
        data = data.strip()
        if (data.startswith('<')):
            lines = _fromXMLString(data)
        elif (jsonSupported and data.startswith('{') or data.startswith('[')):
            lines = _fromJSONString(data)
        else:
            lines = data.split('\n')
        if (len(lines) > maxLines):
            lines[maxLines-10:-10] = ['--- skipped %d lines ---' % (len(lines)-maxLines),] 
        for i, l in enumerate(lines):
            log.net('[%s] %04d: %s' % (label, i+1, l[:maxWidth]))
    except Exception as e:
        log.err('Error logging network data: %s' % (e,))
        
def traceOutput(data, maxLines=50, maxWidth=180):
    """ Log network output if network logging is enabled. *data* is a **string**
    containing the network data. The data is logged nicely formatted if it is XML 
    or JSON. 
    Only *maxLines* are logged, of which only the first *maxWidth* characters are
    shown. Data bigger than 100k is not logged at all.
    """
    if (not log.net_enabled):
        return
    if (len(data) > (100*1000)):
        log.net('Skipped logging of %d bytes of outgoing network traffic' % len(data))
    else:
        _traceData('TX', data, maxLines, maxWidth)

def traceInput(data, maxLines=50, maxWidth=180):
    """ Log network input if network logging is enabled. *data* is a **string**
    containing the network data. The data is logged nicely formatted if it is XML 
    or JSON. 
    Only *maxLines* are logged, of which only the first *maxWidth* characters are
    shown. Data bigger than 100k is not logged at all.
    """
    if (not log.net_enabled):
        return
    if (len(data) > (100*1000)):
        log.net('Skipped logging of %d bytes of incoming network traffic' % len(data))
    else:
        _traceData('RX', data, maxLines, maxWidth)
