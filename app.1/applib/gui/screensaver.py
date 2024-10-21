# -*- coding: utf-8 -*-
#
# Copyright 2010 Grosvenor Technology
#

"""
:mod:`screensaver` -- Screensaver Mix-In
========================================

The :class:`ScreensaverMixin` class is an easy to use Mix-In to add 
screensaver functionality to a dialog. The Mix-In implements the 
:meth:`itg.Dialog.onTimeout` method to start after a period of inactivity.

The screensaver stops itself when the user touches the screen. On other events
(e.g. card reads) the screensaver needs to be stopped manually by calling
:meth:`ScreensaverMixin.stopScreensaver`.

Example::

    class Dialog(screensaver.ScreensaverMixin, itg.Dialog):
    
        def __init__(self):
            super(Dialog, self).__init__()
            view = itg.IdleMenuView()
            # [...]
            self.addView(view)
            self.enableScreensaver(60, 30, 'screensaver/*')

In the example above, the screensaver will start after 60 seconds
of inactivity and show one image for 30 seconds before showing the next.
It is using all files in the "screensaver" directory.

.. note::
    Calling :meth:`ScreensaverMixin.enableScreensaver` sets up the 
    screensaver. The method calls :meth:`itg.Dialog.setTimeout` to 
    set the timeout of the dialog to start the screensaver. This means
    that other calls to :meth:`itg.Dialog.setTimeout` change the timing
    or might even disable the screensaver (e.g. when :meth:`itg.Dialog.disableTimeout`
    is called). 
    
Example of stopping the screen on card reads::

    # [...]
    
    def __onCardRead(self, valid, reader, decoder, data):
        self.stopScreensaver()

.. important::
    It is safe to use this class even on terminals not supporting :class:`itg.ScreensaverView`. The timeout
    is still set, but :meth:`ScreensaverMixin.startScreensaver` just returns if :class:`itg.ScreensaverView`
    is not available.

"""

import itg
import glob
import threading
import os
import log
from applib.utils import mediaDownload


class ScreensaverMixin(object):
    """ Screensaver Mix-In"""
    
    def enableScreensaver(self, timeout, timePerImage, files=None):
        """ Set up screensaver. *timeout* is used to set the timeout
        of the dialog via :meth:`itg.Dialog.setTimeout` which is
        used to trigger the start of the screensaver. *timePerImage*
        is the time one image is shown in seconds. *files* is an
        expression which may contain shell-style wildcards. It is used
        to select the images used in the screensaver and passed internally
        to `glob <http://docs.python.org/library/glob.html>`_ to get a 
        list of files (e.g. "/path/images/*"). If *files* is **None** 
        images from the media "screensaver" are used (see module 
        :mod:`~applib.utils.mediaDownload`). 

        The screensaver will play a video, if *files* is a filename of an 
        MP4 file or the *glob* expression results in exactly one MP4 file.
        
        .. versionchanged:: 2.4
            MP4 video files detected.

        .. seealso::
            :mod:`applib.utils.mediaDownload`
            
        """
        if (files == None):
            self.__files = mediaDownload.getFilename('screensaver')
            if (not self.__files.endswith('.mp4')):
                self.__files += '/*'
        else:
            self.__files = files
        self.__timePerImage = timePerImage
        self.setTimeout(timeout)
        self.screensaverEnabled = True
    
    def _getImagesOrVideo(self):
        if (self.__files.endswith('.mp4') and os.path.exists(self.__files)):
            return ([], self.__files)
        files = glob.glob(self.__files)
        if (len(files)==1 and files[0].endswith('.mp4')):
            return ([], files[0])
        return (files, None)

        
    def startScreensaver(self):
        """ Start showing screensaver. This method is automatically called when
        the dialog times out, so it is normally not needed to be called.
        
        .. note::
            This method creates the :class:`itg.ScreensaverView` view and shows it,
            when the screensaver is stopped, this view is hidden. This is important 
            to note because no new dialog is created, which means that dialog based
            events like card reads are still handled by the dialog.
        
        """
        if (hasattr(self, 'screensaverView')):
            return # screensaver already running
        (images, video) = self._getImagesOrVideo()
        if (video):
            self.screensaverView = itg.FullScreenImageView('media/images/playvideo.png') 
            self.screensaverView.setActionCb(self.stopScreensaver)
            self.screensaverView.show()
            self.videoThread = _VideoPlayThread(video)
            self.videoThread.start()
        elif (images):
            self.screensaverView = itg.ScreensaverView(images, self.__timePerImage)
            self.screensaverView.setActionCb(self.stopScreensaver)
            self.screensaverView.show()

    def stopScreensaver(self):
        """ Stop showing screensaver. The screensaver stops automatically when the 
        user touches the screen. Call this method to stop at manually, e.g. on card 
        reader events.
        
        .. versionchanged:: 1.8
            Restarts inactivity timer, so screensaver will not become active before the configured *timeout*.
        
        """
        itg.restartTimeout()        
        if (hasattr(self, 'videoThread')):
            self.videoThread.stop()
            del self.videoThread
        if (hasattr(self, 'screensaverView')):
            self.screensaverView.hide()
            self.screensaverView.destroy()
            del self.screensaverView
    
    def hasImagesToShow(self):
        """ Returns **True** if there are images available for the screensaver.
        
        .. versionadded:: 1.2        
        """
        return any(self._getImagesOrVideo())
    
    def onTimeout(self):
        if (hasattr(self, 'screensaverEnabled') and self.screensaverEnabled):
            if (hasattr(itg, 'ScreensaverView') and self.hasImagesToShow()):
                self.startScreensaver()
        else:
            # Emulate 'normal' behaviour on timeout if screensaver was not enabed
            super(ScreensaverMixin, self).onTimeout()
 
 
_videoSupervisorStartedAlready = False

class _VideoPlayThread(threading.Thread):
    
    def __init__(self, fileName):
        super(_VideoPlayThread, self).__init__()
        self.__videoFile = fileName
        self.__running = True
        self.__pid = os.getpid() # get PID of process in foreground!
        
    def run(self):
        global _videoSupervisorStartedAlready
        if (not _videoSupervisorStartedAlready):
            supervisorCmd = ('(('
                             'while test -e /proc/%s; '
                             'do '
                                'sleep 1; '
                             'done; '
                             'killall -s SIGINT gst-launch-0.10 > /dev/null 2>&1 ))&') % self.__pid
            log.dbg('Starting video supervisor process..')
            os.system(supervisorCmd)
            _videoSupervisorStartedAlready = True
        playCmd = ('VSALPHA=1 gst-launch-0.10 filesrc location="%s" '
                   '! "video/quicktime" '
                   '! aiurdemux name=demux demux. '
                   '! queue '
                   '! mfw_vpudecoder '
                   '! mfw_isink demux. '
                   '! queue '
                   '! mad '
                   '! audioconvert '
                   '! "audio/x-raw-int, channels=2" '
                   '! alsasink device=plughw:1 > /var/log/video_screensaver.log 2>&1') % (self.__videoFile)
        while self.__running:
            log.dbg('Playing video...')
            err = os.system(playCmd)
            if (err != 0):
                log.err('Video playback stopped with error code: %s' % err)
                break
            import time
            time.sleep(10)
        self.__running = False
        log.dbg('Video playback stopped')

    def stop(self):
        if (self.__running):
            self.__running = False
            log.dbg('Stopping video playback')
            os.system('killall -s SIGINT gst-launch-0.10')

    