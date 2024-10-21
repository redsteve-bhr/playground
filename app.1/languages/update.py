# -*- coding: utf-8 -*-
#
# Update Language Files
# -----------------------------------------------------------------------------
"""                                
This script allows you to internationalise your software.  You can use it to 
create the GNU .po files (Portable Object) files


NOTE:  this module uses GNU gettext utilities.

You can get the gettext tools from the following sites:

   - `GNU FTP site for gettetx`_ where several versions (0.10.40, 0.11.2, 0.11.5 and 0.12.1) are available.
     Note  that you need to use `GNU libiconv`_ to use this. Get it from the `GNU
     libiconv  ftp site`_ and get version 1.9.1 or later. Get the Windows .ZIP
     files and install the packages inside c:/gnu. All binaries will be stored
     inside  c:/gnu/bin.  Just  put c:/gnu/bin inside your PATH. You will need
     the following files: 

      - `gettext-runtime-0.12.1.bin.woe32.zip`_ 
      - `gettext-tools-0.12.1.bin.woe32.zip`_
      - `libiconv-1.9.1.bin.woe32.zip`_ 


.. _GNU libiconv:                            http://www.gnu.org/software/libiconv/
.. _GNU libiconv ftp site:                   http://www.ibiblio.org/pub/gnu/libiconv/
.. _gettext-runtime-0.12.1.bin.woe32.zip:    ftp://ftp.gnu.org/gnu/gettext/gettext-runtime-0.12.1.bin.woe32.zip           
.. _gettext-tools-0.12.1.bin.woe32.zip:      ftp://ftp.gnu.org/gnu/gettext/gettext-tools-0.12.1.bin.woe32.zip 
.. _libiconv-1.9.1.bin.woe32.zip:            ftp://ftp.gnu.org/gnu/libiconv/libiconv-1.9.1.bin.woe32.zip


Based on MKI18N.PY

"""

#
import os
import re
import tempfile
import zipfile
import shutil
import sys


LANGUAGES = ['us', 'en', 'de', 'es', 'fr', 'nl', 'zh', 'zh_TW']
processedPoFiles = set()
wordsToIgnore = []

_poFileHeader = ('msgid ""\n'
                 'msgstr "Content-Type: text/plain; charset=UTF-8\\n"\n')

# -----------------------------------------------------------------------------
def createPoFile(fname):
    """Create the file if it does not exist"""
    po = open(fname, 'a')
    po.write(_poFileHeader)
    po.write('\n')
    po.close()
    processedPoFiles.add(fname)

# -----------------------------------------------------------------------------
def preparePoFile(fname):
    """Remove all comments"""
    if (fname in processedPoFiles):
        return
    r = re.compile('^\#.*$', re.MULTILINE)
    poContent = open(fname, 'r').read()
    po = open(fname, 'w')
    po.write(r.sub('', poContent))
    po.close()
    processedPoFiles.add(fname)    

# -----------------------------------------------------------------------------
def fixPoFile(fname):
    poContent = open(fname, 'r').read()
    poContent = poContent.replace(_poFileHeader, '')
    po = open(fname, 'w')
    po.write(_poFileHeader)
    po.write('\n')    
    for l in poContent.splitlines():
        if (l.startswith('#')):
            l = l.replace('\\', '/')
            l = l.replace('possible-python-format', 'python-format')
        po.write(l + '\n')
    po.close()
    # Force \r\n
    poContent = open(fname, 'r').read()
    po = open(fname, 'wb')
    for l in poContent.splitlines():
        po.write(l + '\r\n')

# -----------------------------------------------------------------------------
def extractZipToDir(zipName):
    tmpDir = tempfile.mkdtemp()
    fwapi  = zipfile.ZipFile(zipName)
    fwapi.extractall(tmpDir)
    return tmpDir
    
# -----------------------------------------------------------------------------
def getPyFiles(fileList, dirname, names):
    for pyFile in filter( lambda n: n.endswith('.py'), names):
        fileList.append( os.path.join(dirname, pyFile) )
    #if (os.sep == '\\'):
    #        files = files.replace(os.sep, '/')
    #    appFiles.append(files)

# -----------------------------------------------------------------------------
def makePO(path):
    """Create the .po file for each language"""
    cwd = os.getcwd()
    try:
        if (path.endswith('.zip')):
            tmpDir = extractZipToDir(path)
            os.chdir(tmpDir)
        else:
            os.chdir(path)
        pyFiles = []
        os.path.walk('./', getPyFiles, pyFiles)
        for lang in LANGUAGES:
            poFile = os.path.join(cwd, '%s.po' % lang)
            if (not os.path.exists(poFile)):
                createPoFile(poFile)
            else:
                preparePoFile(poFile)
            # update the language files with the latest text        
            cmd = 'xgettext --omit-header -F -j -o %s %s' % (poFile, ' '.join(pyFiles))
            # check for windows install
            if (os.path.exists('C:\\gnu\\bin\\xgettext.exe')):
                cmd = 'C:\\gnu\\bin\\' + cmd
            elif (sys.platform == 'darwin'):
                cmd = '/usr/local/bin/' + cmd
            print '%s' % cmd
            os.system(cmd)
            fixPoFile(poFile)
    finally:
        os.chdir(cwd)

    if (path.endswith('.zip') and tmpDir != '/'):
        print('Deleting %s' % tmpDir)
        shutil.rmtree(tmpDir)


# -----------------------------------------------------------------------------
def checkPOs():
    cwd = os.getcwd()    
    for lang in LANGUAGES:
        poFile = os.path.join(cwd, '%s.po' % lang)
        checkPoFile(poFile)


# -----------------------------------------------------------------------------
def checkPoFile(poFile):
    poName = poFile[-5:-3]
    poLines = open(poFile, 'r').readlines()
    poLines = [ l.strip() for l in poLines ]
    if (poLines[0] != 'msgid ""' or poLines[1] != 'msgstr "Content-Type: text/plain; charset=UTF-8\\n"'):
        print 'Error   [%s]: No header' % poName
        raise Exception('No header in %s' % poFile)
    if (poName == 'en'):
        return
    msgid = msgstr = None
    for l in poLines:
        if (l.startswith('msgid "')):
            msgid = l[7:-1]
            msgstr = None
        elif (l.startswith('msgstr "')):
            msgstr = l[8:-1]
        elif (l.startswith('"')):
            if (msgstr == None):
                msgid += l[1:-1]
            else:
                msgstr += l[1:-1]
        else:
            if (msgid and not msgstr and msgid not in wordsToIgnore and poName != 'us'):
                print 'Warning [%s]: Missing translation for "%s"' % (poName, msgid)
            if (msgid and msgstr and msgid.count('%') != msgstr.count('%')):
                print 'Error   [%s]: Different occurrences of %% for "%s"' % (poName, msgid)
                raise Exception('Different occurrences of %% in %s' % poFile)
            msgid = msgstr = None


# -----------------------------------------------------------------------------
if __name__ == '__main__':
    try:
        makePO('../')
        #makePO('../applib/doc/fwapi.zip')
        checkPOs()
    except IOError, e:
        print(e[1] + '\n Error creating .po files')
    


