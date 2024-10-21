# -*- coding: utf-8 -*-
#
# Copyright 2011 Grosvenor Technology
#

import updateit
import log
import itg

_currentDir = None

def setupLTR_RTL():
    try:
        global _currentDir

        if (hasattr(itg, 'enableRTL')):
            if (_('default:LTR') == 'default:RTL'):
                if (_currentDir != 'rtl'):
                    log.dbg('Switching to RTL')
                    itg.enableRTL(True)
                    _currentDir = 'rtl'
            else:
                if (_currentDir != 'ltr'):
                    log.dbg('Switching to LTR')
                    itg.enableRTL(False)
                    _currentDir = 'ltr'

        elif (updateit.get_type() == 'IT5100'):
            import gtk #@UnresolvedImport
            if (_('default:LTR') == 'default:RTL'):
                if (_currentDir != 'rtl'):
                    log.dbg('Switching to RTL')
                    gtk.widget_set_default_direction(gtk.TEXT_DIR_RTL) #@UndefinedVariable
                    _currentDir = 'rtl'
            else:
                if (_currentDir != 'ltr'):
                    log.dbg('Switching to LTR')
                    gtk.widget_set_default_direction(gtk.TEXT_DIR_LTR) #@UndefinedVariable
                    _currentDir = 'ltr'
    except Exception as e:
        log.err('Error in setupLTR_RTL: %s' % e)