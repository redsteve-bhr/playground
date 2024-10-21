# -*- coding: utf-8 -*-
#
# Copyright 2011 Grosvenor Technology
#

import log
import os
import json

_started = False

def isSupported():
    return os.path.exists('pydevd.py')

def isStarted():
    return _started

def start(debugThreads=True):
    if (isSupported()):
        try:
            import pydevd_target #@UnresolvedImport
            os.environ["PATHS_FROM_ECLIPSE_TO_PYTHON"] = json.dumps(pydevd_target.PATHS_FROM_ECLIPSE_TO_PYTHON) 
            import pydevd #@UnresolvedImport
            log.info('Connecting to debugger (%s) ...' % pydevd_target.pydevdTarget)
            pydevd.settrace(pydevd_target.pydevdTarget, 
                            suspend=False, 
                            trace_only_current_thread=(not debugThreads))
            pydevd.set_pm_excepthook() # TODO: This seems to not be there anymore...
            global _started
            _started = True
        except Exception as e:
            log.warn('Error starting debugger: %s' % e)
