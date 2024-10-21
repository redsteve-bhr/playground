# -*- coding: utf-8 -*-
#
# Copyright 2013 Grosvenor Technology
#
import xml.etree.cElementTree
import glob
import re
import log
import os
import updateit
import urllib2
import appit
import cfg
import time
import codecs
import base64
from applib.db import tblSettings, tblLastTableSync
from engine.actionRequestParams import ActionRequestParams

_fileHandlers = {}

def clear():
    _fileHandlers.clear()


# Example file handler:
# 
# class FHandler():
#     
#     def getExportName(self):
#         pass
#     
#     def fileImport(self, name, data, restartReqManager, isDefaultData=False):
#         pass
#     
#     def fileExport(self, name):
#         pass
# 
#     def fileDelete(self, name):
#         pass
# 
#     def projectImport(self, name, xmlTag, restartReqManager):
#         pass
# 
#     def projectExport(self, name):
#         pass
#     

def register(nameFilter, handler, name=None):
    caps = []
    if (hasattr(handler, 'fileImport')):
        caps.append('import')
    if (hasattr(handler, 'fileExport')):
        caps.append('export')
    if (hasattr(handler, 'fileDelete')):
        caps.append('delete')
    if (hasattr(handler, 'projectImport') or hasattr(handler, 'projectExport') or hasattr(handler, 'projectImportText')):
        caps.append('project')
    if (len(caps) == 0):
        raise Exception('File handler %s has no import or export methods' % handler.__class__.__name__)
    if (hasattr(handler, 'getExportName')):
        log.dbg('New file handler %s for %s (%s)' % (handler.__class__.__name__, handler.getExportName(), ','.join(caps)))
    else:
        log.dbg('New file handler %s (%s)' % (handler.__class__.__name__, ','.join(caps)))
    helpTxt = handler.getHelp() if hasattr(handler, 'getHelp') else None
    _fileHandlers[nameFilter] = (handler, name, helpTxt)

def unregister(nameFilter):
    del _fileHandlers[nameFilter]

def getFileHandlerForFile(filename):
    for nameFilter in _fileHandlers.keys():
        if (re.search(nameFilter, filename)):
            return _fileHandlers[nameFilter][0]
    return None

def getAll():
    return map(lambda t: t[0], _fileHandlers.values())
    
def getAllFileHandlersForFile(filename):
    handler = []
    for nameFilter in _fileHandlers.keys():
        if (re.search(nameFilter, filename)):
            handler.append(_fileHandlers[nameFilter][0])
    return handler

def applyDefaults(path='defaultImports'):
    restartReqManager = RestartRequestManager()
    try:
        if (not os.path.isdir(path)):
            return
        files = os.listdir(path)
        for fileName in files:
            if (os.path.isdir(fileName)):
                continue
            log.dbg('Applying defaults from %s' % fileName)
            data = open(os.path.join(path, fileName)).read()
            handled = False
            for handler in getAllFileHandlersForFile(fileName):
                if not hasattr(handler, 'fileImport'):
                    continue
                try:
                    handler.fileImport(fileName, data, restartReqManager, True)
                    handled = True
                except Exception as e:
                    log.err('Error applying default data (%s:%s)' % (fileName, e))
            if (not handled):
                log.err('No file handler for %s' % fileName)
    except Exception as e:
        log.err('Error applying defaults (%s)' % (e,))

def loadStartupProject():
    try:
        projPath = '/mnt/user/db/startup-project.xml'
        if (os.path.exists(projPath)):
            restartReqManager = RestartRequestManager()
            ph = ProjectHandler()
            ph.fileImport('startup-project', open(projPath, 'r').read(), restartReqManager)
            os.unlink(projPath)
    except Exception as e:
        log.warn('Failed to import startup project: %s' % e)

