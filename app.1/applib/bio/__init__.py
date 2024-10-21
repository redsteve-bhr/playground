# -*- coding: utf-8 -*-
#
# Copyright 2012 Grosvenor Technology
#
from applib.bio.bioIdentifyMixin import BioIdentifyMixin
from applib.bio.bioSyncDialog import BioSyncDialog
from applib.bio.bioInfoDialog import BioInfoDialog
from applib.bio.bioEnrolDialog import BioEnrolDialog, BioSimpleEnrolmentDialog
from applib.bio.bioVerifyDialog import BioVerifyDialog, employeeCanBeVerified
from applib.bio.bioThread import getBioLock, bioLockInit
from applib.bio.bioStatus import isWorkingAndHasFingersEnroled, isWorking
from applib.bio.bioTemplates import BioTemplateRepository, setTemplateRepository, hasTemplateRepository, getTemplateRepository
from applib.bio.bioEncryption import BioEncryption

import bioReader
import log


def load():
    try:
        bioLockInit()
        bioReader.initialise()
        log.dbg('Biometric unit initialised')
    except Exception as e:
        log.dbg('Unable to initialise biometric unit (%s)' % e)

    


