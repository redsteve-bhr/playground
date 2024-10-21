# -*- coding: utf-8 -*-
#
# Copyright 2011 Grosvenor Technology
#

import itg
from applib.utils.healthMonitor import getAppHealthMonitor

class HealthMonitorDialog(itg.Dialog):
    """ Create :class:`HealthMonitorDialog`. This dialog shows
    the current health state of all monitored objects.
    
    Example::
        
        from applib.gui.health import HealthMonitorDialog
        dlg = HealthMonitorDialog()
        dlg.run()
    
    The dialog uses :func:`applib.utils.getAppHealthMonitor` to get the
    application health monitor.
    """
    
    def __init__(self):
        super(HealthMonitorDialog, self).__init__()
        view = itg.MenuView(_('Health Status'))
        view.setBackButton(_('Back'), cb=self.back)

        for (name, healthy, details) in getAppHealthMonitor().getHealthStatus():
            view.appendRow(name,
                           value=_('Good') if healthy else _('Bad'),
                           data=(name, details),
                           hasSubItems=True if details else False, 
                           cb=self.__onSelect if details else None)
        self.addView(view)    
        
    def __onSelect(self, pos, row):
        self.runDialog(_DetailsDialog(*row['data']))


class _DetailsDialog(itg.Dialog):
    
    def __init__(self, title, details):
        super(_DetailsDialog, self).__init__()
        view = itg.MenuView('%s' % title)
        view.setBackButton(_('Back'), cb=self.back)
        view.setCancelButton(_('Cancel'), cb=self.cancel)
        for (name, value) in details:
            view.appendRow(name, value, cb=self.__onSelect)
        self.addView(view)    
        
    def __onSelect(self, pos, row):
        itg.msgbox(itg.MB_OK, '"%s" is "%s"' % (row['label'], row['value']))