def registerStandardHandlers():
    register('^itcfg.*\.xml$', CfgHandler(), 'Settings')
    register('^itcfg.*\.txt$', CfgTxtHandler(), 'Settings summary')
    register('^IT.*fw\.info$', FwHandler(), 'Firmware')
    register('^.*\.app$',      AppHandler(), 'Application')
    register('^project\.xml$', ProjectHandler(), 'Project')
    register('^reboot\.xml$',  RebootFileHandler(), 'Reboot Terminal')
    register('^apprestart\.xml$', AppRestartFileHandler(), 'Application Restart')
    register('^resendClockings\.xml$', ResendClockingsFileHandler(), 'Re-send Clockings')
    register('^clearClockings\.xml$', ClearClockingsFileHandler(), 'Re-send Clockings')
    register('^(twn|TWN)4_.*\.bix$', ElatecReaderFileHandler(), 'Elatec Reader')
    register('^app\.info$',    AppInfoHandler(), 'AppInfo')

    # Handler for Attestation details
    helpTxt = """
Handler for file containing Attestation Text and Reasons"""
    register('^attestation\.xml$', PersistentFileHandler('attestation.xml', restart=False, helpText=helpTxt), 'Attestation')
    
    # Handler for certificates file
    helpTxt = """
Handler for file containing certificates of trusted Certificate Authorities.
These are those CAs that are not in the certificate store for the firmware."""
    register('^(ca-certificates.pem|trusted_cacerts.crt)$', PersistentProjectFileHandler('ca-certificates.pem', restart=True, helpText=helpTxt), 'Certificates')

class RestartRequestManager(object):
    
    def __init__(self):
        self.__restartRequested = False
        self.__rebootRequested  = False
    
    def requestRestart(self):
        self.__restartRequested = True
    
    def requestReboot(self):
        self.__rebootRequested = True
    
    def isRestartRequested(self):
        return self.__restartRequested

    def isRebootRequested(self):
        return self.__rebootRequested


def _removeNamespace(doc, ns=None):
    """Remove namespace in the passed document in place."""
    for elem in doc.getiterator():
        if elem.tag.startswith('{'):
            uri, tagName = elem.tag[1:].split('}')
            if (ns == None):
                elem.tag = tagName
            elif (ns == uri):
                elem.tag = tagName


#
# Generic file handler
#
#




_sysCfgIgnores = ( 'bootdelay', 'it_quickboot', 'uboot-version', 'hw_tested', 'pcb_revision', 'partno', 'systemid')
_appCfgIgnores = []


