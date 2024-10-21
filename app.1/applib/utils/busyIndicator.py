# -*- coding: utf-8 -*-
#
# Copyright 2011 Grosvenor Technology
#

"""
:mod:`busyIndicator` --- Showing background activity
====================================================

This module provides an easy way of showing the progress icon on the
:class:`itg.IdleMenuView` when certain background tasks are performed.

For it to work, the :class:`itg.IdleMenuView` needs to be registered::

    class Dialog(itg.Dialog):
    
        def __init__(self):
            super(Dialog, self).__init__()
            view = itg.IdleMenuView()
            # [...]  
            busyIndicator.setIconView(view) # set idle view
            self.addView(view)
            self.disableTimeout()

After that, background tasks can signal activity::

    # [...]
    with busyIndicator.BusyIndicator(_('Calculating XYZ')):
        self.calculateXYZ()        

The busy icon is shown on the idle screen while self.calculateXYZ() is executed.
The user can click on the icon and see the message "Calculating XYZ".             

"""

import itg
import weakref
from applib.utils import resourceManager

_iconViewRef = None

def setIconView(view):
    global _iconViewRef
    _iconViewRef = weakref.ref(view) if (view) else None


class BusyIndicator(object):
    
    def __init__(self, label):
        self.__iconView = _iconViewRef() if _iconViewRef else None
        self.__icon = resourceManager.get('applib/icons/progress')
        self.__label = label
        self.__dlg = None
    
    def __enter__(self):
        if (self.__iconView):
            itg.runLater(self.__iconView.addIcon, (self.__icon, self.__onIconPress))
    
    def __exit__(self, exc_type, exc_value, traceback):
        if (self.__iconView):
            itg.runLater(self.__iconView.removeIcon, (self.__icon,))
        if (self.__dlg):
            itg.runLater(self.__dlg.quit, (itg.ID_TIMEOUT,))
            
    def __onIconPress(self):
        self.__dlg = _BusyInfoDialog(self.__label)
        self.__dlg.run()
        self.__dlg = None
        

class _BusyInfoDialog(itg.Dialog):
    
    def __init__(self, text):
        super(_BusyInfoDialog, self).__init__()
        view = itg.CancellableWaitBoxView()
        view.setText(text)
        view.setButton(0, _('Cancel'), itg.ID_CANCEL, self.cancel)
        self.addView(view)
        self.disableTimeout()


