# -*- coding: utf-8 -*-
#
# Copyright 2011 Grosvenor Technology
#


"""   
.. currentmodule:: applib.gui.msg

:func:`passMsg` and :func:`failMsg`
===========================================

A common task for a terminal is to show a message and indicate 
success or failure. The terminal does so by flashing green or 
red LEDs and sounding two short or one long buzz. 

In addition, such messages only need to be on the screen for 
a short time, so it does not block up the terminals for the next
user. Therefore the default timeout for :func:`passMsg` and
:func:`failMsg` is 5 seconds.

Example::

    def clock(self):
        try:
            sendClocking()
        except Exception as e:
            msg.failMsg('Failed to clock (%s)!' % e)
        else:
            msg.passMsg('Clocking accepted!')
        

In applications which need to deal with many users during rush hours,
the time between two users is crucial. To improve speed, it is possible to 
accept new card reads while still showing the pass or fail message from the 
previous user.

Example of accepting card reads in :func:`passMsg` and :func:`failMsg`::

    class IdleDialog(itg.Dialog):
    
        # [...]
        
        def __onCardRead(self, *rdrData):
            while (rdrData != None):
                (valid, reader, decoder, data) = rdrData
                if (valid):
                    try:
                        self.__sendClocking(data)
                    except Exception as e:
                        rdrData = msg.failMsg('Failed to clock (%s)!' % e, acceptReader=True)
                    else:
                        rdrData = msg.passMsg('Clocking accepted!', acceptReader=True)
                else:
                    rdrData = msg.failMsg(_('Invalid card!'), acceptReader=True)


"""

import itg
import led
import os
import playit

_defaultPassTimeout = 5
_defaultFailTimeout = 5

def setDefaultPassTimeout(timeout):
    """ Set default timeout in seconds for pass messages (:func:`passMsg`)."""
    global _defaultPassTimeout
    _defaultPassTimeout = timeout

def passMsg(text, timeout=None, acceptReader=False, soundFile=None, useMarkup=False):
    """ Show message *text* for *timeout* seconds. If *acceptReader*
    is **True** card reads are accepted and returned (see example above).
    
    While showing the message, all green LEDs are on for one second and 
    the buzzer is used to indicate success.
    
    *soundFile* is a **String** containing the filename of a WAV sound file.
    If not **None** it is played instead of using the buzzer.
    
    *useMarkup* is a **Boolean**. If set to True, the *text* parameter may use Pango Markup
    
    This function returns when the OK button is pressed, a card read happens
    (and *acceptReader* is **True**) or the timeout occurs.
    
    .. versionchanged:: 2.0
        Obsolete *parent* parameter removed
        
    .. versionchanged:: 2.4
        Optional soundFile parameter added.
        
    .. versionchanged:: 3.0
        Optional useMarkup parameter added.
        
    """
    led.on(led.LED_ALL | led.LED_STATUS, led.GREEN, 1*1000)
    if (soundFile != None and os.path.exists(soundFile)):
        p = playit.PlayIT()
        p.play(soundFile)
    else:
        itg.successSound()
    if (timeout == None):
        timeout = _defaultPassTimeout
    dlg = _Dialog(text, timeout, acceptReader, useMarkup)
    dlg.run()
    led.off(led.LED_ALL)
    return dlg.getReaderData()    

def setDefaultFailTimeout(timeout):
    """ Set default timeout in seconds for fail messages (:func:`failMsg`)."""
    global _defaultFailTimeout
    _defaultFailTimeout = timeout
    
def failMsg(text, timeout=None, acceptReader=False, soundFile=None, useMarkup=False):
    """ Show message *text* for *timeout* seconds. If *acceptReader*
    is **True** card reads are accepted and returned (see example above).
    
    While showing the message, all red LEDs are on for five seconds and 
    the buzzer is used to indicate a failure.
    
    *soundFile* is a **String** containing the filename of a WAV sound file.
    If not **None** it is played instead of using the buzzer.
    
    *useMarkup* is a **Boolean**. If set to True, the *text* parameter may use Pango Markup
    
    This function returns when the OK button is pressed, a card read happens
    (and *acceptReader* is **True**) or the timeout occurs.
    
    .. versionchanged:: 2.0
        Obsolete *parent* parameter removed
        
    .. versionchanged:: 2.4
        Optional soundFile parameter added.
        
    .. versionchanged:: 3.0
        Optional useMarkup parameter added.
        
    """
    led.on(led.LED_ALL | led.LED_STATUS, led.RED, 5*1000)
    if (soundFile != None and os.path.exists(soundFile)):
        p = playit.PlayIT()
        p.play(soundFile)
    else:
        itg.failureSound()
    if (timeout == None):
        timeout = _defaultFailTimeout
    dlg = _Dialog(text, timeout, acceptReader, useMarkup)
    dlg.run()
    led.off(led.LED_ALL)
    return dlg.getReaderData()
        

class _Dialog(itg.Dialog):

    def __init__(self, msg, timeout=5, acceptReader=False, useMarkup=False):
        super(_Dialog, self).__init__()
        self.__readerData = None
        self.__timeout = timeout
        view = itg.MsgBoxView()
        
        # See if Pango Markup required
        if (useMarkup):
            view.setMarkup(msg)
        else:
            view.setText(msg)
            
        view.setButton(0, _('OK (%s)') % timeout, itg.ID_OK, self.quit)
        self.addView(view)
        self.setTimeout(1)
        if (acceptReader):
            self.setReaderCb(self.__onCardRead)

    def onTimeout(self):
        self.__timeout -= 1
        self.getView().setButton(0, _('OK (%s)') % self.__timeout, itg.ID_OK, self.quit)
        if (self.__timeout <= 0):
            self.quit(itg.ID_TIMEOUT)

    def __onCardRead(self, valid, reader, decoder, data):
        self.__readerData = (valid, reader, decoder, data)
        self.quit(itg.ID_OK)

    def getReaderData(self):
        return self.__readerData