class CfgHandler(object):

    def getHelp(self):
        return """
The settings file handler can import and export *itcfg.xml* files,
which contain system and application settings. The file handler
will request a terminal reboot on system setting changes and an
application restart on application setting changes.
 
Simple *itcfg.xml*::
   
  <?xml version="1.0" encoding="utf-8"?>
  <itCfg>
    <sysCfg>
      <cfg name="it_language">en</cfg>
      <cfg name="it_locale">en_GB.UTF-8</cfg>
    </sysCfg>
    <appCfg>
      <cfg name="app_log">dbg</cfg>
      <cfg name="emp_limit_by">table</cfg>
    </appCfg>
  </itCfg>
 
"""

    def getXsd(self):
        return ('itcfg.xsd', """<?xml version="1.0"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns="http://gtl.biz/apps/itcfg" targetNamespace="http://gtl.biz/apps/itcfg" elementFormDefault="qualified">
    <xs:complexType name="cfgEntryType">
        <xs:simpleContent>
            <xs:extension base="xs:normalizedString">
                <xs:attribute name="name" type="xs:string" use="required" />
                <xs:attribute name="terminal" type="xs:string" />
                <xs:attribute name="partno" type="xs:string" />
            </xs:extension>
        </xs:simpleContent>
    </xs:complexType>

    <xs:complexType name="sysCfgType">
        <xs:sequence>
            <xs:element name="cfg" type="cfgEntryType" maxOccurs="unbounded" />
        </xs:sequence>
    </xs:complexType>

    <xs:complexType name="appCfgType">
        <xs:sequence>
            <xs:element name="cfg" type="cfgEntryType" maxOccurs="unbounded" />
        </xs:sequence>
    </xs:complexType>

    <xs:element name="itCfg">
        <xs:complexType>
            <xs:all>
                <xs:element name="sysCfg" type="sysCfgType" minOccurs="0" />
                <xs:element name="appCfg" type="appCfgType" minOccurs="0" />
            </xs:all>
        </xs:complexType>
    </xs:element>
</xs:schema> 
""".replace('        ', ''))

    
    def getExportName(self):
        return 'itcfg.xml'

    def fileImport(self, name, data, restartReqManager, isDefaultData=False):
        if (isDefaultData):
            log.warn('CfgHandler does not support importing default data')
        if (log.debug_enabled):
            f = open('/tmp/%s' % name, 'w')
            f.write(data)
            f.close()
        itcfg = xml.etree.cElementTree.fromstring(data)
        self.projectImport(name, itcfg, restartReqManager)

    def projectImport(self, name, xmlTag, restartReqManager):
        _removeNamespace(xmlTag)
        tType  = updateit.get_type()
        partNo = cfg.get(cfg.CFG_PARTNO)
        settings = tblSettings.getAppSettings()
        nvram    = {}
        restart  = False
        for c in xmlTag.findall('sysCfg/cfg'):
            name  = c.get('name', '').strip()
            if (not name):
                continue
            if (c.get('terminal', tType) != tType):
                continue
            if (c.get('partNo', partNo) != partNo):
                continue            
            value = c.text if (c.text != None) else ''
            if (cfg.get(name) != value):
                log.dbg('System setting change: %s=%s' % (name, value))
                nvram[name] = value
        for c in xmlTag.findall('appCfg/cfg'):
            name  = c.get('name', '').strip()
            value = c.text
            if (not name):
                continue
            if (c.get('terminal', tType) != tType):
                continue
            if (c.get('partNo', partNo) != partNo):
                continue            
            if (value == None):
                value = ''
            try:
                if (settings.getAsString(name) != value):
                    log.dbg('Application setting change: %s=%s' % (name, value))
                    settings.set(name, value, False)
                    restart = True
            except Exception as e:
                log.err('Error updating application setting (%s:%s): %s' % (name, value, e))
        if (nvram):
            log.info('System configuration changed')
            # store NVRAM settings and request reboot
            cfg.setMany(nvram)
            restartReqManager.requestReboot()
        # exit application 
        if (restart):
            log.info('Application configuration changed')
            restartReqManager.requestRestart()            
        if (not nvram and not restart):
            log.info('Configuration unchanged')

    def fileExport(self, name):
        data = self.projectExport(name, True)
        if (log.debug_enabled):
            f = open('/tmp/%s' % name, 'w')
            f.write(data)
            f.close()
        return data
    
    def projectExport(self, name, comments=False):
        defaults = cfg.getAllDefaults()        
        data =  ['<itcfg>', '  <sysCfg>' ]
        # add nvram values
        for entry in cfg.get_all():
            if (entry['name'] in _sysCfgIgnores):
                continue
            dflt = defaults[entry['name']]
            if (dflt['noreset'] != 0):
                continue
            if (comments and dflt['comment'] != None):
                comment = dflt['comment']
                comment = '\n         '.join(comment.splitlines())
                data.append('    <!-- %s [default: "%s"] -->' % (comment, dflt['dflt']))
            xmlLine = '    <cfg name="%s">%s</cfg>' % (entry['name'], entry['value'].decode('iso8859-1'))
            if (dflt['dflt'] == entry['value']):
                if (not comments):
                    continue # do not add default entry
                xmlLine = '    <!-- %s -->' % xmlLine
            data.append(xmlLine)
        data.append('  </sysCfg>')
        data.append('  <appCfg>')
        # add app settings
        settings = tblSettings.getAppSettings()
        for section in settings.selectSectionNames():
            sectionName = section['Section']
            if (comments):
                data.append('')
                data.append('    <!-- %s -->' % sectionName)
                data.append('')            
            for entry in settings.selectBySection(sectionName):
                if (entry['name'] in _appCfgIgnores):
                    continue
                if (comments and entry['Comment']):
                    comment = entry['Comment']
                    comment = '\n         '.join(comment.splitlines())
                    info = 'format: "%s", options: "%s", default: "%s"' % (entry['Format'], entry['Options'], entry['DefaultData'])
                    data.append('    <!-- %s [%s] -->' % (comment, info))
                xmlLine = '    <cfg name="%s">%s</cfg>' % (entry['Name'], entry['Data'])
                if ( entry['DefaultData'] == entry['Data']):
                    if (not comments):
                        continue
                    xmlLine = '    <!-- %s -->' % xmlLine
                data.append(xmlLine)
        data.append('  </appCfg>')
        data.append('</itcfg>')
        return '\n'.join(data)




