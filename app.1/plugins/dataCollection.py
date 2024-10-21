# -*- coding: utf-8 -*-
#
# Copyright 2011 Grosvenor Technology
#
import itg
import log
import xml.etree.cElementTree as ET
import webClient

from engine import dynButtons, fileHandler, acceptMsgDlg, badge
from applib.gui import msg
from applib.utils import timeUtils
from applib.db import sqlTime

# for last clockings
from plugins.clockings.tblLastClockings import getAppLastClocking

def _getText(tag, languages, default=None):
    """ Extract text for given language. """
    if (tag == None):
        return default
    if (len(tag) == 0):
        return tag.text or ''
    for language in languages:
        for text in tag:
            if (text.tag != 'text'):
                continue
            if (text.get('language') == language):
                return text.text
    return default

def _getMultiLanguageText(tag):
    """ Find all text and return as dictionary with language as key. """
    textDict = {}
    if (tag == None):
        pass
    elif (len(tag) == 0):
        if (tag.text):
            textDict['en'] = tag.text
    else:
        for text in tag:
            if (text.tag != 'text'):
                continue
            lang =text.get('language', None)
            if (lang and text.text):
                textDict[lang] = text.text
    return textDict


class DataCollection(object):
    """ Wrapper class for dataCollection.xml file. A data collection XML
        files holds a list of data collection flows, e.g.::
        
            <dataCollection>
              <dataCollectionFlow id="flow-1">
                ...
              </dataCollectionFlow>

              <dataCollectionFlow id="flow-2">
                ...
              </dataCollectionFlow>
            </dataCollection>

        """
    
    def __init__(self):
        self.__xml = None
        self.__filename = '/mnt/user/db/dataCollection.xml'

    def __removeNamespace(self, doc, ns=None):
        """Remove namespace in the passed document in place."""
        for elem in doc.getiterator():
            if elem.tag.startswith('{'):
                uri, tagName = elem.tag[1:].split('}')
                if (ns == None):
                    elem.tag = tagName
                elif (ns == uri):
                    elem.tag = tagName

    def __loadXml(self):
        try:
            xmlTree = ET.parse(self.__filename)
            self.__xml = xmlTree.getroot()
            self.__removeNamespace(self.__xml)
            if (self.__xml.tag != 'dataCollection'):
                raise Exception('Invalid root tag "%s" for dataCollection' % (self.__xml.tag,))
        except IOError: # no dataCollection.xml, no error message
            self.__xml = None 
        except Exception as e:
            log.err('Error parsing dataCollection.xml file: %s' % (e,))
            self.__xml = None
    
    def getAll(self):
        """ Return list of all data collection flows (*DataCollectionFlow*). """
        self.__loadXml()
        if (self.__xml == None):
            return []
        return [ DataCollectionFlow(t) for t in self.__xml.findall('dataCollectionFlow') ]

    def getById(self, flowId):
        """ Return data collection flow (*DataCollectionFlow*) for given Id or **None**. """
        self.__loadXml()
        if (self.__xml == None):
            return None
        for flow in self.__xml.findall('dataCollectionFlow'):
            if (flow.get('id') == flowId):
                return DataCollectionFlow(flow)
        return None


class DataCollectionFlow(object):
    """ Wrapper class for accessing data collection flow data. A data 
        collection flow consists of a configuration section and a 
        list of levels, e.g.::
        
            <dataCollectionFlow id="flow-1">

              <config>
                <button>
                  <label>Data Entry</label>
                </button>
                <response>
                  <message>Data entry accepted!</message>
                </response>
              </config>

              <levels>...</levels>
            
            </dataCollectionFlow>

        """
    
    def __init__(self, dataCollectionFlowXml):
        self.__xml = dataCollectionFlowXml
        if (self.__xml.tag != 'dataCollectionFlow'):
            raise Exception('Invalid tag "%s" for data collection flow' % (self.__xml.tag,))
        
    def getId(self):
        """ Return Id of data collection flow. """
        return self.__xml.get('id')
    
    def getReqRole(self):
        """ Return required employee role or **None** if none was specified in flow. """
        reqRoleTag = self.__xml.find('config/button/reqRole')
        if (reqRoleTag != None):
            return reqRoleTag.text
        return None

    def getGroup(self):
        """ Return group or **None**."""
        groupTag = self.__xml.find('config/button/group')
        if (groupTag != None):
            return groupTag.text
        return None

    def getButtonText(self, languages):
        """ Return button text for flow. *languages* is a list with 
            preferred languages (e.g. ['en', 'de']. 
        """
        return _getText(self.__xml.find('config/button/label'), languages)
            
    def getResponseText(self, languages):
        """ Return text to be shown when the transaction was sent. *languages* is a list
            with preferred langauges (e.g. ['en', 'de']).
        """
        return _getText(self.__xml.find('config/response/message'), languages, _('Accepted'))
    
    def getReviewType(self):
        """ Return review type, used for last clockings. """
        reviewType = self.__xml.find('config/review/type')
        if (reviewType != None):
            return reviewType.text
        return None
    
    def getMultiLanguageReviewText(self):
        """ Return dictionary with review text for all languages. The language 
            is used as key.
        """
        reviewLabel = self.__xml.find('config/review/label')
        if (reviewLabel != None):
            return _getMultiLanguageText(reviewLabel)
        return None
    
    def getLevels(self):
        """ Return list of data collection levels (*_DataCollectionLevel*). """
        return [ _DataCollectionLevel(i) for i in self.__xml.findall('levels/level') ]
            
    def checkRoleAndGroup(self, roles, group):
        """ Return **True** if the data collection flow can be used with the given
            roles and group.
            A flow should not be used, if a role was defined but is not in the given 
            list of roles. A flow should also not be used if a group was defined and
            it does not match the given group.
        """
        if not dynButtons.hasRequiredRole(roles, self.getReqRole()):
            return False
        if (group and self.getGroup() != group):
            return False
        return True
    

class _DataCollectionLevel(object):
    """ Wrapper class for data collection level. A level usually contains
        a title and a list of items to be shown, e.g.::
        
            <level>
              <title>Levels</title>
              <items>
                <item id="item1">...</item>
                <item id="item2">...</item>
                <item id="item3">...</item>
              </items>
            </level>
        
        A level can also contain data entries that can be referenced from
        within sub-levels.
    """
    
    def __init__(self, xmlLevelTag):
        self.__xml = xmlLevelTag
        if (self.__xml.tag != 'level'):
            raise Exception('Invalid tag "%s" for data collection level' % (self.__xml.tag,))
    
    def getId(self):
        """ Return Id of the level or **None**. A level only requires
            to have an Id if is referenced (see linked lists). """
        return self.__xml.get('id')
        
    def getRefId(self):
        """ Return Id of referenced level. """
        return self.__xml.get('ref')
        
    def getTitle(self, languages):
        """ Return title. """
        return _getText(self.__xml.find('title'), languages, _('Please select'))
    
    def getItems(self):
        """ Return list of items (*_DataCollectionItem*). """
        return [ _DataCollectionItem(i) for i in self.__xml.findall('items/item') ]
    
    def getDataEntries(self):
        """ Return list of data entries (*_DataCollectionDataEntry*). These data
            entries can be referenced from an data collection item.
        """
        dataEntries = {}
        for dataEntryElem in self.__xml.findall('dataEntries/dataEntry'):
            dataEntry = _DataCollectionDataEntry(dataEntryElem)
            dataEntries[dataEntry.getId()] = dataEntry
        return dataEntries


