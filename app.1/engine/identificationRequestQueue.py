# -*- coding: utf-8 -*-
#
#
import log

_queue = []


class _IdentificationRequest(object):
    
    def __init__(self, readerInputType):
        if (readerInputType not in ('bio', 'card')):
            raise Exception('Unsupported reader input type: %s' % readerInputType)
        self._type = readerInputType
        self._empPicture = None
        self._requestData = None
        self._cardReaderRequestData = None
        self._biometricRequestData = None
    
    def isCardReaderRequest(self):
        return (self._type == 'card')
    
    def isBiometricRequest(self):
        return (self._type == 'bio')
    
    def getRequestData(self):
        return self._requestData
    
    def setEmpPicture(self, empPicture):
        self._empPicture = empPicture
    
    def getEmpPicture(self):
        return self._empPicture


class _CardReaderRequest(_IdentificationRequest):
    
    def __init__(self):
        super(_CardReaderRequest, self).__init__('card')    

    def setRequestData(self, valid, reader, decoder, data):
        self._requestData = (valid, reader, decoder, data)
    

class _BiometricRequest(_IdentificationRequest):
    
    def __init__(self):
        super(_BiometricRequest, self).__init__('bio')    

    def setRequestData(self, tmplID):
        self._requestData = tmplID
    

def addCardReaderRequest(valid, reader, decoder, data, empPicture=None):
    """ Queue read data from reader. """ 
    # only allow one entry
    if (len(_queue) > 0):
        log.warn('Inserting swipe data into non-empty swipe queue!')
        return
    ri = _CardReaderRequest()
    ri.setRequestData(valid, reader, decoder, data)
    ri.setEmpPicture(empPicture)
    _queue.append(ri)

def addBiometricRequest(tmplID, empPicture=None):
    """ Queue read data from biometric unit. """ 
    # only allow one entry
    if (len(_queue) > 0):
        log.warn('Inserting biometric data into non-empty swipe queue!')
        return
    ri = _BiometricRequest()
    ri.setRequestData(tmplID)
    ri.setEmpPicture(empPicture)
    _queue.append(ri)

def getNext():
    """ Remove and return next request from queue. """
    if (_queue):
        return _queue.pop(0)
    return None

def clear():
    """ Clear queue. """
    del _queue[:]