class CfgTxtHandler(object):

    def getHelp(self):
        return """
The settings summary file handler can export a text summary of all
current system and application settings. It is much easier to read than
the *itcfg.xml* file, but the exported *itcfg.txt* file is for viewing only
and cannot be re-imported.
"""
        
    def getExportName(self):
        return 'itcfg.txt'

    def fileExport(self, name):
        appInfo = appit.AppInfo()
        data =  ['Application                 : %s (%s)' % (appInfo.name(), appInfo.version()),
                 'Firmware                    : %s (%s)' % (updateit.get_version(), updateit.get_build_date()),
                 'SystemID                    : %s' % cfg.get(cfg.CFG_SYSTEM_ID),
                 'PartNo                      : %s' % cfg.get(cfg.CFG_PARTNO).decode('iso8859-1'),
                 'Timestamp                   : %s' % time.strftime('%Y-%m-%dT%H:%M:%S%z'),
                 '',
                 '',
                 'NOTE: This file cannot be imported!',
                 '' ]

        data.append('System Settings')
        data.append('===============')
        data.append('')
        for e in cfg.get_all():
            if (e['name'] in _sysCfgIgnores):
                continue
            data.append('%-28s: %s' % (e['name'], e['value'].decode('iso8859-1')))
        data.append('')
        data.append('')
        data.append('Application Settings')
        data.append('====================')
        data.append('')
        data.append('')
        settings = tblSettings.getAppSettings()
        for section in settings.selectSectionNames():
            sectionName = section['Section']
            data.append(sectionName)
            data.append('-' * len(sectionName))
            data.append('')
            for entry in settings.selectBySection(sectionName):
                if (entry['name'] in _appCfgIgnores):
                    continue
                data.append('%-28s: %s' % (entry['DisplayName'], entry['Data']))
            data.append('')
            data.append('')
        data.append('')
        data.append('')
        if (log.debug_enabled):
            f = open('/tmp/%s' % name, 'w')
            f.write('\r\n'.join(data))
            f.close()                
        return '\r\n'.join(data)


class AppHandler(object):

    def getHelp(self):
        return """The application file handler can import an IT application file and install it."""
        
    def getAutoConfig(self):
        data =  ['<itcfg>',
                 '  <appCfg>' ]
        settings = tblSettings.getAppSettings()
        for entry in settings.selectAll():
            name  = entry['Name']
            value = entry['Data']
            if (value == None):
                log.warn('Application setting %s is None!' % name)
                value = ''
            xmlLine = '    <cfg name="%s">%s</cfg>' % (name, value)
            data.append(xmlLine)
        data.append('  </appCfg>')
        data.append('</itcfg>')
        return '\n'.join(data)

    def fileImport(self, name, data, restartReqManager, isDefaultData=False):
        if (isDefaultData):
            log.warn('AppHandler does not support importing default data')
        # save app
        f = open('/tmp/%s' % name, 'w')
        f.write(data)
        f.close()
        itcfg = self.getAutoConfig()
        # start update
        err = os.system('appit install file:///tmp/%s 2>&1| logger' % name)
        if (err):
            log.err('Error while installing application')
        else:
            # write current config
            try:
                if (not os.path.exists('/mnt/user/db')):
                    log.dbg('Creating itcfg-auto.xml file')
                    os.mkdir('/mnt/user/db')
                    f = open('/mnt/user/db/itcfg-auto.xml', 'w')
                    f.write(itcfg)
                    f.close()
            except Exception as e:
                log.err('Error creating itcfg-auto.xml: %s' % e)
            # restart app on success
            restartReqManager.requestRestart()
           
