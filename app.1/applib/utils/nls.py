# -*- coding: utf-8 -*-
#
# Copyright 2011 Grosvenor Technology
#
"""
:mod:`nls` --- Native Language Support Helpers
==============================================

This module contains functions and classes to easily
switch language and locale.

    .. versionadded:: 1.2
        
"""

from applib.gui import setupLTR_RTL
import gettext
import locale
import log
import os

_languageStack = []
_localeStack = []

def getCurrentLanguage():
    for l in reversed(_languageStack):
        if (l):
            return l
    return os.getenv('LANGUAGE')

def getCurrentLocale():
    if (_localeStack):
        return _localeStack[-1]
    return None


class Language(object):
    """ :class:`Language` can be used to change language or locale for a context.
    
    Example::
    
        with nls.Language('en'):
            log.info(_('One Two Three')) # logs "One Two Three"
        
        with nls.Language('de'):
            log.info(_('One Two Three')) # logs German translation of "One Two Three"
        
    With proper translation, the example above would log 'one Two Three' and 'Eins Zwei Drei'.
    The same would happen executing it in a nested way::
    
        with nls.Language('en'):
            log.info(_('One Two Three')) # logs "One Two Three"
            with nls.Language('de'):
                log.info(_('One Two Three')) # logs German translation of "One Two Three"
            log.info(_('One Two Three')) # logs "One Two Three" again                
        
    This is especially useful when switching language to run dialogs for different users::
    
        # ...
        
        def onButtonPressEnglish(self, btnID):
            with nls.Language('en'):
                self.runDialog(SomeDialog())
    
        def onButtonPressGerman(self, btnID):
            with nls.Language('de'):
                self.runDialog(SomeDialog())
    
    
    Or in fact automatically switch language for known users::

        def onCardRead(self,  valid, reader, decoder, data):
            if (not valid):
                msg.failMsg(_('Got invalid card read!'))
            else:
                user = getUserFromCardRead(data)
                with nls.Language(user.getLanguage()):
                    self.runDialog(SomeDialog())
    
    
    
    """
    
    def __init__(self, language, locale=None):
        self.__language = language
        self.__locale = locale
        
    def __enterLanguage(self):
        _languageStack.append(self.__language)
        if (self.__language):
            log.dbg('Switching language to %s' % self.__language)
            lang = gettext.translation('app', 'languages', [self.__language])
            lang.install()
        setupLTR_RTL()
    
    def __getNewLanguage(self):
        if (_languageStack):
            for l in reversed(_languageStack):
                if (l):
                    return l
        return None
        
    def __exitLanguage(self):
        # remove current language from stack
        if (_languageStack):
            _languageStack.pop()
        # restore old language if on stack
        newLang = self.__getNewLanguage()
        if (newLang):
            log.dbg('Switching back to language %s' % newLang)
            lang = gettext.translation('app', 'languages', [newLang])
            lang.install()
        else: # restore system language
            log.dbg('Switching back to system language')
            gettext.install('app', 'languages')
        setupLTR_RTL()            

    def __enterLocale(self):
        _localeStack.append(self.__locale)
        if (self.__locale):
            log.dbg('Switching locale to %s' % self.__locale)
            locale.setlocale(locale.LC_ALL, self.__locale)
            
    def __exitLocale(self):
        # remove current locale from stack
        if (_localeStack):
            _localeStack.pop()
        # restore old locale if on stack
        if (_localeStack):
            newLocale = _localeStack[-1]
            if (newLocale):
                log.dbg('Switching back to locale %s' % newLocale)
                locale.setlocale(locale.LC_ALL, newLocale)
        else:
            # restore system locale
            log.dbg('Switching back to system locale')
            locale.setlocale(locale.LC_ALL, '')
        
    def __enter__(self):
        try:
            self.__enterLanguage()
        except Exception as e:
            log.warn('Could not install language %s (%s)' % (self.__language, e))

        try:
            self.__enterLocale()
        except Exception as e:
            log.warn('Could not install locale %s (%s)' % (self.__locale, e))
        
        
    def __exit__(self, exc_type, exc_value, traceback):
        try:
            self.__exitLanguage()
        except Exception as e:
            log.warn('Could not install default language (%s)' % e)

        try:
            self.__exitLocale()
        except Exception as e:
            log.warn('Could not install default locale (%s)' % e)

            