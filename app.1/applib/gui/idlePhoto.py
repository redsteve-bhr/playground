# -*- coding: utf-8 -*-
#
# Copyright 2011 Grosvenor Technology
#
"""
:mod:`idlePhoto` -- IdlePhoto Mix-In
========================================

.. versionadded:: 1.5

The :class:`IdlePhotoMixin` class is an easy to use Mix-In to add 
a live photo preview to a dialog (normally the idle dialog) and give
simple functions to take a photo. 

The two important methods are:

 - :meth:`IdlePhotoMixin.enableIdlePhoto`
 - :meth:`IdlePhotoMixin.getIdlePhoto`

:meth:`IdlePhotoMixin.enableIdlePhoto` should be called when creating the dialog 
(e.g. in the constructor or in :meth:`itg.Dialog.onCreate`. It is safe to do this 
even on terminals not supporting a webcam. The live photo preview is shown 
automatically when the dialog is shown. The preview is hidden automatically as well.

:meth:`IdlePhotoMixin.getIdlePhoto` can be used to acquire the photo.

Example::

    class IdleDialog(idlePhoto.IdlePhotoMixin, itg.Dialog):

        def __init__(self):
            super(IdleDialog, self).__init__()
            view = itg.IdleMenuView()
            view.setText(getAppSetting('app_idle_time_fmt'),
                         getAppSetting('app_idle_date_fmt'), 
                         getAppSetting('app_idle_title'))
            view.setButton(0, _('Login'), 0, self.__onLogin)
            if (getAppSetting('app_idle_photo_enable')):
                self.enableIdlePhoto() # enabling photo preview
            self.addView(view)

        def __onLogin(self, btnID):
            idlePhoto = self.getIdlePhoto() # take photo
            # Use or save photo
            [...]
        

Integration with screensaver
----------------------------

:class:`IdlePhotoMixin` integrates well with the :class:`applib.gui.screensaver.ScreensaverMixin`. 
:class:`IdlePhotoMixin` automatically stops the live photo preview when
:meth:`applib.gui.screensaver.ScreensaverMixin.startScreensaver` is called and starts it again
when :meth:`applib.gui.screensaver.ScreensaverMixin.stopScreensaver` is executed.

.. important:: For this to work, the order of how the Mix-Ins are included is very important. 

Example::

    class IdleDialog(idlePhoto.IdlePhotoMixin, screensaver.ScreensaverMixin, itg.Dialog):

        def __init__(self):
            super(IdleDialog, self).__init__()
            # [...]

      
"""

import itg
import os
import playit


class IdlePhotoMixin(object):
    """ IdlePhoto Mix-In 
    
    .. versionadded:: 1.5
    
    """
    
    def onShow(self):
        super(IdlePhotoMixin, self).onShow()
        if (hasattr(self, 'idlePhotoEnabled')):
            itg.runLater(self.showIdlePhotoPreview)            

    def onHide(self):
        super(IdlePhotoMixin, self).onHide()
        if (hasattr(self, 'idlePhotoPlayer')):
            self.idlePhotoPlayer.videoCameraHide()
            self.idlePhotoPlayer.close()
            del self.idlePhotoPlayer

    def enableIdlePhoto(self):
        """ Enable idle photo. This method must be called
        before the dialog is shown in order to see the live
        photo preview.
        
        .. note:: This function checks for the existence of 
                  :class:`itg.WebcamView` to determine whether 
                  a terminal has webcam support. This means it
                  is safe to use this Mixin and to call this 
                  function even on terminals without webcam.
        
        """    
        if (not hasattr(itg, 'WebcamView')):
            return
        self.idlePhotoEnabled = True
        
    def getIdlePhotoRect(self):
        """ Returns tuple of coordinates (x, y, width, height) for
        live photo preview. 
        It is possible to overwrite this method to change the position
        of the live photo preview.
        """
        width  = 294
        height = width * 240 / 320
        return ( (1024-20-width), 600-20-height, width, height)
        
    def showIdlePhotoPreview(self):
        """ Show live photo preview.
        
        :meth:`getIdlePhotoRect` is called to get the coordinates
        for the live preview.
        
        .. note:: This method should not be called. It is called
                  automatically when the dialog is shown or the
                  screensaver is stopped.
        
        """
        if (not self.isTopDialog()):
            return
        if (not hasattr(self, 'idlePhotoEnabled')):
            return
        self.idlePhotoPlayer = playit.PlayIT()
        (x, y, w, h) = self.getIdlePhotoRect()
        self.idlePhotoPlayer.videoCameraWait()
        self.idlePhotoPlayer.videoCameraShow(x, y, w, h)
    
    def hideIdlePhotoPreview(self):
        """ Hide live photo preview without taking a photo."""
        if (hasattr(self, 'idlePhotoPlayer')):
            self.idlePhotoPlayer.videoCameraHide()
            del self.idlePhotoPlayer

    def getIdlePhoto(self):
        """ Stop live preview and take photo. The photo image (JPEG)
        data is returned or **None**, if the terminal has no webcam 
        or :meth:`enableIdlePhoto` was not called before.
        **None** is also returned when the live preview is not active
        (e.g. not shown).
        """
        if (hasattr(self, 'idlePhotoPlayer')):
            idlePhotoFilename = '/tmp/idlePhoto.jpg'
            self.idlePhotoPlayer.videoCameraSnapshot(idlePhotoFilename)
            if (os.path.exists(idlePhotoFilename)):
                idlePhoto = open(idlePhotoFilename, 'r').read()
                os.unlink(idlePhotoFilename)
            else:
                idlePhoto = None
            del self.idlePhotoPlayer
            return idlePhoto
        return None

    def startScreensaver(self):
        self.hideIdlePhotoPreview()
        super(IdlePhotoMixin, self).startScreensaver()

    def stopScreensaver(self):
        super(IdlePhotoMixin, self).stopScreensaver()
        if (hasattr(self, 'idlePhotoEnabled') and not hasattr(self, 'idlePhotoPlayer')):
            itg.runLater(self.showIdlePhotoPreview)              
 