class _DataCollectionItem(object):
    """ Wrapper class for data collection items. An item has an Id
        and a label, e.g.::
        
            <item id="subitem1">
              <label>Sub-level 1</label>
            </item>
        
        An item can also have data entry steps and new sub-levels.
    """
    
    def __init__(self, xmlItemTag):
        self.__xml = xmlItemTag
        if (self.__xml.tag != 'item'):
            raise Exception('Invalid tag "%s" for data collection item' % (self.__xml.tag,))

    def getId(self):
        """ Return Id of item. """
        return self.__xml.get('id')

    def getLabel(self, languages):
        """ Return label. *languages* is a list of preferred languages. """
        return _getText(self.__xml.find('label'), languages)
    
    def getSubLevels(self):
        """ Return list of levels (*_DataCollectionLevel*) defined on item. """
        return [ _DataCollectionLevel(i) for i in self.__xml.findall('levels/level') ]
    
    def getSubLevelRefId(self):
        """ Returns the ref ID  attribute of a levelRef element """
        elem = self.__xml.find('levelRef')
        if (elem != None):
            return elem.get('ref')
        return None
    
    def getDataEntry(self, refdDataEntries):
        """ Return *_DataCollectionDataEntry* or **None** if none are defined. """
        dataEntryElem = self.__xml.find('dataEntry')
        if (dataEntryElem == None):
            return None
        refId = dataEntryElem.get('ref')
        if (refId != None):
            return refdDataEntries.get(refId)
        return _DataCollectionDataEntry(dataEntryElem)
        
    
class _DataCollectionDataEntry(object):
    """ Wrapper class for data entry. A data entry element contains 
        a sequence of different data entry steps, e.g.::

          <dataEntry>        
            <numericEntryStep id="numeric.input1">
              <title>Please enter number</title>
              <default>10</default>
            </numericEntryStep>
          </dataEntry>        
    
    """
    
    def __init__(self, xmlDataEntryTag):
        self.__xml = xmlDataEntryTag
        if (self.__xml.tag != 'dataEntry'):
            raise Exception('Invalid tag "%s" for data collection data entry' % (self.__xml.tag,))
 
    def getId(self):
        """ Return Id of data entry. Only data entries used for referencing require
            to have an Id.
        """
        return self.__xml.get('id')

    def hasSteps(self):
        """ Return **True** if data entry has steps. """
        return (len(self.__xml)>0)

    def getSteps(self):
        """ Return list of data entry steps. """
        steps = []
        for e in self.__xml:
            if (e.tag == 'numericEntryStep'):
                steps.append(_NumericDataEntryStep(e))
            elif (e.tag == 'textEntryStep'):
                steps.append(_TextDataEntryStep(e))
            elif (e.tag == 'maskedEntryStep'):
                steps.append(_MaskedDataEntryStep(e))
            elif (e.tag == 'fixedTextStep'):
                steps.append(_FixedTextStep(e))
        return steps


class _AbstractDataEntryStep(object):
    """ Abstract base-class for data entry steps. All (or most?)
        data entry steps have an Id, a title and a default, e.g.::
        
          <numericEntryStep id="numeric.input1">
            <title>Please enter number</title>
            <default>10</default>
          </numericEntryStep>
    
    """
    
    def __init__(self, xmlDataEntryTag):
        self._xml = xmlDataEntryTag

    def getId(self):
        """ Return Id of data entry step. """
        return self._xml.get('id')
    
    def getTagName(self):
        """ Get tag name of data entry step. """
        return self._xml.tag

    def getTitle(self, languages):
        """ Get title of step. """
        return _getText(self._xml.find('title'), languages, _('Please select'))

    def getDefault(self):
        """ Get default value (as a **String**) or **None**. """
        elem = self._xml.find('default')
        if (elem != None):
            return elem.text
        return None

    def _getNumericVal(self, tagName, default=None):
        valElem = self._xml.find(tagName)
        if (valElem == None or not valElem.text):
            return default
        try:
            return int(valElem.text)
        except:
            log.err('Error converting "%s" ("%s") to integer!' % (tagName, valElem.text))
            return default

    def getExtraButton(self):
        """ Return extra button if one was defined. """
        extraBtnElem = self._xml.find('extraButton')
        if (extraBtnElem == None):
            return None
        for e in extraBtnElem:
            if (e.tag == 'skipButton'):
                return _DataEntrySkipButton(e)
            elif (e.tag == 'helpButton'):
                return _DataEntryHelpButton(e)
            elif (e.tag == 'doneButton'):
                return _DataEntryDoneButton(e)
        return None
    
    def allowReader(self):
        """ Return **True** if reader can be used. """
        return (self._xml.find('reader') != None)
    
    def isReaderAutoCommitEnabled(self, default=False):
        """ Return **True** if a read completes the data entry. """
        readerElem = self._xml.find('reader')
        if (readerElem == None):
            return default
        val = readerElem.find('autoCommit')
        if val is not None:
            if (val.text.lower() == 'true'):
                return True
            elif (val.text.lower() == 'false'):
                return False
        return default

    def _getBoolVal(self, tagName, default):
        valElem = self._xml.find(tagName)
        if (valElem != None):
            if (valElem.text == 'true'):
                return True
            elif (valElem.text == 'false'):
                return False
        return default
    

class _NumericDataEntryStep(_AbstractDataEntryStep):

    def getMin(self, default=None):
        """ Return required minimum of numeric input.
            The returned value is an integer or *default*
            if not specified. 
        """
        return self._getNumericVal('min', default)

    def getMax(self, default=None):
        """ Return required maximum of numeric input.
            The returned value is an integer or *default*
            if not specified. 
        """
        return self._getNumericVal('max', default)
    
    def allowEmpty(self, default=False):
        """ Return **True** if it is Ok to not enter anything. """
        return self._getBoolVal('allowEmpty', default)


class _TextDataEntryStep(_AbstractDataEntryStep):

    def getMin(self, default=None):
        """ Return required minimum of numeric input.
            The returned value is an integer or *default*
            if not specified. 
        """
        return self._getNumericVal('min', default)

    def getMax(self, default=None):
        """ Return required maximum of numeric input.
            The returned value is an integer or *default*
            if not specified. 
        """
        return self._getNumericVal('max', default)


class _MaskedDataEntryStep(_AbstractDataEntryStep):

    def getMask(self):
        elem = self._xml.find('mask')
        if (elem != None):
            return elem.text
        return None

class _FixedTextStep(_AbstractDataEntryStep):
    
    def getTagName(self):
        """ Get tag name of data entry step. """
        return 'fixedTextEntryStep'

    def getFixedText(self):
        elem = self._xml.find('text')
        if (elem != None):
            return elem.text
        return None

class _AbstractDataEntryExtraButton(object):
    
    def __init__(self, xmlButtonTag):
        self._xml = xmlButtonTag
        
    def getLabel(self, languages):
        """ Return label. *languages* is a list of preferred languages. """
        return _getText(self._xml.find('label'), languages)


