# -*- coding: utf-8 -*-
#
# Copyright 2011 Grosvenor Technology
#
import os
import applib
import appWizard
import appInitWizard
import appSettings
import appUpdate
import appDlg
import ssl
import log
import itg
import updateit
import gtmetrics

def hasCameraSupport():
    return hasattr(itg, 'WebcamView')

def getHelp(appInfo):
    return """
Overview
========

The %(appName)s application is a highly configurable and flexible Time and Attendance 
application program that runs on the IT series of terminals.

Purpose
-------

The main purpose of the application is to identify and verify users and then to present 
them with a configurable set of menus allowing actions such as clocking, absences or holiday 
booking.

Key features
------------

 - User interface configurable via XML.
 - Multi-language support.
 - Per user configurable verification methods.
 - User roles can be used to show different options. 
 - Local supervisor.
 - Biometric enrolment, identification and verification.
 - Custom Exchange support.
 - Web service support
 - AssistIT support for export and import.
 - USB export and import.

Web service and Custom Exchange
-------------------------------

%(appName)s is capable of communicating with a server that implements
the GTL web services and with Custom Exchange.

The web services can be used for:

 - Transactions (clockings, etc.).
 - Synchronising of employees and employee info.
 - Changing and uploading employee data (templates, PIN, etc.).
 - On demand (online) employee info.
 - Loading of system and application settings.
 - Updating of user interface and data collection definitions.
 - Updating of firmware and application.

.. note::
    Please be aware that some features may depend on the server implementation.

Custom Exchange can be used for:

 - Heartbeats
 - Loading of system and application settings
 - Updating of buttons and data collection definitions.
 - Updating of firmware and application.

.. note::
    Biometric template distribution is done via web services and 
    not Custom Exchange. Loading of settings and definitions must also 
    not be mixed, e.g. settings should come either from web services or 
    Custom Exchange.


""" % appInfo

    
#
# Entry point for application
#
if __name__ == '__main__':
    log.info('App Startup...')
    applib.debugger.start()

    # See if IT51 or IT71
    terminalType = updateit.get_type().lower()[0:4]
    
    gtmetrics.gtEvent(gtmetrics.EVT_APP_STARTUP)
    
    if (terminalType == 'it51'):
        # IT51 terminal, copy background image to theme directory.
        # Note the location media/images/it5100 has been added as a special for BanKoe
        log.info('Terminal type is IT51')
        for backgroundImage in ('/mnt/user/db/it51-background.png',
                                '/mnt/user/db/background.png',
                                'media/themefiles/it51-background.png',
                                'media/themefiles/background.png',
                                'media/images/it5100/it51-background.png',
                                'media/images/it5100/background.png'):
            if (os.path.exists(backgroundImage)):
                log.info('Copying %s to /tmp/theme/images' % backgroundImage)
                os.system('cp "%s" /tmp/theme/images/it5100/background.png' % backgroundImage)
                break
        if (os.path.exists('media/themefiles/it51-rotation.gif')):
            os.system('cp media/themefiles/it51-rotation.gif /tmp/theme/icons/rotation.gif')
    elif (terminalType == 'it71'):
        # IT71 terminal, copy background image to theme directory.
        # Note the location media/images/it7100 has been added as a special for BanKoe
        log.info('Terminal type is IT71')
        for backgroundImage in ('/mnt/user/db/it71-background.png',
                                '/mnt/user/db/background.png',
                                'media/themefiles/it71-background.png',
                                'media/themefiles/background.png',
                                'media/images/it7100/it71-background.png',
                                'media/images/it7100/background.png'):
            if (os.path.exists(backgroundImage)):
                log.info('Copying %s to /tmp/theme/images' % backgroundImage)
                os.system('cp "%s" /tmp/theme/images/it7100/background.png' % backgroundImage)
                break
        if (os.path.exists('media/themefiles/it71-rotation.gif')):
            os.system('cp media/themefiles/it71-rotation.gif /tmp/theme/icons/rotation.gif')

    # Turn on HTTPS certificate checking by default
    ssl._https_verify_certificates(True)

    app = applib.Application(appDlg.Dialog, appSettings.getDefaultSettings(), WizardDialogClass=appInitWizard.Dialog, UpgradeDialogClass=appUpdate.UpdateDialog)
    gtmetrics.mtxReport()
    app.run()