class AppInfoHandler(object):
    
    def fileImport(self, name, data, restartReqManager, isDefaultData=False):
        if (isDefaultData):
            log.warn('AppInfoHandler does not support import default data')
            return        

        # Save app.info
        f = open('/tmp/%s' % name, 'w')
        f.write(data)
        f.close()
        
        # Parse the file
        lines = data.split('\n')
        version = ""
        url = ""
        for line in lines:
            key, value = line.split('=')
            if key.strip() == "version":
                version = re.sub("'", "", value.strip())
            if key.strip() == "update-url":
                url = re.sub("'", "", value.strip())
        
        if version == "":
            log.warn("No version number found in %s" % name)
            return
            
        if url == "":
            log.warn("No update URL found in %s" % name)
            return
        
        # Get Application info for currently-installed application
        appInfo = appit.AppInfo()
        appVersion = appInfo.version()
        
        if appVersion > version:
            log.warn("Installed application is version %s, cannot downgrade to %s" % (appVersion, version))
        elif appVersion == version:
            log.warn("Version %s is current" % appVersion)
        else:
            handler = AppHandler()
            try:
                # If a proxy-server needs to be navigated through:
                # Use http://www.someproxy.com:3128 for http proxying
                # proxies = {'http': 'http://www.someproxy.com:3128'}
                # filehandle = urllib2.urlopen(proxy_url, proxies=proxies)
                f = urllib2.urlopen(url)
                data = f.read()
            except:
                log.err("HTTP client, urlopen error.")
        
            handler.fileImport(name, data, restartReqManager, isDefaultData)
        
        

class FwHandler(object):

    def getHelp(self):
        return """
The firmware file handler can import a firmware info file and use
it to update the terminal firmware if necessary. The terminal is rebooted, once the 
firmware is updated.
"""

    def fileImport(self, name, data, restartReqManager, isDefaultData=False):
        if (isDefaultData):
            log.warn('CfgHandler does not support importing default data')
        if (name != 'IT-fw.info' and name != '%s-fw.info' % updateit.get_type()[0:4]):
            log.dbg('Got firmware update request for different terminal type. Ignoring it...')
            return
        # save info file in tmp
        f = open('/tmp/%s' % name, 'w')
        f.write(data)
        f.close()
        os.system('updateit -r -i file:///tmp/%s update 2>&1| logger' % name)


class ElatecReaderFileHandler(object):
    
    def getHelp(self):
        return """
The Elatec Reader file handler can import a file to update the Elatec Reader. 
The terminal is rebooted once the handler is installed.
"""

    def fileImport(self, name, data, restartReqManager, isDefaultData=False):
        if (isDefaultData):
            log.warn('ElactecReaderFileHandler does not support importing default data')
            return

        filePath = '/mnt/user/db/elatec'
        if not os.path.exists(filePath):
            os.mkdir(filePath)
        else:
            try:
                # Remove any previous files
                files = glob.glob(os.path.join(filePath, "*.*"))
                for filename in files:
                    os.remove(filename)
            except Exception as e:
                log.warn("Could not delete all existing files from Elatec folder: %s" % str(e))
        filename = os.path.join(filePath, name)

        # Use a generic name for storing in TblLastSync (don't use the filename
        # specified by 'name', because this changes for each new reader file)
        filetype = "elatec-reader"
        
        lastTableSync = tblLastTableSync.TblLastTableSync()
        lastTableSync.open()
        if (os.path.exists(filename)):
            (_, lastMD5) = lastTableSync.getByTableName(filetype)
        else:
            lastMD5 = None
        md5sum = tblLastTableSync.createMD5Sum(data)
        if (md5sum == lastMD5):
            log.dbg('Not applying data for Elatec Reader, no changes.')
            return

        open(filename, 'w').write(data)
        log.dbg('New version of Elatec Reader saved. Restarting application to apply changes.')        
        lastTableSync.setSynched(filetype, md5sum)

        # Update the system setting so that the firmware imports the new file
        cfg.set('it_usb_reader_elatec_bix_file', filename)

        restartReqManager.requestReboot()
            