class _DataEntrySkipButton(_AbstractDataEntryExtraButton):
    pass


class _DataEntryDoneButton(_AbstractDataEntryExtraButton):
    pass


class _DataEntryHelpButton(_AbstractDataEntryExtraButton):

    def getHelp(self, languages):
        """ Return help text. *languages* is a list of preferred languages. """
        return _getText(self._xml.find('help'), languages)



class _DataCollectionMenuDialog(itg.Dialog):    
    """Dialog for showing menu with data collection buttons """

    def __init__(self, employee, languages, group=None):
        super(_DataCollectionMenuDialog, self).__init__()
        self.__employee = employee
        self.__languages = languages
        view = itg.MultiGridMenuView()
        view.setBackCb(self.back)
        roles = employee.getRoles()
        self.__flows = filter(lambda t: t.checkRoleAndGroup(roles, group), DataCollection().getAll())
        for (idx, flow) in enumerate(self.__flows):
            btnText = flow.getButtonText(languages)
            if (btnText):
                view.setButton(idx, btnText, idx, self.__onClick)
            else:
                log.err('Data collection flow %s has no button text!' % flow.getId())
        self.addView(view)
        
    def run(self):
        if (len(self.__flows) == 1):
            # Handle flow straight away if only one
            flow = self.__flows[0]
            dlg = _DataCollectionDialog(self.__employee, self.__languages, flow)
            resID = dlg.run()
            self.setResultID(resID)
            return resID
        else:
            return super(_DataCollectionMenuDialog, self).run()
    
    def __onClick(self, menuIdx):
        """Call the selection dialogs"""
        flow = self.__flows[menuIdx]
        dlg = _DataCollectionDialog(self.__employee, self.__languages, flow)
        resID = dlg.run()
        if (resID in (itg.ID_OK, itg.ID_NEXT)):
            self.quit(itg.ID_OK)
        
        
class _DataCollectionDialog(itg.PseudoDialog):
    """ Dialog for running the employee through a data collection flow.
        A data collection transaction is sent at the end of the selection.
    """

    def __init__(self, employee, languages, flow, actionType=None):
        super(_DataCollectionDialog, self).__init__()
        self.__employee = employee
        self.__languages = languages
        self.__flow = flow
        self.__actionType = actionType
    
    def run(self):
        # let user select items from data collection flow
        dlg = DataCollectionFlowDialog(self.__languages, self.__flow.getLevels())
        resID = dlg.run()
        if (resID not in (itg.ID_OK, itg.ID_NEXT)):
            self.setResultID(resID)
            return resID
        # send transaction
        try:
            # get time
            sqlTimestamp = sqlTime.getSqlTimestampNow()
            xmlTimestamp = timeUtils.getXMLTimestampNow()
            dataCollectionResult = dlg.getDataCollectionResult(self.__flow.getId(), xmlTimestamp, self.__actionType)
            # send transaction
            self.__sendTransaction(dataCollectionResult, sqlTimestamp)
            # show response text
            responseText = '%s\n%s' % (self.__employee.getName(), self.__flow.getResponseText(self.__languages))
            acceptMsgDlg.acceptMsg(responseText, acceptReader=True)
        except Exception as e:
            msg.failMsg(_('Failed to send transaction: %s') % e)
        self.setResultID(itg.ID_OK)
        return itg.ID_OK

    def __sendTransaction(self, dataCollectionResult, sqlTimestamp):
        # get transaction table
        transactions = webClient.getAppTransactions()
        # check transaction buffer
        if (not transactions.hasSpace()):
            raise Exception(_('Transaction buffer full!'))
        # add to transaction table
        # TODO: Find a way of getting the action name, instead of hard-coding "ws.dataCollection"
        transactions.addTransaction(dataCollectionResult, self.__employee, "ws.dataCollection")
        # add to last clockings table
        reviewType = self.__flow.getReviewType()
        if (reviewType):
            getAppLastClocking().add(reviewType, 
                              sqlTimestamp, 
                              self.__employee.getEmpID(), 
                              None, 
                              self.__flow.getMultiLanguageReviewText())
        

class DataCollectionFlowDialog(itg.Dialog):
    """ Dialog to go through all levels of a data collection flow. """

    def __init__(self, languages, levels, refdLevels=None, refdDataEntries=None):
        super(DataCollectionFlowDialog, self).__init__()
        self.__languages  = languages
        self.__selectedItems  = []
        # first level is used for this dialog
        level = levels[0]
        # every level after the first is used for referencing
        self.__refdLevels = levels[1:] + (refdLevels or [])
        # update referenced data entries
        self.__refdDataEntries = refdDataEntries or {}
        self.__refdDataEntries.update(level.getDataEntries())
        # lookup actual level if reference id is given
        if (level.getRefId()):
            level = self.__findLevelByRef(level.getRefId())
        # create view
        view = itg.ListView(level.getTitle(languages))
        if (level):
            # put in items
            for item in level.getItems():
                itemId = item.getId()
                itemLabel = item.getLabel(languages) or ('Item (%s)' % itemId)
                if (not itemId or not itemLabel):
                    log.warn('Item id or label missing (%s:%s)' % (itemId, itemLabel))
                    continue
                view.appendRow(itemLabel, item)
        view.setCancelButton(_('Cancel'), cb=self.cancel)        
        view.setBackButton(_('Back'), cb=self.back)
        view.setOkButton(_('Next'), cb=self.__onNext)        
        self.addView(view)
        
    def __findLevelByRef(self, ref):
        for l in self.__refdLevels:
            if (l.getId() == ref):
                return l
        return None
    
    def getSelectedItems(self):
        """ Return selection of user in the form of a list of 
            XML elements ready to be used within a transaction.
            Only call this function after the dialog finished
            with itg.ID_OK.
        """
        return self.__selectedItems
    
    def getDataCollectionResult(self, flowId=None, xmlTimestamp=None, actionType=None):
        """ Return data collection flow result in form of an
            dataCollection XML element, e.g.::
            
              <dataCollection>
                <time>2016-03-24T09:50:54+0000</time>
                <selection flowId="flow-1">
                  <item id="item1" />
                  <item id="item2" />
                </selection>
              </dataCollection>
              
            *flowId* and *xmlTimestamp* are **String**s that can
            be supplied optionally.

        """
        dataCollectionTag = ET.Element('dataCollection')
        # insert time
        if (xmlTimestamp):
            ET.SubElement(dataCollectionTag, 'time').text = xmlTimestamp
        # insert information about selected items 
        e = ET.SubElement(dataCollectionTag, 'selection')
        if (flowId):
            e.set('flowId', flowId)
        if (actionType):
            ET.SubElement(e, 'actionType').text = actionType
        # add selected items
        for s in self.getSelectedItems():
            e.append(s)
        return dataCollectionTag
    
    def run(self):
        if (self.getView().numberOfRows() == 1):
            # Handle single item straight away 
            item = self.getView().getRowByPosition(0)['data']
            resID = self.__processItem(item)
            self.setResultID(resID)
            return resID
        return super(DataCollectionFlowDialog, self).run()
        
    def __onNext(self, btnID):
        item = self.getView().getSelectedRow()['data']
        resID = self.__processItem(item)
        if (resID != itg.ID_BACK):
            self.quit(resID)
    
    def __processItem(self, item):
        # create XML for selected item
        selectedItem = ET.Element('item')
        selectedItem.set('id', item.getId())
        # check for data collection
        dataEntry = item.getDataEntry(self.__refdDataEntries)
        if (dataEntry != None and dataEntry.hasSteps()):
            # run through data entry steps here
            dlg = _getDataEntryDialogInstance(self.__languages, dataEntry.getSteps())
            resID = dlg.run()
            if (resID not in (itg.ID_OK, itg.ID_NEXT)):
                return resID # bail out on anything but OK
            # create data entry element as a sub-element of selectedItem
            dataEntryResult = ET.SubElement(selectedItem, 'dataEntry')
            # append all data entry results
            for d in dlg.getEnteredData():
                dataEntryResult.append(d)
        # check for sub-levels
        levels = item.getSubLevels()
        if (not levels):
            # Levels not found, look for level reference e.g. <levelRef ref="level2" />
            levelRefId = item.getSubLevelRefId()
            if (levelRefId):
                # Have a level reference, get the level, and add to list of levels
                level = self.__findLevelByRef(levelRefId)
                levels = [level]
        if (levels):
            # Recursive call for dialog on next level down
            dlg = DataCollectionFlowDialog(self.__languages, levels, self.__refdLevels, self.__refdDataEntries)
            resID = dlg.run()
            # if dialog comes back with OK, remember selection
            if (resID in (itg.ID_OK, itg.ID_NEXT)):
                self.__selectedItems = [selectedItem] + dlg.getSelectedItems()
            return resID
        else:
            # no sub-levels, so just remember selection of this dialog
            self.__selectedItems = [selectedItem]
            return itg.ID_OK

        
