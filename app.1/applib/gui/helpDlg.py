# -*- coding: utf-8 -*-
#
# Copyright 2011 Grosvenor Technology
#

import itg


class HelpDialog(itg.Dialog):
    
    def __init__(self, helpTitle, htmlHelpFile):
        super(HelpDialog, self).__init__()
        view = itg.TextView(helpTitle, open(htmlHelpFile, 'r').read(), 'text/html')
        view.setButton(_('OK'), itg.ID_OK, self.quit)
        self.addView(view)
