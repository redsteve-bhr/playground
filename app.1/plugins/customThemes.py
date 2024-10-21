# -*- coding: utf-8 -*-
#
# Copyright 2016 Grosvenor Technology

# CJS 2017-01-16 - FR88 - Customisable Themes

import os
import glob
import shutil
import zipfile

import cfg
import itg
import log
from applib.db.tblSettings import SettingsSection, ListSetting, getAppSetting
from applib.gui import themes
from engine import fileHandler

def getSettings():
    sectionName = 'Theme'
    sectionComment = 'These are the settings for applying a theme to the terminal'
    themeSection = SettingsSection(sectionName, sectionComment)
    s = ListSetting(themeSection,
            name     = 'theme_name',
            label    = 'Theme Name',
            data     = 'default',
            comment  = ('Select the theme to apply' ))
    s.addListOption('default', 'default')
    s.addListOption('appdefault', 'application')
    s.addListOption('custom', 'custom')

    return [themeSection, ]

class ThemeFileHandler(object):
    def fileImport(self, name, data, restartReqManager, isDefaultData=False):
        path='/mnt/user/db/themes/'

        # Ignore theme files on IT11 and IT31, as they don't support theming
        if itg.isIT11() or  itg.isIT31():
            if os.path.exists(path):
                shutil.rmtree(path)
            return
        
        # Extract the theme name from the filename
        (filepath, _) = os.path.splitext(name)
        themeName = os.path.basename(filepath)
        themeName = themeName.split('_')[1]

        # Save the source ZIP file (passed via the data parameter)
        source = '/tmp/theme.zip'
        f = open(source, 'w')
        f.write(data)
        f.close()

        # Delete any existing theme (because ZipFile.extractall() will refuse to 
        # overwrite existing files), but take a back-up of it
        themePath = path + os.path.basename(themeName)
        backupPath = themePath + '.bak'
        if os.path.exists(themePath):
            shutil.copytree(themePath, backupPath)        
            shutil.rmtree(themePath)
        
        # Extract the new theme files
        zipSource = zipfile.ZipFile(source)
        zipSource.extractall(path)

        # Clean up        
        os.remove(source)
        if os.path.exists(backupPath):
            shutil.rmtree(backupPath)

        # If this was the currently-active theme, force a restart to pick up
        # any changes 
        curTheme = cfg.get(cfg.CFG_LCD_THEME)
        log.info("%s : %s" % (curTheme, themePath))
        if curTheme == themePath:       
            themes.setupTheme(themePath)
            restartReqManager.requestRestart()

    def getHelp(self):
        return """
        The ThemeFileHandler allows the application to support a custom theme, which 
        the end-user can update by supplying a theme_custom.zip file via Custom
        Exchange or Assist-IT. This ZIP file is expected to contain a 'custom' folder
        which in turn must contain a gtkrc.it51 configuration file, along with folders
        of any icons and images required. The icon and image folders must themselves
        contain subfolders with at least a 'default' subfolder, and optionally 
        subfolders for terminal types (e.g. 'it5100', 'it7100').
        
        Example layout:
        
            custom
                |
                +-- gtkrc.it51
                |
                +-- icons
                |     |
                |     +-- default
                |     |
                |     +-- it5100
                |
                +-- images
                      |
                      +-- default
                      |
                      +-- it5100
        
        The contents of the supplied ZIP file will completely replace the existing
        custom theme.
        """

def installDefaultCustomTheme():
    """If there is no custom theme currently installed this function creates one by
    copying from either the application default theme (if any) or the system default
    theme (which always exists)."""
    themeTarget = '/mnt/user/db/themes/custom'
    if not os.path.exists(themeTarget):
        themeSource = '/mnt/user/app/themes/appdefault'
        if not os.path.exists(themeSource):
            themeSource = '/usr/share/themeit/default'
        shutil.copytree(themeSource, themeTarget)
        
def updateTheme():
    """ Make sure the current theme is up-to-date. If a new version of 
    the application is installed with new icons or images for the active
    theme, these are copied to the current installed theme directory 
    (/tmp/theme/)
    """
    # Remove theme files on IT11 and IT31, as they don't support theming
    if itg.isIT11() or  itg.isIT31():
        path='/tmp/theme/'
        if os.path.exists(path):
            shutil.rmtree(path)
        path='/mnt/user/db/themes/'
        if os.path.exists(path):
            shutil.rmtree(path)
        path='/mnt/user/app/themes/'
        if os.path.exists(path):
            shutil.rmtree(path)
        return
        
    # Get the current theme name
    if not os.path.exists('/tmp/theme/'):
        # No theme installed, don't bother to go on
        return

    theme = getAppSetting('theme_name')
        
    # Ignore the default theme
    if (theme == 'default'):
        return
    
    # Check for a folder matching the current theme (this should exist -- if it
    # doesn't we'll just ignore it, but will log a warning)
    theme_source = '/mnt/user/db/themes/' + theme
    if not os.path.exists(theme_source):
        theme_source = '/mnt/user/app/themes/' + theme
        if not os.path.exists(theme_source):
            return
    
    # Scan the theme folders and compare the contents with the active theme 
    # -- if any files are missing or have changed, copy them over
    folders = ['icons/default', 'images']
    for folder in folders:
        sourceFolder = os.path.join(theme_source, folder)
        targetFolder = os.path.join('/tmp/theme/', folder)
        sourceFiles = [os.path.basename(f) for f in glob.glob(os.path.join(sourceFolder, "*.png"))]
        targetFiles = [os.path.basename(f) for f in glob.glob(os.path.join(targetFolder, "*.png"))]
        for filename in sourceFiles:
            mustCopy = False
            if filename in targetFiles:
                # Do the files seem to be different?
                if os.path.getsize(os.path.join(sourceFolder, filename)) != os.path.getsize(os.path.join(targetFolder, filename)):
                    mustCopy = True
            else:
                mustCopy = True
                
            if mustCopy:
                sourceFile = os.path.join(sourceFolder, filename)
                targetFile = os.path.join(targetFolder, filename)
                shutil.copy(sourceFile, targetFile)
                
def loadPlugin():
    fileHandler.register('^theme_.*\.zip$', ThemeFileHandler(), 'Themes')