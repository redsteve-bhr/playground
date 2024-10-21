# -*- coding: utf-8 -*-
#
# Copyright 2023 Grosvenor Technology
#
"""Unit tests for the Consents system"""

import unittest
import datetime
import log
from applib.utils import timeUtils

from consentManager import ConsentManager, ConsentStatus

class TestConsents(unittest.TestCase):

    testJsonString = """
        {
            "Templates": ["VWxOclRrWkpkM0ZXVlZsb..."],
            "Info": {"fingerInfo": [{"code": "ri", "quality": 70}], "numTemplates": 4},
            "Consents": [
                {
                    "id": "0c8d3abe-2187-3bf7-1f41-b60ddbd8f272",
                    "usage": "finger",
                    "source": "[DEVICE-ID]",
                    "time": "2023-01-12T11:30:00+0000",
                    "expiry": "2024-01-12T11:30:00+0000",
                    "action": "accepted",
                    "templateHashes": "",
                    "consentText": ""
                },
                {
                    "id": "f0d8d4d1-efc9-3501-e47a-0672aa8063dc",
                    "usage": "finger",
                    "source": "[DEVICE-ID]",
                    "time": "2022-01-12T11:30:00+0000",
                    "expiry": "2023-01-12T11:30:00+0000",
                    "action": "expired",
                    "templateHashes": "",
                    "consentText": ""
                }
            ]
        }
    """
    
    testJsonStringWithoutConsents = """
        {
            "Templates": ["VWxOclRrWkpkM0ZXVlZsb..."],
            "Info": {"fingerInfo": [{"code": "ri", "quality": 70}], "numTemplates": 4}
        }
    """
    
    def setUp(self):
        self.consents = ConsentManager()

    def tearDown(self):
        self.consents = None
        
    def testParseJSONString(self):
        """-- Can we parse a JSON string containing Consents?"""
        self.consents.parseJSONString(self.testJsonString)
        self.assertTrue(self.consents.count() == 2, "Expected 2 consent records, found {}".format(self.consents.count()))
        
    def testParseJSONStringWithNoConsents(self):
        """-- Can we parse a JSON string that does not contain Consents?"""
        self.consents.parseJSONString(self.testJsonStringWithoutConsents)
        self.assertTrue(self.consents.count() == 0, "Expected no consent records")
        
    def testAdd_DefaultValues(self):
        """-- Can we add a new Consent Record with default values?"""
        self.consents.add(None, None, None, None)
        self.assertTrue(self.consents.count() == 1, "Failed to add Consent Record")

    def testIsExpiring(self):
        """-- Can we detect that a Consent is expiring?""" 
        self.consents.parseJSONString(self.testJsonString)
        self.consents.records[0].expiry = "2022-01-12T11:30:00+0000"
        atDate = timeUtils.getUTCDatetimeFromISO8601("2022-01-11T11:30:00+0000")
        
        status = self.consents.getStatus(atDate)
        expiring = status == ConsentStatus.EXPIRING
        self.assertTrue(expiring, "Expected consent to be expiring, but was {}".format(status))

    def testIsExpired(self):
        """-- Can we detect that a Consent is expired?""" 
        self.consents.parseJSONString(self.testJsonString)
        self.consents.records[0].expiry = "2022-01-12T11:30:00+0000"
        atDate = timeUtils.getUTCDatetimeFromISO8601("2022-01-13T11:30:00+0000")
        
        status = self.consents.getStatus(atDate)
        expired = status == ConsentStatus.EXPIRED
        self.assertTrue(expired, "Expected consent to be expired, but was {}".format(status))

        
class Tests(object):

    def run(self):
        log.dbg("=" * 78)
        log.dbg("Running Consent Tests")
        log.dbg("=" * 78)
        suite = unittest.TestLoader().loadTestsFromTestCase(TestConsents)
        unittest.TextTestRunner(verbosity=2).run(suite)
        log.dbg("=" * 78)
        log.dbg("Consent Tests completed")
        log.dbg("=" * 78)
    