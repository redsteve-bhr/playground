# -*- coding: utf-8 -*-
#
# Copyright 2023 Grosvenor Technology
#
import log

class ActionRequestParams(object):
    """
    Class to read Action Request XML and extract any parameters from it.
    
    The parameters are key/value pairs, so they are stored internally in
    a dictionary, and can be accessed by treating this class as if it were
    a dictionary.
    
    I.E. values can be extracted by named index:
    
    value = actionRequestParams['key']
    
    Because all Action Request parameters are expected to be strings, unknown
    parameters will not throw an exception, but will instead simply return an
    empty string.
    
    The format of the Action Request XML is expected to match this example:
    
    <actionRequest>
       <resendClockings>
           <params>
               <param>
                   <name>startDate</name>
                   <value>2023-06-13 10:30:00</value>
               </param>
           </params>
       </resendClockings>
    </actionRequest>
    """

    def __init__(self):
        self.__items = {}

    def read(self, root):
        if root.tag != 'actionRequest':
            log.warn('Unexpected root in Action Request XML: "%s"' % root.tag)
            return
        params = root.findall('.//param')
        for param in params:
            nameElement = param.find('name')
            valueElement = param.find('value')
            if nameElement is None:
                log.warn('Invalid Action Request parameter. "name" is missing.')
                continue
            if valueElement is None:
                log.warn('Invalid Action Request parameter "%s". "value" is missing.' % nameElement.text)
                continue
            self.__items[nameElement.text] = valueElement.text

    def __getitem__(self, itemName):
        """Implementation for ActionRequestParams[key]"""
        if itemName in self.__items:
            return self.__items[itemName]
        else:
            log.warn('Unknown Action Request parameter: "%s"' % itemName)
            return ""
        
    def __contains__(self, key):
        """Implementation for 'key in ActionRequestParams'"""
        return key in self.__items
