# -*- coding: utf-8 -*-
#
# Copyright 2011 Grosvenor Technology
#
import itg
from engine import dynButtons


class _GenericGridMenuDialog(dynButtons.DynButtonsMixin, itg.Dialog):
    """
    The grid menu can have up to 8 buttons and supports the following menu properties:
    
    .. tabularcolumns:: |p{0.25\\linewidth}|l|l|p{0.50\\linewidth}|
    
    +--------------------------+---------+----------------------+-----------------------------------------------+
    | Name                     | Type    | Default              | Description                                   |
    +==========================+=========+======================+===============================================+
    | button.alignment         | Text    |                      | Alignment of button text                      |
    +--------------------------+---------+----------------------+-----------------------------------------------+
    | timeout                  | Number  | 60                   | Dialog timeout in seconds                     |
    +--------------------------+---------+----------------------+-----------------------------------------------+        
    
    """

    def __init__(self, menuName, actionParam, employee, languages):
        super(_GenericGridMenuDialog, self).__init__()
        self.loadProperties(menuName)
        btnAlignment = self.getMenuPropertyText('button.alignment')
        view = itg.GridMenuView(btnAlignment) if btnAlignment else itg.GridMenuView()
        self.populateButtons(view, menuName, employee)
        self.addView(view)
        self.setTimeout(self.getMenuPropertyInteger('timeout', self.getDefaultTimeout()))



class _GenericMultiGridMenuDialog(dynButtons.DynButtonsMixin, itg.Dialog):
    """
    The multi grid menu can have up to 7 buttons per page and supports the following menu properties:
    
    .. tabularcolumns:: |p{0.25\\linewidth}|l|l|p{0.50\\linewidth}|
    
    +--------------------------+---------+----------------------+-----------------------------------------------+
    | Name                     | Type    | Default              | Description                                   |
    +==========================+=========+======================+===============================================+
    | button.alignment         | Text    |                      | Alignment of button text                      |
    +--------------------------+---------+----------------------+-----------------------------------------------+
    | timeout                  | Number  | 60                   | Dialog timeout in seconds                     |
    +--------------------------+---------+----------------------+-----------------------------------------------+        
    
    """

    def __init__(self, menuName, actionParam, employee, languages):
        super(_GenericMultiGridMenuDialog, self).__init__()
        self.loadProperties(menuName)
        btnAlignment = self.getMenuPropertyText('button.alignment')
        view = itg.MultiGridMenuView(btnAlignment) if btnAlignment else itg.MultiGridMenuView()
        view.setBackCb(self.back)
        self.populateButtons(view, menuName, employee, 7)
        self.addView(view)
        self.setTimeout(self.getMenuPropertyInteger('timeout', self.getDefaultTimeout()))


class _GenericIconMenuDialog(dynButtons.DynButtonsMixin, itg.Dialog):
    """
    The icon grid menu can have a configurable number of icons, organised by rows and columns and 
    supports the following menu properties:
    
    .. tabularcolumns:: |p{0.25\\linewidth}|l|l|p{0.50\\linewidth}|
    
    +--------------------------+---------+----------------------+-----------------------------------------------+
    | Name                     | Type    | Default              | Description                                   |
    +==========================+=========+======================+===============================================+
    | timeout                  | Number  | 60                   | Dialog timeout in seconds                     |
    +--------------------------+---------+----------------------+-----------------------------------------------+
    | rows                     | Number  | 3                    | Number of icon rows                           |
    +--------------------------+---------+----------------------+-----------------------------------------------+        
    | columns                  | Number  | 3                    | Number of icon columns                        |
    +--------------------------+---------+----------------------+-----------------------------------------------+        
    
    """

    def __init__(self, menuName, actionParam, employee, languages):
        super(_GenericIconMenuDialog, self).__init__()
        self.loadProperties(menuName)
        rows = self.getMenuPropertyInteger('rows', 3)
        cols = self.getMenuPropertyInteger('columns', 3)
        view = itg.IconGridMenuView(rows, cols)
        self.populateButtons(view, menuName, employee)        
        self.addView(view)
        self.setTimeout(self.getMenuPropertyInteger('timeout', self.getDefaultTimeout()))




def loadPlugin():
    dynButtons.registerMenu('menu.grid.',       _GenericGridMenuDialog,      'Grid Menu',       _GenericGridMenuDialog.__doc__)
    dynButtons.registerMenu('menu.multigrid.',  _GenericMultiGridMenuDialog, 'Multi Grid Menu', _GenericMultiGridMenuDialog.__doc__)
    dynButtons.registerMenu('menu.icon.',       _GenericIconMenuDialog,      'Icon Grid Menu',  _GenericIconMenuDialog.__doc__)

