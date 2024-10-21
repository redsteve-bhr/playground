# -*- coding: utf-8 -*-
#
# Copyright 2013 Grosvenor Technology
#

from applib.utils import restartManager
import log
import os


# dynamically import all plugins
_modules = []
_module_names = set()
for module in sorted(os.listdir(os.path.dirname(__file__))):
    if (module == '__init__.py' or module == '__init__.pyc'):
        continue
    elif (module.endswith('.py')):
        module = module[:-3]
    elif (module.endswith('.pyc')):
        module = module[:-4]
    elif (os.path.exists(os.path.join(os.path.dirname(__file__), module, '__init__.py'))):
        pass
    elif (os.path.exists(os.path.join(os.path.dirname(__file__), module, '__init__.pyc'))):
        pass
    else:
        continue
    if (module in _module_names):
        continue
    _module_names.add(module)
    try:
        m = __import__(module, locals(), globals())
        _modules.append(m)
    except Exception as e:
        log.err('Error loading %s: %s' % (module, e))
del module



def getSettings():
    sections = []
    for m in (_modules):
        try:
            if (hasattr(m, 'getSettings')):
                log.dbg('Loading settings from %s' % m.__name__)
                sections.extend(m.getSettings())
        except Exception as e:
            log.err('Error while getting plugin settings %s (%s)' % (m.__name__, e))
    return sections

def load():
    for m in (_modules):
        try:
            if (not hasattr(m, 'loadPlugin')):
                log.warn('%s has no function "loadPlugin"!' % m.__name__)
            else:
                log.dbg('Loading %s' % m.__name__)
                m.loadPlugin()
        except Exception as e:
            log.err('Error while loading plugin %s (%s)' % (m.__name__, e))

def start():
    for m in (_modules):
        try:
            if (hasattr(m, 'startPlugin')):
                log.dbg('Starting %s' % m.__name__)
                m.startPlugin()
        except Exception as e:
            log.err('Error while starting plugin %s (%s)' % (m.__name__, e))
    restartManager.registerCleanup(stop)

def stop():
    for m in (_modules):
        try:
            if (hasattr(m, 'stopPlugin')):
                log.dbg('Stopping %s' % m.__name__)
                m.stopPlugin()
        except Exception as e:
            log.err('Error while stopping plugin %s (%s)' % (m.__name__, e))