class PersistentFileHandler(object):
    
    def __init__(self, filename, restart=False, helpText=None, xsdDef=None):
        self._filename = filename
        self._restart  = restart
        self._helpText = helpText
        self._xsdDef = xsdDef
        
    def getHelp(self):
        return self._helpText
    
    def getXsd(self):
        return self._xsdDef

    def getExportName(self):
        return self._filename
        
    def fileImport(self, name, data, restartReqManager, isDefaultData=False):
        if (log.debug_enabled and not isDefaultData):
            f = open('/tmp/%s' % name, 'w')
            f.write(data)
            f.close()
        name = self.getExportName()
        filename = '/mnt/user/db/%s' % name
        lastTableSync = tblLastTableSync.TblLastTableSync()
        lastTableSync.open()
        if (os.path.exists(filename)):
            (lastSync, lastMD5) = lastTableSync.getByTableName(name)
        else:
            (lastSync, lastMD5) = (None, None)
        if (isDefaultData and lastSync != None):
            log.dbg('Not applying defaults for %s (last sync on %s).' % (name, lastSync))
            return
        md5sum = tblLastTableSync.createMD5Sum(data)
        if (md5sum == lastMD5):
            log.dbg('Not applying data for %s, no changes.' % name)
            return
        open(filename, 'w').write(data)
        log.dbg('New version of %s saved.' % name)        
        if (isDefaultData):
            lastTableSync.setMD5(name, md5sum)
        else:
            lastTableSync.setSynched(name, md5sum)
            if (self._restart):
                restartReqManager.requestRestart()
            
    def fileExport(self, name):
        filename = '/mnt/user/db/%s' % self.getExportName()
        if (not os.path.exists(filename)):
            return ''
        xmlData = open(filename, 'r').read()
        if (log.debug_enabled):
            f = open('/tmp/%s' % name, 'w')
            f.write(xmlData)
            f.close()                
        return xmlData        

    def fileDelete(self, name):
        name = self.getExportName()
        filename = '/mnt/user/db/%s' % name
        try:
            os.unlink(filename)
        except Exception as e:
            log.warn('Error deleting %s: %s' % (name, e))



class PersistentProjectFileHandler(PersistentFileHandler):

    def projectImport(self, name, xmlTag, restartReqManager):
        data = xml.etree.cElementTree.tostring(xmlTag, 'utf-8')
        self.fileImport(name, data, restartReqManager, False) 
 
    def projectExport(self, name):
        fData = self.fileExport(name).strip()
        if (fData.startswith(codecs.BOM_UTF8)):
            fData = fData[3:]
        # remove XML version header
        if (fData.startswith('<?')):
            endIdx = fData.index('?>') + 2
            fData = fData[endIdx:].strip(' \t\n\r')
        # remove XML doctype
        if (fData.startswith('<!')):
            endIdx = fData.index('>') + 1
            fData = fData[endIdx:].strip(' \t\n\r')
        return fData


class PersistentProjectTextFileHandler(PersistentFileHandler):

    def projectImportText(self, name, text, restartReqManager):
        self.fileImport(name, text.strip(), restartReqManager, False) 
 
    def projectExport(self, name):
        fData = self.fileExport(name).strip()
        if (fData.startswith(codecs.BOM_UTF8)):
            fData = fData[3:]
        # remove XML version header
        if (fData.startswith('<?')):
            endIdx = fData.index('?>') + 2
            fData = fData[endIdx:].strip(' \t\n\r')
        # remove XML doctype
        if (fData.startswith('<!')):
            endIdx = fData.index('>') + 1
            fData = fData[endIdx:].strip(' \t\n\r')
        return fData


class PersistentBinaryProjectFileHandler(PersistentFileHandler):

    def projectImport(self, name, xmlTag, restartReqManager):
        b64Data = xmlTag.text
        if (b64Data):
            binData = base64.b64decode(b64Data)
            self.fileImport(name, binData, restartReqManager, False) 
        else:
            self.fileDelete(name)
 
    def projectExport(self, name):
        binData = self.fileExport(name)
        if (binData):
            b64Data = base64.b64encode(binData)
            return '<b64data>%s</b64data>' % b64Data
        return None


