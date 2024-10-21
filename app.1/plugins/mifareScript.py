# -*- coding: utf-8 -*-
#
# Copyright 2013 Grosvenor Technology
#
from engine import fileHandler
import os
import cfg


def loadPlugin():
    helpText = """
The Mifare XML file handler can import and export a Mifare script. A 
Mifare script file can be used by the application to access information
from Mifare cards.

The reader decoder (*it_reader_decoder*) must also be set to "Mifare Application" 
(109), before the application can use the Mifare script.

    """
    fh = fileHandler.PersistentProjectFileHandler('mifare.xml', restart=True, helpText=helpText)
    fileHandler.register('^mifare.xml$', fh, 'Mifare XML script')
    helpText = """
The Mifare script (mifare.script) file is an encrypted Mifare XML script (see
:ref:`file_handler_mifare_script`).

The reader decoder (*it_reader_decoder*) must also be set to "Mifare Application" 
(109), before the application can use the Mifare script.

    """
    fh = fileHandler.PersistentProjectTextFileHandler('mifare.script', restart=True, helpText=helpText)
    fileHandler.register('^mifare.script$', fh, 'Mifare script')

def startPlugin():
    if (cfg.get(cfg.CFG_RDR_DECODER) != '109'):
        return
    for scriptName in ('/mnt/user/db/mifare.script', '/mnt/user/db/mifare.xml'):
        if (os.path.exists(scriptName)):
            import mifare
            script = open(scriptName, 'r').read().strip()
            mifare.init()
            mifare.setDefaultScript(script)
            mifare.runDefaultScript()    
            return

