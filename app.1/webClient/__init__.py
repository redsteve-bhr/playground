# -*- coding: utf-8 -*-
#
# Copyright 2013 Grosvenor Technology
#
from webConfig import getJobQueue, getJobUITimeout
from webSettings import getSettings
from transaction import getAppTransactions, OnlineTransactionJob
from employeeInfo import EmployeeInfoRequest, getAppEmpInfo
from employeeUpdates import getAppEmpUpdatesQueue
from registerDevice import RegisterDeviceRequest
from webWizard import WebClientWizardRegisterPage, WebClientWizardHostPage
from start import start, load


def getHelp(appInfo):
    return """
Web Services
============

The %(appName)s application can communicate via HTTP or HTTPS with one or two 
servers running Web Services for different purposes. These are:

WS Protocol Web Service
-----------------------

The application will use this Web Service for the following functionality:

- Authentication
- Registration
- Transactions (e.g. used for clockings)
- Mechanism to detect changes
- Synchronisation of employee/user data
- Ability to upload changes to employee/user data (e.g. for enrolling biometric data)
- Synchronisation of employee specific information (e.g. balances, over-time, holidays left, etc)
- Loading of configuration data, including firmware and application updates

This Web Service follows the Representational State Transfer (REST) architecture. It is described
in the GTL document "Web Services for Workforce Management IT-Terminals".

Custom Exchange 
---------------

Optionally, the application can communicate with GTL's Custom Exchange platform.
This can be for the following reasons:

- Terminal Management
- File Transfer
- Heartbeats 

Communication will be via a Web Service. See the section Settings / CustomExchange 
in this document for details on how to set this up.

""" % appInfo