class CsvExportFileHandler(object):
    
    def __init__(self, filename, dataTable):
        self._filename = filename
        self.dataTbl = dataTable

    def getExportName(self):
        return self._filename
        
    def fileExport(self, name):
        csvData = []
        cols = self.dataTbl.getColumnNames()
        if cols:
            csvData.append(','.join(cols))
            for row in self.dataTbl.selectAll():
                csvData.append(','.join( [str(row[str(colName)]) for colName in cols] ))
            return '\r\n'.join(csvData)        
        return None


   
class ProjectHandler(object):
    
    def getHelp(self):
        return """
The project file handler can import and export a *project.xml*
file. It is an XML file, that simply contains other files and their names
in it. When exporting a *project.xml* file, all file handlers that support
project export and have a default export name will be included.

Basic *project.xml*::

  <?xml version="1.0" encoding="utf-8"?>
  <project>
    <file name="itcfg.xml"> ... </file>
  </project>


The project file above contains only one file, which is an *itcfg.xml* file.

The purpose of the project file is to be able to bundle many files into one, so only
one import is necessary. This is especially useful for initial setup of application, as 
a project file can include an *itcfg.xml* file together with a *buttons.xml* file, for
example.

"""

    def fileImport(self, name, data, restartReqManager, isDefaultData=False):
        if (log.debug_enabled):
            f = open('/tmp/%s' % name, 'w')
            f.write(data)
            f.close()
        root = xml.etree.cElementTree.fromstring(data)
        for f in root:
            if (f.tag == 'file'):
                self.handleFileTag(f, restartReqManager)
    
    def handleFileTag(self, fTag, restartReqManager):
        handled = False
        fName = fTag.get('name', '').strip()
        if (not fName):
            raise Exception('file tag without name attribute')
        if (len(fTag) == 0):
            for handler in getAllFileHandlersForFile(fName):
                if not hasattr(handler, 'projectImportText'):
                    continue
                handler.projectImportText(fName, fTag.text, restartReqManager)
                handled = True
        elif (len(fTag) == 1):
            for handler in getAllFileHandlersForFile(fName):
                if not hasattr(handler, 'projectImport'):
                    continue
                handler.projectImport(fName, fTag.getchildren()[0], restartReqManager)
                handled = True
        else:
            raise Exception('file tag must contain exactly one sub element or text')
        if (not handled):
            log.err('No file handler for project file %s' % fName)

    def getExportName(self):
        return 'project.xml'

    def fileExport(self, name):
        data =  ['<project>' ]
        for handler in getAll():
            if (not hasattr(handler, 'projectExport') or not hasattr(handler, 'getExportName')):
                continue
            fName = handler.getExportName()
            fData = handler.projectExport(fName)
            if (not fData):
                continue
            data.append('<file name="%s">' % fName)
            data.append(fData)
            data.append('</file>')
        data.append('</project>')
        if (log.debug_enabled):
            f = open('/tmp/%s' % name, 'w')
            f.write('\n'.join(data))
            f.close()                
        return '\n'.join(data)

class RebootFileHandler(object):
    
    def getHelp(self):
        return """
The RebootFileHandler imports a reboot file, which is simply taken as a 
request to reboot the terminal. The contents of the file are irrelevant
and ignored.
        """
        
    def fileImport(self, name, data, restartReqManager, isDefaultData=False):
        log.info("Reboot Request received. Rebooting terminal.")
        restartReqManager.requestReboot()
        
class AppRestartFileHandler(object):
    
    def getHelp(self):
        return """
The AppRestartFileHandler imports a restart file, which is simply taken as a 
request to restart the application. The contents of the file are irrelevant
and ignored.
        """
        
    def fileImport(self, name, data, restartReqManager, isDefaultData=False):
        log.info("App Restart Request received. Restarting application.")
        restartReqManager.requestRestart()