def _getDataEntryDialogInstance(languages, steps):
    """ Factory method for returning data entry dialog instance based
        on next step. 
    """
    step = steps[0]
    if (isinstance(step, _NumericDataEntryStep)):
        return _NumericDataEntryDialog(languages, steps)
    elif (isinstance(step, _TextDataEntryStep)):
        return _TextDataEntryDialog(languages, steps)
    elif (isinstance(step, _MaskedDataEntryStep)):
        return _MaskedDataEntryDialog(languages, steps)
    elif (isinstance(step, _FixedTextStep)):
        return _FixedTextDialog(languages, steps)
    else:
        raise Exception('Unexpected data entry step class (%s)' % step)
    

class _AbstractDataEntryDialog(itg.Dialog):
    """ Abstract Dialog class for collecting data entry data. This dialog 
        accepts a list of data entry steps. The entered data is available via 
        *getEnteredData* after the dialog returned with **itg.ID_OK**.
        
        Derived classes may have to implement onCreate, _validate
        or _getValue.
    """
    
    def __init__(self, languages, dataEntrySteps):
        super(_AbstractDataEntryDialog, self).__init__() 
        self._enteredData = []
        self._languages = languages
        self._curStep = dataEntrySteps[0]
        self._nextSteps = dataEntrySteps[1:]
        if (self._curStep.allowReader()):
            self.setReaderCb(self._onReader)
        
    def _onReader(self, isValid, rdr, decoder, data):
        if (not isValid):
            itg.failureSound()
            return
        itg.tickSound()
        self.getView().setValue(data)
        if (self._curStep.isReaderAutoCommitEnabled(True)):
            self._onNext(itg.ID_NEXT)

    def getEnteredData(self):
        """ Return entered data as list of XML elements (one entry per
            data entry step). The data can be used as part of the transaction.
        """
        return self._enteredData
    
    def _createDefaultButton(self, view):
        btnOfs = 1
        extraBtn = self._curStep.getExtraButton()
        if (isinstance(extraBtn, _DataEntryDoneButton)):
            view.setButton(1, extraBtn.getLabel(self._languages), itg.ID_OK, self._onDone)
        elif (isinstance(extraBtn, _DataEntrySkipButton)):
            view.setButton(1, extraBtn.getLabel(self._languages), itg.ID_SKIP if hasattr(itg, 'ID_SKIP') else itg.ID_OK, self._onSkip)
        elif (isinstance(extraBtn, _DataEntryHelpButton)):
            self._helpTxt = extraBtn.getHelp(self._languages)
            view.setButton(1, extraBtn.getLabel(self._languages), itg.ID_HELP, self._onHelp)
        else:
            btnOfs = 0
        view.setButton(0, _('Next'), itg.ID_NEXT, self._onNext)
        view.setButton(btnOfs+1, _('Back'), itg.ID_BACK, self.back)
        view.setButton(btnOfs+2, _('Cancel'), itg.ID_CANCEL, self.cancel)

    def _onNext(self, btnId):
        if (self._validate()):
            self._goToNextStep()
    
    def _onDone(self, btnId):
        if (self._validate()):
            self._goToNextStep(done=True)
    
    def _validate(self):
        # overwrite in subclass if needed!
        return True
    
    def _onSkip(self, btnId):
        self._goToNextStep(skip=True)
    
    def _onHelp(self, btnId):
        itg.msgbox(itg.MB_OK, self._helpTxt)
        
    def _getValue(self):
        # overwrite in sub-class if a view is used that 
        # does not have getView()
        return self.getView().getValue()
    
    def _goToNextStep(self, done=False, skip=False):
        # create XML element for data entry
        data = ET.Element(self._curStep.getTagName())
        data.set('id', self._curStep.getId())
        value = self._getValue()
        if (value != None and not skip):
            data.text = value
        if (skip):
            data.set('skipped', 'true')
        # run dialog with rest of steps 
        if (self._nextSteps and not done):
            dlg = _getDataEntryDialogInstance(self._languages, self._nextSteps)
            resID = dlg.run()
            if (resID == itg.ID_BACK):
                return # stay in this dialog
            elif (resID in (itg.ID_OK, itg.ID_NEXT)):
                # set data entered in this dialog and in executed sub-dialogs
                self._enteredData = [data] + dlg.getEnteredData()
            # leave this dialog
            self.quit(resID)
        else:
            # set value and leave
            self._enteredData = [data]
            self.quit(itg.ID_OK)


class _NumericDataEntryDialog(_AbstractDataEntryDialog):
    """ Data entry dialog class for numeric input. """

    def onCreate(self):
        super(_NumericDataEntryDialog, self).onCreate()
        self.setReaderCb(self.__onCardRead)
        view = itg.NumberInputView(self._curStep.getTitle(self._languages))
        val = self._curStep.getDefault()
        if (val != None):
            view.setValue(val)
        self._createDefaultButton(view)
        self.addView(view)

    def __onCardRead(self, valid, reader, decoder, data):
        log.dbg('valid=' + str(valid) + ', reader=' + str(reader) + ', decoder=' + str(decoder))
        log.dbg('data='  + str(data))
        if badge.isUSBBarcodeScan(reader, decoder):
            self.getView().setValue(data)
            if self._validate():
                if (self._curStep.isReaderAutoCommitEnabled(True)):
                    self._onNext(itg.ID_NEXT)
        
    def _validate(self):
        val = self.getView().getValue()
        # validate input
        if (not val):
            if (not self._curStep.allowEmpty()):
                itg.msgbox(itg.MB_OK, _('Please enter a numeric value.'))
                return False
        else:
            try:
                # convert to integer
                intVal = int(val)
                minVal = self._curStep.getMin()
                if (minVal != None and intVal < minVal):
                    itg.msgbox(itg.MB_OK, _('The minimum value allowed is %s.' % minVal))
                    return False
                maxVal = self._curStep.getMax()
                if (maxVal != None and intVal > maxVal):
                    itg.msgbox(itg.MB_OK, _('The maximum value allowed is %s.' % maxVal))
                    return False
            except:
                itg.msgbox(itg.MB_OK, _('Please enter a numeric value.'))
                return False
        # accept input 
        return True
    
    
