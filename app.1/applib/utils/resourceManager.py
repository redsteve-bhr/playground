# -*- coding: utf-8 -*-
#
# Copyright 2010 Grosvenor Technology
#



"""
:mod:`resourceManager` --- Resource Manager module
==================================================

This module helps organising resources for the application. Although **ITG** and 
the IT libraries make it easy to write applications and run them on different terminal
platforms (e.g. IT31, IT51, etc), some  resources like images need to be different to 
accommodate the different screen sizes and colours. 

To keep using these resources easy, this module provides a function which will return 
the right resource for the terminal it is currently running on.

For example::

    errorIcon = resourceManager.get('applib/icons/warn')
    
The code above will return 'applib/icons/it3100/warn.bmp' on an IT31 and 'applib/icons/default/warn.png' on 
all other terminal types which do not provide a terminal specific icon.

The directory structure might be as follows::

    applib/icons/it3100/warn.bmp
    applib/icons/it3100/nolink.bmp    
    applib/icons/it5100/
    applib/icons/it5100/nolink.png    
    applib/icons/default/warn.png
    applib/icons/default/nolink.png    

Before using these resources it is necessary to register the directory::

    resourceManager.addResourceDir('applib/icons')
    
.. note::
    The "applib/icons" directory is automatically registered during :class:`applib.Application` 
    initialisation.
    
After registering a directory, it is possible to get the right resource for a terminal
by requesting the file and leaving off the terminal type directory and file extension.

For example::

    resourceManager.get('applib/icons/warn')
    # IT31: applib/icons/it3100/warn.bmp
    # IT51: applib/icons/default/warn.png
    # ITXX: applib/icons/default/warn.png
    
    resourceManager.get('applib/icons/nolink')
    # IT31: applib/icons/it3100/nolink.bmp
    # IT51: applib/icons/it5100/nolink.png
    # ITXX: applib/icons/default/nolink.png

The 'default' directory is used when no resource file can be found in the terminal type
specific path.

:func:`resourcemanager.get` will only search for resources in the given directory, so the
following will not conflict:: 

    resourceManager.addResourceDir('icons')
    resourceManager.addResourceDir('special/images')
    
    # lets assume this is on an IT51
    resourceManager.get('applib/icons/myicon') # will only look for myicon* in applib/icons/it5100 or applib/icons/detault
    resourceManager.get('icons/myicon')  # will only look for myicon* in icons/it5100 or icons/detault
    resourceManager.get('special/images/buddy')  # will only look for buddy* in special/images/it5100 or special/images/detault    


"""



import updateit
import glob
import os

_resourceDirs = set()
_resources = {}

def addResourceDir(path):
    """ Add a resource directory."""
    global _resourceDirs
    _resourceDirs.add(path)
    reload()

def reload(): #@ReservedAssignment
    """ Reload cache for added resource directories."""
    global _resources
    _resources = {}
    for path in _resourceDirs:
        for sub in [ 'default', updateit.get_type().lower() ]:
            files = glob.glob( os.path.join(path, sub, '*'))
            for f in files:
                name = os.path.join(path, os.path.basename(f))
                (name, _ext) = os.path.splitext(name)
                _resources[name] = f

def get(name):
    """ Get resource. *name* is the path of the resource without the 
    terminal type directory and file extension. If no resource is
    found **None** is returned and a warning is logged.
    """ 
    global _resources
    if (name in _resources):
        return _resources[name]
    return None