class ResendClockingsFileHandler(object):
    
    def getHelp(self):
        return """
The ResendClockingsFileHandler imports a resend file, which is taken as a 
request to re-send clockings. It does this by simply clearing the 'sent' flag
on the clocking entries in the Transaction table, which will force the 
clockings to be automatically re-sent by the Transaction Upload system.

The data can be empty, in which case all clockings will be re-sent, or it can
contain an ActionRequestParams instance containing the start date for re-sending 
the clockings. Transactions including and after that date will be re-sent. 

If set, startDate is expected to be in the format %Y-%m-%d %H:%M:%S
        """
        
    def fileImport(self, name, data, restartReqManager, isDefaultData=False):
        from webClient.transaction import getAppTransactions
        startDate = ''
        if (data is not None) and (data is ActionRequestParams) and ('startDate' in data):
            startDate = re.sub('T', ' ', data['startDate'])[:19]
            
        trans = getAppTransactions()
        trans.markAsUnsentAfter(startDate)
    
class ClearClockingsFileHandler(object):
    
    def getHelp(self):
        return """
The ClearClockingsFileHandler imports a clearClockings file, which is taken as 
a request to clear any unsent clockings. It does this by simply setting the 
'sent' flag on the clocking entries in the Transaction table.

The data can be empty, in which case all clockings will be cleared, or it can
contain an ActionRequestParams instance containing the end date for clearing 
the clockings. Transactions up to and including that date will be marked as
sent. 

If set, endDate is expected to be in the format %Y-%m-%d %H:%M:%S
        """
        
    def fileImport(self, name, data, restartReqManager, isDefaultData=False):
        from webClient.transaction import getAppTransactions
        endDate = ''
        if (data is not None) and (data is ActionRequestParams) and ('endDate' in data):
            endDate = re.sub('T', ' ', data['endDate'])[:19]
            
        trans = getAppTransactions()
        trans.markAsSentToDate(endDate)
    
def getHelp(appInfo):
    registerStandardHandlers()
    helpText = []
    numFileHandlers = 0
    for (fileNameRe, (fileHandler, fileHandlerName, fileHandlerHelp)) in sorted(_fileHandlers.iteritems(), key=lambda (k,v): v[1]):
        if (not fileHandlerName):
            log.warn('File handler %s for %s has no name' % (fileHandler.__class__.__name__, fileNameRe))
            continue
        numFileHandlers += 1
        fileHandlerTitle = '%s file handler' % fileHandlerName
        exportName = fileHandler.getExportName() if hasattr(fileHandler, 'getExportName') else 'none'
        caps = []
        for (capName, methName) in ( ('import', 'fileImport'), 
                                     ('export', 'fileExport'), 
                                     ('project import', 'projectImport'), 
                                     ('project import', 'projectImportText'), 
                                     ('project export', 'projectExport') ):
            if (hasattr(fileHandler, methName)):
                caps.append(capName)
        helpText.append('.. _file_handler_%s:' % fileHandlerName.lower().replace(' ', '_'))
        helpText.append('')
        helpText.append(fileHandlerTitle)
        helpText.append('-' * len(fileHandlerTitle))
        helpText.append('')
        helpText.append(':RegEx for filename: %s' % fileNameRe)
        helpText.append(':Default export name: %s' % exportName)
        helpText.append(':Supported modes: %s' % ', '.join(caps))
        helpText.append('')
        if (fileHandlerHelp):
            helpText.append(fileHandlerHelp)
        else:
            print 'File handler %s got no help' % fileHandlerName
        helpText.append('')
    appInfo['numFileHandlers'] = numFileHandlers
    helpPrefix = \
"""
.. file_handlers:

File Handlers
=============

File handlers are a means for the %(appName)s terminal application to 
import and export data. The %(appName)s terminal application has %(numFileHandlers)d
file handlers. Each file handler may support importing or exporting data. Some file
handlers also support importing or exporting into a project file. A project file works 
like a container and is capable of holding multiple files in it (see :ref:`file_handler_project`).

Each file handler defines a regular expression for their file name. If the expression
matches a file name, the file can be imported or exported by that file handler. A file handler
can also have a default name, which is used when exporting data where no file name is specified.

File handlers are for example used for importing/exporting data via Custom Exchange, AssistIT 
or to/form USB memory devices via the :ref:`action_usb.import` and :ref:`action_usb.export` actions.

""" % appInfo
    return helpPrefix + '\n'.join(helpText)