class _TextDataEntryDialog(_AbstractDataEntryDialog):
    """ Data entry dialog class for text input. """

    def onCreate(self):
        super(_TextDataEntryDialog, self).onCreate()
        self.setReaderCb(self.__onCardRead)
        view = itg.TextInputView(self._curStep.getTitle(self._languages))
        val = self._curStep.getDefault()
        if (val != None):
            view.setValue(val)
        self._createDefaultButton(view)
        self.addView(view)
    
    def __onCardRead(self, valid, reader, decoder, data):
        log.dbg('valid=' + str(valid) + ', reader=' + str(reader) + ', decoder=' + str(decoder))
        log.dbg('data='  + str(data))
        if badge.isUSBBarcodeScan(reader, decoder):
            self.getView().setValue(data)
            self._validate()
            if self._validate():
                if (self._curStep.isReaderAutoCommitEnabled(True)):
                    self._onNext(itg.ID_NEXT)
        
    def _validate(self):
        val = self.getView().getValue()
        # validate input
        minVal = self._curStep.getMin()
        if (minVal != None and len(val) < minVal):
            itg.msgbox(itg.MB_OK, _('Please enter at least %s characters.' % minVal))
            return False
        maxVal = self._curStep.getMax()
        if (maxVal != None and len(val) > maxVal):
            itg.msgbox(itg.MB_OK, _('Please enter no more than %s characters.' % maxVal))
            return False
        # accept input 
        return True


class _MaskedDataEntryDialog(_AbstractDataEntryDialog):
    """ Data entry dialog class for masked input. """

    def onCreate(self):
        super(_MaskedDataEntryDialog, self).onCreate()
        self.setReaderCb(self.__onCardRead)
        view = itg.MaskedTextInputView(self._curStep.getMask(), self._curStep.getDefault(), self._curStep.getTitle(self._languages))
        self._createDefaultButton(view)
        self.addView(view)

    def __onCardRead(self, valid, reader, decoder, data):
        log.dbg('valid=' + str(valid) + ', reader=' + str(reader) + ', decoder=' + str(decoder))
        log.dbg('data='  + str(data))
        if badge.isUSBBarcodeScan(reader, decoder):
            self.getView().setValue(data)

class _FixedTextDialog(_AbstractDataEntryDialog):
    """ Data entry dialog class for Fixed Text. This dialog has no visual 
    display, it simply sets the text value and goes to the next step (if any)
    """
            
    def _getValue(self):
        return self._curStep.getFixedText()

    def run(self):
        self._goToNextStep(done=False, skip=False)
        return itg.ID_OK
        
