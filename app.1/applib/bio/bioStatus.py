# -*- coding: utf-8 -*-
#
# Copyright 2012 Grosvenor Technology
#

import bioReader
from applib.bio import bioTemplates


def isWorkingAndHasFingersEnroled():
    """ Returns **True** if biometric reader was found and initialised,
    is working in identification mode and has templates enrolled. """ 
    if (not bioTemplates.hasTemplateRepository()):
        return False
    if (not bioReader.isInitialised()):
        return False
    if (bioTemplates.getTblBioTemplatesSyncStatus().getNumberOfUsers() > 0):
        return True
    return False

def isWorking():
    """ Returns **True** if biometric reader was found and initialised. """
    return bioReader.isInitialised()

