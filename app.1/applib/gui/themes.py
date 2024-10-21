# -*- coding: utf-8 -*-
#
# Copyright 2010 Grosvenor Technology
#

"""
:func:`setupTheme` --- Changing the graphical theme
===================================================

The IT51 terminal supports customisable graphical themes which can 
change the look and feel. Which theme a terminal is using is stored
in NVRAM in 'it_lcd_theme'. The default value is '/usr/share/themeit/default'.

An application can provide a customised theme and change the NVRAM value. However,
it is recommended to use :func:`setupTheme` to change a theme. This function is also
used by :class:`applib.Application` during its initialisation. Class :class:`applib.Application`
is using the application setting 'theme_name' to pass to :func:`setupTheme`. 

Setting for theme support::

        appSettings = (
                # [...]
                {'name'         : 'theme_name',
                 'displayName'  : 'Theme',
                 'allowEdit'    : True,
                 'format'       : 'list',
                 'options'      : 'default|myBlueTheme',
                 'data'         : 'myBlueTheme' },
                 )
"""

import os
import cfg
import log
import updateit

def setupTheme(theme):
    """ Re-configure a theme. *theme* is the theme name which is
    used to create the path of the theme. All application themes
    should be located inside the application in the "themes" directory
    (e.g. 'themes/myBlueTheme'). There is also an optional 'custom' theme
    which is located in /mnt/user/db/themes, which allows end-users to
    provide their own customised theme using the Custom Themes plug-in.
    
    :func:`setupTheme` does a few sanity checks to make sure the theme exists
    and changes 'it_lcd_theme' to point to the new application theme.
    If *theme* is equal to "**default**", the default system theme is used.
    
    :func:`setupTheme` returns **True** if it changed 'it_lcd_theme' and an 
    application restart is required.
    
    .. note::
        This function only needs to be called when the theme is changed while
        running the application. Normally it is sufficient to add the 'theme_name'
        application setting and let :class:`applib.Application` do the work. 
    
    .. important::
        On terminals not supporting customisable themes, this function returns **False**.
        
    .. versionchanged:: 3.0
        Added support for custom themes in /mnt/user/db/themes        
    """
    if (theme == None):
        return False
    if (not os.path.exists('/usr/share/themeit')):
        return False
    curTheme = cfg.get(cfg.CFG_LCD_THEME)
    if (theme == None or theme.strip() == '' or theme == 'default'):
        if (curTheme.startswith('/mnt/')):
            cfg.set(cfg.CFG_LCD_THEME, None)
            return True
    else:
        # Default to the custom themes path
        themePath = os.path.join('/mnt/user/db/themes/', theme)
        themeFile = os.path.join(themePath, 'gtkrc.%s' % updateit.get_type().lower()[0:4])
        # If the theme does not exist there, try the application themes path
        if not os.path.exists(themeFile):
            themePath = os.path.join('/mnt/user/app/themes/', theme)
            themeFile = os.path.join(themePath, 'gtkrc.%s' % updateit.get_type().lower()[0:4])
            # If the theme still can't be found, report this and exit
            if (not os.path.exists(themeFile)):
                log.err('Theme %s does not exist!)' % themePath)
                return False
             
        if (curTheme != themePath):
            cfg.set(cfg.CFG_LCD_THEME, themePath)
            return True
    return False