class DataCollectionAction(dynButtons.Action):
    
    def getName(self):
        return 'ws.dataCollection'
    
    def __getFlow(self, actionParam, employee):
        if (not hasattr(actionParam, 'getParam')):
            log.warn('No data collection flow id specified!')
            return None
        try:
            flowXml = actionParam.getXMLElement('dataCollectionFlow')
            if (flowXml != None):
                flow = DataCollectionFlow(flowXml)
            else:
                flowId = actionParam.getParam('id')
                flow = DataCollection().getById(flowId)
        except Exception as e:
            log.err('Error parsing data collection parameter: %s' % e)
            return None
        if (flow != None):
            if employee and not dynButtons.hasRequiredRole(employee.getRoles(), flow.getReqRole()):
                return None
        return flow
    
    def __getActionType(self, actionParam):
        if (not hasattr(actionParam, 'getParam')):
            return None
        try:
            actionTypeElement = actionParam.getXMLElement('actionType')
            if actionTypeElement is not None:
                actionType = actionTypeElement.text
        except Exception as e:
            log.err('Error parsing data collection parameter: %s' % e)
            actionType = None
        return actionType
    
    def getButtonText(self, actionParam, employee, languages):
        flow = self.__getFlow(actionParam, employee)
        if (not flow):
            return None
        return flow.getButtonText(languages)

    def isVisible(self, actionParam, employee, languages):
        flow = self.__getFlow(actionParam, employee)
        return (flow != None)

    def getDialog(self, actionParam, employee, languages):
        flow = self.__getFlow(actionParam, employee)
        if (not flow):
            return None
        return _DataCollectionDialog(employee, languages, flow, self.__getActionType(actionParam))

    def isEmployeeRequired(self, actionParam):
        return True

    def getXsdTypes(self):
        return """
    <xs:complexType name="dataCollectionFlowType">
        <xs:all>
            <xs:element name="config" type="dataCollectionFlowConfigType" minOccurs="0" />
            <xs:element name="levels" type="dataCollectionFlowLevelsType" />
        </xs:all>
        <xs:attribute name="id" type="xs:ID" use="required" />
    </xs:complexType>

    <xs:complexType name="dataCollectionFlowConfigType">
        <xs:all>
            <xs:element name="button" type="dataCollectionFlowButtonType" minOccurs="0" />
            <xs:element name="response" type="dataCollectionFlowResponseType" minOccurs="0" />
            <xs:element name="review" type="dataCollectionFlowReviewType" minOccurs="0" />
        </xs:all>
    </xs:complexType>

    <xs:complexType name="dataCollectionFlowButtonType">
        <xs:all>
            <xs:element name="label" type="languageTextType" minOccurs="0" />
            <xs:element name="group" type="xs:normalizedString" minOccurs="0" />
            <xs:element name="reqRole" type="xs:normalizedString" minOccurs="0" />
        </xs:all>
    </xs:complexType>

    <xs:complexType name="dataCollectionFlowResponseType">
        <xs:all>
            <xs:element name="message" type="languageTextType" />
        </xs:all>
    </xs:complexType>

    <xs:complexType name="dataCollectionFlowReviewType">
        <xs:all>
            <xs:element name="type" type="xs:normalizedString" minOccurs="1" />
            <xs:element name="label" type="languageTextType" minOccurs="1" />
        </xs:all>
    </xs:complexType>

    <xs:complexType name="dataCollectionFlowDataEntriesType">
        <xs:sequence>
            <xs:element name="dataEntry" type="dataCollectionFlowDataEntryWithIdType" minOccurs="0" maxOccurs="unbounded" />
        </xs:sequence>
    </xs:complexType>

    <xs:complexType name="dataCollectionFlowDataEntryType">
        <xs:choice maxOccurs="unbounded" >
            <xs:element name="numericEntryStep" type="dataCollectionFlowNumericEntryStep" minOccurs="0" maxOccurs="unbounded" />
            <xs:element name="textEntryStep" type="dataCollectionFlowTextEntryStep" minOccurs="0" maxOccurs="unbounded" />
            <xs:element name="maskedEntryStep" type="dataCollectionFlowMaskedEntryStep" minOccurs="0" maxOccurs="unbounded" />
            <xs:element name="fixedTextStep" type="dataCollectionFlowFixedTextStep" minOccurs="0" maxOccurs="unbounded" />
       </xs:choice>
       <xs:attribute name="ref" type="xs:IDREF" />
    </xs:complexType>

    <xs:complexType name="dataCollectionFlowDataEntryWithIdType">
        <xs:complexContent>
          <xs:extension base="dataCollectionFlowDataEntryType">
             <xs:attribute name="id" type="xs:ID" use="required" />
          </xs:extension>
        </xs:complexContent>
    </xs:complexType>
    
    <xs:complexType name="dataCollectionFlowNumericEntryStep">
        <xs:all>
            <xs:element name="title" type="languageTextType" />
            <xs:element name="default" type="xs:integer" minOccurs="0" />
            <xs:element name="min" type="xs:integer" minOccurs="0" />
            <xs:element name="max" type="xs:integer" minOccurs="0" />
            <xs:element name="allowEmpty" type="xs:boolean" minOccurs="0" />
            <xs:element name="reader" type="dataCollectionFlowReaderOption" minOccurs="0" />
            <xs:element name="extraButton" type="dataCollectionFlowExtraButton" minOccurs="0" />
        </xs:all>
        <xs:attribute name="id" type="xs:normalizedString" use="required" />
    </xs:complexType>

    <xs:complexType name="dataCollectionFlowFixedTextStep">
        <xs:all>
            <xs:element name="text" type="xs:string" minOccurs="1" maxOccurs="1" />
        </xs:all>
        <xs:attribute name="id" type="xs:normalizedString" use="required" />
    </xs:complexType>

    <xs:complexType name="dataCollectionFlowTextEntryStep">
        <xs:all>
            <xs:element name="title" type="languageTextType" />
            <xs:element name="default" type="xs:string" minOccurs="0"/>
            <xs:element name="min" type="xs:integer" minOccurs="0" />
            <xs:element name="max" type="xs:integer" minOccurs="0" />
            <xs:element name="reader" type="dataCollectionFlowReaderOption" minOccurs="0" />
            <xs:element name="extraButton" type="dataCollectionFlowExtraButton" minOccurs="0" />
        </xs:all>
        <xs:attribute name="id" type="xs:normalizedString" use="required" />
    </xs:complexType>

    <xs:complexType name="dataCollectionFlowMaskedEntryStep">
        <xs:all>
            <xs:element name="title" type="languageTextType" />
            <xs:element name="default" type="xs:string" />
            <xs:element name="mask" type="xs:string" />
            <xs:element name="reader" type="dataCollectionFlowReaderOption" minOccurs="0" />
            <xs:element name="extraButton" type="dataCollectionFlowExtraButton" minOccurs="0" />
        </xs:all>
        <xs:attribute name="id" type="xs:normalizedString" use="required" />
    </xs:complexType>

    <xs:complexType name="dataCollectionFlowReaderOption">
        <xs:attribute name="autoCommit" type="xs:boolean" />
    </xs:complexType>

    <xs:complexType name="dataCollectionFlowExtraButton">
        <xs:choice>
            <xs:element name="doneButton" type="dataCollectionFlowExtraDoneButton" />
            <xs:element name="skipButton" type="dataCollectionFlowExtraSkipButton" />
            <xs:element name="helpButton" type="dataCollectionFlowExtraHelpButton" />
        </xs:choice>
    </xs:complexType>

    <xs:complexType name="dataCollectionFlowExtraDoneButton">
        <xs:all>
            <xs:element name="label" type="languageTextType" />
        </xs:all>
    </xs:complexType>

    <xs:complexType name="dataCollectionFlowExtraSkipButton">
        <xs:all>
            <xs:element name="label" type="languageTextType" />
        </xs:all>
    </xs:complexType>

    <xs:complexType name="dataCollectionFlowExtraHelpButton">
        <xs:all>
            <xs:element name="label" type="languageTextType" />
            <xs:element name="help" type="languageTextType" />
        </xs:all>
    </xs:complexType>

    <xs:complexType name="dataCollectionFlowLevelsType">
        <xs:sequence>
            <xs:element name="level" type="dataCollectionFlowLevelType" minOccurs="0" maxOccurs="unbounded" />
        </xs:sequence>
    </xs:complexType>

    <xs:complexType name="dataCollectionFlowLevelType">
        <xs:all>
            <xs:element name="title" type="languageTextType" />
            <xs:element name="items" type="dataCollectionFlowItemsType" />
            <xs:element name="dataEntries" type="dataCollectionFlowDataEntriesType" minOccurs="0"/>
        </xs:all>
        <xs:attribute name="id" type="xs:ID" />
    </xs:complexType>

    <xs:complexType name="dataCollectionFlowItemsType">
        <xs:sequence>
            <xs:element name="item" type="dataCollectionFlowItemType" maxOccurs="unbounded" />
        </xs:sequence>
    </xs:complexType>

    <xs:complexType name="dataCollectionFlowLevelRefType">
        <xs:attribute name="ref" type="xs:IDREF" use="required"/>
    </xs:complexType>

    <xs:complexType name="dataCollectionFlowItemType">
        <xs:all>
            <xs:element name="label" type="languageTextType" />
            <xs:element name="levels" type="dataCollectionFlowLevelsType" minOccurs="0" />
            <xs:element name="dataEntry" type="dataCollectionFlowDataEntryType" minOccurs="0" />
            <xs:element name="levelRef" type="dataCollectionFlowLevelRefType" minOccurs="0" />
        </xs:all>
        <xs:attribute name="id" type="xs:ID" use="required" />
    </xs:complexType>
        """

    def getXsd(self):
        return """
            <xs:complexType>
                <xs:all>
                    <xs:element name="id" type="xs:normalizedString" minOccurs="0" />
                    <xs:element name="dataCollectionFlow" type="dataCollectionFlowType" minOccurs="0" />
                </xs:all>
            </xs:complexType>
        """

    def getHelp(self):
        return """
        Collect data from employee.
        
        This action collects data from the employee. The required steps can be defined
        in a data collection XML file via the :ref:`file_handler_datacollection`
        or as action parameter.

        Example::
        
            <button>
                <pos>1</pos>
                <action>
                    <ws.dataCollection>
                        <id>absences</id>
                    </ws.dataCollection>
                </action>
            </button>


        Example with data collection flow defined as action parameter::
        
            <button>
              <pos>5</pos>
              <label>Flip coin</label>
              <action>
                <ws.dataCollection>
                  <dataCollectionFlow id="coin">
                    <levels>
                      <level>
                        <items>
                          <item id="heads">
                            <label>Heads</label>
                          </item>
                          <item id="tails">
                            <label>Tails</label>
                          </item>
                        </items>
                      </level>
                    </levels>
                  </dataCollectionFlow>
                </ws.dataCollection>
              </action>
            </button>

        Please refer to :ref:`file_handler_datacollection` for more details.
        
        """


