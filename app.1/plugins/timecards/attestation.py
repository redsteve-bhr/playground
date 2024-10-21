# -*- coding: utf-8 -*-
#
# Copyright 2023 Grosvenor Technology
#
import os
import xml.etree.cElementTree as ET
import miscUtils

import log

class Reason(object):
    """Simple data class to hold the details of one Attestation Reason."""
    
    def __init__(self, reasonID, icon=None, text=''):
        self.reasonID = reasonID
        self.icon = icon
        self.text = text

class Attestation(object):
    """Class to read and store Attestation details (as retrieved from
    attestation.xml). Creating an instance of the class automatically reads the
    data from the current attestation.xml file, if it it exists. If it does not
    exist, it uses default values (?).
    """
    
    def __init__(self, employee):
        self.employee = employee
        self.load()
        
    def reset(self):
        self.prompt = ''
        self.agreeButtonText = 'Agree'
        self.disagreeButtonText = 'Disagree'
        self.reasons = []
        
    def load(self):
        """Load the details from `attestation.xml`, if it exists."""
        self.reset()
        if not os.path.exists('/mnt/user/db/attestation.xml'):
            log.warn('attestation.xml not found')
            return
        
        lang = self.employee.getLanguage()
        
        with open('/mnt/user/db/attestation.xml') as f:
            data = f.read()
            
        root = ET.fromstring(data)
        if root.tag != 'attestation':
            log.err('Error parsing attestation.xml. Expected root of "attestation" but got "%s"' % root.tag)
            return

        self.prompt = " ".join(miscUtils.getElementText(root, 'promptDialog/prompt', 'Prompt not found!', warn=True, language=lang).split())
        self.agreeButtonText = miscUtils.getElementText(root, 'promptDialog/agreeButton/label', 'Agree', warn=True, language=lang)
        self.disagreeButtonText = miscUtils.getElementText(root, 'promptDialog/disagreeButton/label', 'Disagree', warn=True, language=lang)
        
        reasonList = root.findall('reasons/reason')
        for reasonElement in reasonList:
            reasonID = miscUtils.getElementText(reasonElement, 'id', 'No-ID', warn=True)
            icon = miscUtils.getElementText(reasonElement, 'icon', None, warn=False)
            text = miscUtils.getElementText(reasonElement, 'text', 'Unknown', warn=True, language=lang)
            self.reasons.append(Reason(reasonID, icon, text))
