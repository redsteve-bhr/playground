# -*- coding: utf-8 -*-
#
# Copyright 2013 Grosvenor Technology
#

from engine import fileHandler

def loadPlugin():
    buttonHelpText = """
    The buttons file handler can import and export the buttons.xml file, which 
    defines the UI flow of the application. It defines and configures menus,
    buttons and their actions. See :ref:`buttons` for more information. 
    """.replace('    ', '')
    fh = fileHandler.PersistentProjectFileHandler('buttons.xml', restart=True, helpText=buttonHelpText)
    fileHandler.register('^buttons.xml$', fh, 'Buttons')
    backgroundHelpText = """
    The IT51 background image file handler is able to import and export a file
    named 'it51-background.png'. The file is used as background image for the 
    application and must have 1024 by 600 pixels.
    """.replace('    ', '')
    fh = fileHandler.PersistentBinaryProjectFileHandler('it51-background.png', restart=True, helpText = backgroundHelpText)
    fileHandler.register('^it51-background.png$', fh, 'IT51 Background')