class DataCollectionMenuAction(dynButtons.Action):
    
    def getName(self):
        return 'ws.dataCollection.menu'
    
    def __getGroup(self, actionParam):
        if (hasattr(actionParam, 'getParam')):
            return actionParam.getParam('group')
        return None

    def getButtonText(self, actionParam, employee, languages):
        return _('Data Collection')
    
    def getDialog(self, actionParam, employee, languages):
        return _DataCollectionMenuDialog(employee, languages, self.__getGroup(actionParam))

    def isVisible(self, actionParam, employee, languages):
        flows = DataCollection().getAll()
        if (len(flows) <= 0):
            return False
        if (employee is None):
            return True
        # only show the menu button if there are flows available
        roles = employee.getRoles()
        group = self.__getGroup(actionParam)
        flows = filter(lambda t: t.checkRoleAndGroup(roles, group), flows)
        return (len(flows) > 0)

    def isEmployeeRequired(self, actionParam):
        return True

    def getXsd(self):
        return """
            <xs:complexType>
                <xs:all>
                    <xs:element name="group" type="xs:normalizedString" minOccurs="0" />
                </xs:all>
            </xs:complexType>
        """

    def getHelp(self):
        return """
        Show menu with all configured data collection flows.
        
        Example::
        
            <button>
                <pos>1</pos>
                <action>
                    <ws.dataCollection.menu />
                </action>
            </button>

        Optionally, it is possible to specify a data collection flow group, to only
        show flows that are in that group.
        
        Example with group::
        
            <button>
                <pos>1</pos>
                <action>
                    <ws.dataCollection.menu>
                        <group>costcenters</group>
                    </ws.dataCollection.menu>
                </action>
            </button>

        Please refer to :ref:`file_handler_datacollection` for more details.
        
        """


def loadPlugin():
    helpText = """
The data collection file handler can import and export data collection flow definitions, 
which can be used by the (:ref:`action_ws.datacollection`) and (:ref:`action_ws.datacollection.menu`)
action.
The *dataCollection.xml* file contains a list of flows. Each flow consists of a configuration 
section and levels with items. Each flow is totally independent, e.g. one flow may be used for
changing departments and another can be used to select an absence reason. Flows can not be linked
together.

Simple example *dataCollection.xml*::

  <?xml version="1.0" encoding="utf-8"?>
  <dataCollection>
    <dataCollectionFlow id="TF1">
      <config>
        <button>
          <label>Absence</label>
        </button>
      </config>
      <levels>
        <level>
          <title>Select Absence</title>
          <items>
            <item id="ABS001">
              <label>Vacation</label>
            </item>
            <item id="ABS002">
              <label>Sick</label>
            </item>
            <item id="ABS003">
              <label>Doctor</label>
            </item>
            <item id="ABS004">
              <label>Dentist</label>
            </item>
            <item id="ABS005">
              <label>On business</label>
            </item>
          </items>
          </level>
        </levels>
    </dataCollectionFlow>
  </dataCollection>
  
.. important::
    All *dataCollectionFlow*, *item* and *level* (except the first) elements must have 
    an *id* attribute. 

Text (button label, title, item label, etc) can be specified per language by using 
*text* tags. The text tags can be omitted if only one language is required.

Example::

    <item id="ABS005">
      <label>
        <text language="en">On business</text>
        <text language="de">Arbeitsreise</text>
      </label>
    </item>
    
Configuration section
~~~~~~~~~~~~~~~~~~~~~
    
The configuration section can contain information used by the :ref:`action_ws.datacollection.menu`
action for displaying a button for each flow. A label, role and group can be defined. The button
will not be placed, if the employee does not have the role specified. The button will also not be 
placed if a different group is defined for the action (see :ref:`action_ws.datacollection.menu`).

Example button configuration::

    <dataCollection>
      <dataCollectionFlow id="TF1">
        <config>
          <button>
            <label>Absence</label>
            <group>absence</group>
            <reqRole>fulltime</reqRole>
          </button>
        </config>
        [...]
      </dataCollectionFlow>
    </dataCollection>
    
The configuration section can also contain a response message, which is displayed after the transaction
was successfully sent.

Example response message configuration::

    <dataCollection>
      <dataCollectionFlow id="TF1">
        <config>
          <response>
            <message>Accepted!</message>
          </response>
        </config>
        [...]
      </dataCollectionFlow>
    </dataCollection>

In addition to the response message the configuration section can also define whether the transaction is saved
in the last clockings table allowing it to be reviewed at the terminal.

Example of last clockings review configuration::

    <dataCollection>
      <dataCollectionFlow id="TF1">
        <config>
          <response>
            <message>Accepted!</message>
          </response>
          <review>
            <type>pabs</type>
            <label>
              <text language="en">P.ABS</text>
            </label>
          </review>          
        </config>
        [...]
      </dataCollectionFlow>
    </dataCollection>


Nested levels
~~~~~~~~~~~~~

The simple example from above defines only one level with 5 items but it is
also possible to configure nested and linked levels.

With nested levels, each item can have sub-levels, so that a large selection can 
be broken down into higher level groups that can be drilled down to refine the
selection.

Example::

    <levels>
      <level>
        <items>
          <item id="item1">
            <label>Item 1</label>
            <levels>
              <level>
                <items>
                  <item id="item1-1">
                      <label>Item 1-1</label>
                  </item>
                  <item id="item1-2">
                      <label>Item 1-2</label>
                  </item>
                </items>
              </level>
            </levels>
          </item>
          <!-- more items -->
        </items>
      </level>
    </levels>

.. graphviz::
    :caption: Nested items with 3 levels.

    digraph tasks_nested {

        items1 [shape="record", label="<i1> Item 1|<i2> Item 2"];
        items2 [shape="record", label="<i11> Item 1-1|<i12> Item1-2"];
        items3 [shape="record", label="<i21> Item 2-1|<i22> Item2-2"];
        
        items1:i1:s -> items2:i11:n;
        items1:i1:s -> items2:i12:n;
        items1:i2:s -> items3:i21:n;
        items1:i2:s -> items3:i22:n;

        items4 [shape="record", label="<i111> Item 1-1-1|<i112> Item 1-1-2"];
        items5 [shape="record", label="<i121> Item 1-2-1|<i122> Item 1-1-2"];
        items6 [shape="record", label="<i211> Item 2-2-1|<i212> Item 2-1-2"];
        items7 [shape="record", label="<i221> Item 2-2-1|<i222> Item 2-2-2"];        

        items2:i11:s -> items4:i111:n;
        items2:i11:s -> items4:i112:n;        
        items2:i12:s -> items5:i121:n;
        items2:i12:s -> items5:i122:n;        
        items3:i21:s -> items6:i211:n;
        items3:i21:s -> items6:i212:n;        
        items3:i22:s -> items7:i221:n;
        items3:i22:s -> items7:i222:n;        

    }

Multi-levels or linked levels
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

With nested levels, each item defines its own sub-levels. Sometimes however, 
the next level may not depend on the previous selection. Linked levels
allow to reference a level, making it possible for many items to link to
the same sub-level.

Example::

    <levels>
      <level>
        <items>
          <item id="item1">
            <label>Item 1</label>
            <levelRef ref="level2" />
          </item>
          <item id="item2">
            <label>Item 2</label>
            <levelRef ref="level2" />
          </item>
        </items>
      </level>
      <level id="level2">
        <items>
          <item id="itemA">
            <label>Item A</label>
            <levelRef ref="level3" />
          </item>
          <item id="itemB">
            <label>Item B</label>
            <levelRef ref="level3" />
          </item>
        </items>
      </level>
      <!-- more levels -->
    </levels>



.. graphviz::
    :caption: Multi-level items with 3 levels.

    digraph tasks_linked {

        items1 [shape="record", label="<i1> Item 1|<i2> Item 2"];
        items2 [shape="record", label="<iA> Item A|<iB> Item B"];
        items3 [shape="record", label="<iC> Item α|<iD> Item β"];
        
        items1:i1 -> items2:iA;
        items1:i1 -> items2:iB;
        items1:i2 -> items2:iA;
        items1:i2 -> items2:iB;
        items2:iA -> items3:iC;
        items2:iA -> items3:iD;
        items2:iB -> items3:iC;        
        items2:iB -> items3:iD;
        
    }

Data entry
~~~~~~~~~~

An item can also define a data entry. Data entries can be used to 
ask the user for entering additional data (e.g. amount,
cost center ID, price, etc.).

A data entry defines a sequence of entry steps. The following types
of data entries are available:

 - numeric input
 - text input
 - masked text input
 - fixed text

Example for two numeric data entry steps with fixed text::

  <item id="apples">
    <label>Apples</label>
    <dataEntry>
      <fixedTextStep id="apples.text">
        <text>Apple Selection</text>
      </fixedTextStep>
      <numericEntryStep id="apples.typeid">
        <title>Enter type ID of apple</title>
      </numericEntryStep>
      <numericEntryStep id="apples.amount">
        <title>How many apples</title>
      </numericEntryStep>
    </dataEntry>
  </item>

An item with a data entry can also have further sub-levels.

These entries also permit a barcode scanner to be used. When a barcode
is scanned, it will be accepted immediately and will move to the next
data entry step. If this behaviour is not required, an autoCommit tag
can be added, with a value of 'false'.

In this example, if a barcode scanner is used the first data
entry step will immediately move to the next step. The second data
entry step, however, will allow the barcode scanner to read a number
into the edit box, but requires the user to press the Next
button to continue.

Example ::

  <item id="apples">
    <label>Apples</label>
    <dataEntry>
      <numericEntryStep id="apples.typeid">
        <title>Enter type ID of apple</title>
        <reader></reader>
      </numericEntryStep>
      <numericEntryStep id="apples.amount">
        <title>How many apples</title>
        <reader><autoCommit>false</autoCommit></reader>
      </numericEntryStep>
    </dataEntry>
  </item>


Numeric data entry steps
^^^^^^^^^^^^^^^^^^^^^^^^

Example::

  <numericEntryStep id="project.id">
    <title>Project ID</title>
    <default>1000</default>
    <min>1000</min>
    <max>9999</max>
    <allowEmpty>true</allowEmpty>
  </numericEntryStep>
  
The example above defines a numeric entry step with a default, 
minimum and maximum value and specifies that an empty input
is allowed.

Text data entry steps
^^^^^^^^^^^^^^^^^^^^^

Example::

  <item id="not-listed-project">
    <label>Project not listed</label>
    <dataEntry>
      <textEntryStep id="not-listed-project.name">
        <title>Project name</title>
        <default>Prj-</default>
        <min>3</min>
        <max>10</max>
      </textEntryStep>
    </dataEntry>
  </item>

Specifying a default or a minimum and maximum length is optional.

Masked data entry steps
^^^^^^^^^^^^^^^^^^^^^^^

Example::

  <item id="not-listed-project">
    <label>Project not listed</label>
    <dataEntry>
      <maskedEntryStep id="not-listed-project.prj-id">
        <title>Project ID</title>
        <mask>___-####</mask>
        <default>PRJ-0000</default>
      </maskedEntryStep>
    </dataEntry>
  </item>

A masked data entry step allows for a fixed length entry in which
allowed characters can be defined for each position.

The meaning of the mask characters is as follows:

  =============== =====================================
  Mask Character  Allowed Characters
  =============== =====================================    
  **#**           digits (0-9)
  **A**           alphabetic and upper case (A-Z)
  **a**           alphabetic and lower case (a-z)
  **?**           alphanumeric (a-z, A-Z, 0-9)      
  **\***          any
  **_**           none (read only)
  =============== ===================================== 

Fixed Text steps
^^^^^^^^^^^^^^^^

Example ::

  <fixedTextStep>
    <text>Site 1</text>
  </fixedTextStep>

A fixed step step does not expect user input, nor does it display
anything to the user. Instead it simply adds the contents of the
'text' element to the selection items and immediately moves on to
the next step (if any).
  
Referencing data entries
^^^^^^^^^^^^^^^^^^^^^^^^

Referencing already defined data entries can be useful if many items
within a level need to use the same data entry steps. 
In these cases, the data entry within the item only references a data entry 
by its ID. The actual data entries are defined with the level.

Example::

  <level>
    <title>Select fruit</title>
    <dataEntries>
      <dataEntry id="fruit.amount">
        <numericEntryStep id="amount">
          <title>Enter amount</title>
        </numericEntryStep>
      </dataEntry>
    </dataEntries>
    
    <items>
      <item id="fruit.apples">
        <label>Apples</label>
        <dataEntry ref="fruit.amount" />
      </item>

      <item id="fruit.bananas">
        <label>Bananas</label>
        <dataEntry ref="fruit.amount" />
      </item>

      <item id="fruit.oranges">
        <label>Oranges</label>
        <dataEntry ref="fruit.amount" />
      </item>
    </items>
  </level>

"""
    dataCollectionXsd = """<?xml version="1.0"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns="http://gtl.biz/apps/dataCollection" targetNamespace="http://gtl.biz/apps/dataCollection" elementFormDefault="qualified">

    <xs:complexType name="textType">
        <xs:simpleContent>
            <xs:extension base="xs:string">
                <xs:attribute name="language" type="xs:string" use="required" />
            </xs:extension>
        </xs:simpleContent>
    </xs:complexType>

    <xs:complexType name="languageTextType" mixed="true">
        <xs:sequence minOccurs="0" maxOccurs="unbounded">
            <xs:element name="text" type="textType" />
        </xs:sequence>
    </xs:complexType>
""" + DataCollectionAction().getXsdTypes() + """
    <xs:element name="dataCollection">
        <xs:complexType>
            <xs:sequence>
                <xs:element name="dataCollectionFlow" type="dataCollectionFlowType" maxOccurs="unbounded" />
            </xs:sequence>
        </xs:complexType>
    </xs:element>
</xs:schema> 
"""

    dynButtons.registerAction(DataCollectionAction())
    dynButtons.registerAction(DataCollectionMenuAction())
    fh = fileHandler.PersistentProjectFileHandler('dataCollection.xml', False, helpText, ('dataCollection.xsd', dataCollectionXsd))
    fileHandler.register('^data[cC]ollection.xml$', fh, 'DataCollection')

