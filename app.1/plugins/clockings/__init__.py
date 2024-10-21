# -*- coding: utf-8 -*-
#
# Copyright 2011 Grosvenor Technology
#

import xml.etree.cElementTree as ET
from applib.utils import timeUtils
from applib.db.tblSettings import getAppSetting
from engine import dynButtons, fileHandler
from plugins import dataCollection
import clockingDialog
import lastClockingsDialog
from clearClockings import ClearClockingsAction
from resendClockings import ResendClockingsAction
import log
from miscUtils import getElementText
from webClient import transaction

class _Clocking(object):

    def __init__(self, clkType, param=None):
        self.__param = param
        self.__clkType = clkType
        self.__clkTime = None
        self.__onlineResponseText = None
        self.__isSent = False
        self.__clockingTag = ET.Element('clocking')
        ET.SubElement(self.__clockingTag, 'type').text = self.__clkType
        self.__restrictions = Restrictions()
        if self.__param is not None:
            self.__restrictions.parse(self.__param)

    def getType(self):
        """ Return clocking type. """
        return self.__clkType
    
    def getActionType(self):
        """ Return the action type.
        
        This value is not used by the application. It is simply retrieved from the
        action XML if it exists and will be passed unchanged to the booking web
        service.
        
        If no actionType is specified in the XML, None will be returned.
        """
        result = None
        if self.__param is not None:
            element = self.__param.getXMLElement('actionType') 
            if element is not None:
                result = element.text
        return result
                
    def getClockingTag(self):
        """ Return clocking tag used for holding all clocking related
            data for transaction.
        """
        return self.__clockingTag
    
    def setTime(self, clkTime):
        """ Set time of clocking. """
        self.__clkTime = clkTime
        
    def getTime(self):
        """ Return time of clocking. """
        return self.__clkTime
    
    def getApTimeAndNode(self):
        """ Return antipassback time and node (or None, None). """
        if (not self.__param):
            return (None, None)
        return (self.__param.getInteger('antipassback/time', None), 
                self.__param.getInteger('antipassback/node', None))

    def getResponseText(self, languages):
        """ Return response text for language. """
        if (not self.__param):
            return None
        text = self.__param.getText('clockingConfirmation/response', languages)
        if text is None:
            # Fall-back to old version
            text = self.__param.getText('response', languages)
            if text is not None:
                log.warn('Deprecated "response" element found, please migrate to new "clockingConfirmation" element')
        return text

    def isOnlineClocking(self):
        """ Return *True* if online clocking. """
        if (not self.__param):
            return False
        return (self.__param.getXMLElement('online') != None)
        
    def isOnlineOnly(self):
        """ Return *True* if online only clocking. """
        if (not self.__param):
            return False
        return self.__param.getBoolean('online/onlineOnly', False)
        
    def getTimeout(self):
        """ Return timeout (e.g. used for online clockings). """
        if (not self.__param):
            return False
        return self.__param.getInteger('online/timeout', 5)
        
    def setOnlineResponseText(self, response):
        """ Set response text for offline clocking. """
        self.__onlineResponseText = response

    def getOnlineResponseText(self):
        """ Get online response text or None. """
        return self.__onlineResponseText

    def getMultiLanguageReviewText(self):
        """ Return multi-language dictionary with review text. """
        if (not self.__param):
            return {}
        return self.__param.getMultiLanguageText('review')
    
    def getResponseSoundFile(self, languages):
        """ Return response sound file (for language). """
        if (not self.__param):
            return None
        return self.__param.getSound('responseSound', languages)

    def getRelayTrigger(self):
        """ Return tuple with ioBoard, relay and duration. """
        if (not self.__param):
            return (0, 0, -1)
        return (self.__param.getInteger('relay/ioboard', 1)-1,
                self.__param.getInteger('relay/relayNumber', 1)-1,
                self.__param.getFloat('relay/duration', -1))

    def getDataCollectionFlow(self, emp):
        if (not self.__param):
            return None
        if (self.__param.getXMLElement('dataCollection') == None):
            return None
        try:
            flowXml = self.__param.getXMLElement('dataCollection/dataCollectionFlow')
            if (flowXml != None):
                flow = dataCollection.DataCollectionFlow(flowXml)
            else:
                flowId = self.__param.getParam('dataCollection/id')
                flow = dataCollection.DataCollection().getById(flowId)
        except Exception as e:
            log.err('Error parsing data collection parameter: %s' % e)
            return None
        if (flow != None):
            if not dynButtons.hasRequiredRole(emp.getRoles(), flow.getReqRole()):
                return None
        return flow

    def getPromptLevels(self):
        if not self.__param:
            return set()

        if hasattr(self.__param, 'getList'):
            return set(self.__param.getList('transfer/promptLevel'))
        else:
            return set()
    
    def requireTimecardApproval(self):
        if self.__param is None:
            return False
        return (self.__param.getXMLElement('timecard') is not None)
    
    def requireTransfer(self):
        if self.__param is None:
            return False
        return (self.__param.getXMLElement('transfer') is not None)
    
    def getRestrictions(self):
        return self.__restrictions
    
    def checkSupervisorOverride(self):
        return (self.__param.getXMLElement('checkSupervisorOverride') is not None)
    
    def getEarlyStartMins(self):
        if self.__param is None:
            return 0
        return self.__restrictions.earlyStartMins
    
    def getLateEndMins(self):
        if self.__param is None:
            return 0
        return self.__restrictions.lateEndMins

    def checkLastPunch(self):
        if self.__param is None:
            return False
        return self.__restrictions.checkLastClocking
    
    def getMinimumElapsedMinutes(self):
        if self.__param is None:
            return 0
        return self.__restrictions.minimumElapsedMinutes
    
    def getLastPunchTime(self):
        if self.__param is None:
            return ''
        return self.__restrictions.lastPunch.punchTime

    def getLastPunchType(self):
        if self.__param is None:
            return ''
        return self.__restrictions.lastPunch.punchType

    def getIsSent(self):
        return self.__isSent

    def setIsSent(self, value):
        self.__isSent = value
        
    def getTransaction(self, emp, clockingTimeStr=None):
        # Build the transaction XML from the clocking tag
        clockingTag = self.getClockingTag()
        actionType = self.getActionType()
        if clockingTimeStr is None:
            clockingTimeStr = timeUtils.getXMLTimestampNow()
        # If necessary, add the required transaction elements
        if actionType is not None:
            if clockingTag.find('actionType') is None:
                ET.SubElement(clockingTag, 'actionType').text = actionType

        if clockingTag.find('time') is None:
            ET.SubElement(clockingTag, 'time').text = clockingTimeStr
        transactionXmlStr = transaction.createTransactionData(getAppSetting('clksrv_id'), self.getClockingTag(), emp)
        return transactionXmlStr
        

class Restrictions(object):
    """Class to parse and store details of the restrictions element from
    buttons.xml.

    Example:

        <button>
            <action>
                <ws.clocking>
                    <restrictions>
                        <checkHealthAttest>true</checkHealthAttest>
                        <checkSupervisorOverride>true</checkSupervisorOverride>
                        <online>
                            <checkSchedules>
                                <strict>true</strict>
                            </checkSchedules>
                            <checkLastClocking>
                                <minimumElapsedMinutes>0</minimumElapsedMinutes>
                                <type>IN</type>
                            </checkLastClocking>
                            <onlineOnly>true</onlineOnly>
                        </online>
                        <offline>
                            <checkSchedules>
                                <strict>false</strict>
                            </checkSchedules>
                        </offline>
                        <dialogTimeout>30</dialogTimeout>
                        <earlyStartMins>0</earlyStartMins>
                        <lateEndMins>0</lateEndMins>
                    </restrictions>
                </ws.clocking>
            </action> 
        </button>
    """

    def __init__(self):
        self.reset()

    def reset(self):
        self.enabled = False
        self.checkHealthAttest = False
        self.checkSupervisorOverride = False
        self.checkSchedules = False
        self.checkLastClocking = False
        self.minimumElapsedMinutes = 0
        self.lastClockingType = 'IN'
        self.hasOnlineElement = False
        self.hasOfflineElement = False
        self.onlineOnly = False
        self.strictOnlineScheduleCheck = False
        self.strictOfflineScheduleCheck = False
        self.dialogTimeout = 30
        self.earlyStartMins = 0
        self.lateEndMins = 0

    def parse(self, actionParam):
        """Parses the supplied actionParam, which is expected to be an XML
        (ElementTree) object, with `action` as the top-level element.
        """
        self.reset()
        if actionParam.getXMLElement().tag != 'ws.clocking':
            log.err('Invalid action element. Expected `ws.clocking` but got `{}`'.format(actionParam.tag))
            return

        element = actionParam.getXMLElement('restrictions')
        if element is None:
            log.warn('No `restrictions` tag found in action element')
            return
        
        self.hasOnlineElement = element.find('online') is not None
        self.hasOfflineElement = element.find('offline') is not None
        self.checkSchedules = element.find('online/checkSchedules') is not None or element.find('offline/checkSchedules') is not None
        self.checkHealthAttest = element.find('online/checkHealthAttest') is not None
        self.checkSupervisorOverride = element.find('online/checkSupervisorOverride') is not None
        self.strictOnlineScheduleCheck = getElementText(element, 'online/checkSchedules/strict', 'false').lower() == 'true' 
        self.strictOfflineScheduleCheck = getElementText(element, 'offline/checkSchedules/strict', 'false').lower() == 'true'
        self.checkLastClocking = element.find('online/checkLastClocking') is not None
        self.minimumElapsedMinutes = int(getElementText(element, 'online/checkLastClocking/minimumElapsedMins', '0'))
        self.lastClockingType = getElementText(element, 'online/checkLastClocking/type', '*')
        self.onlineOnly = getElementText(element, 'online/onlineOnly', 'false').lower() == 'true'
        self.dialogTimeout = int(getElementText(element, 'dialogTimeout', '0'))
        self.earlyStartMins = int(getElementText(element, 'earlyStartMins', '0'))
        self.lateEndMins = int(getElementText(element, 'lateEndMins', '0'))
        
        self.enabled = True

class ClockingAction(dynButtons.Action):
    
    def getName(self):
        return 'ws.clocking'
    
    def getButtonText(self, clocking, employee, languages):
        return 'Clock'

    def getDialog(self, actionParam, employee, languages):
        if (hasattr(actionParam, 'getParam')):
            clocking = _Clocking(actionParam.getParam('type'), actionParam)
        else:
            clocking = _Clocking(actionParam)
        return clockingDialog.ClockingDialog(clocking, employee)

    def isEmployeeRequired(self, actionParam):
        return True

    def getXsd(self):
        return """
            <xs:complexType>
                <xs:all>
                    <xs:element name="type" type="xs:normalizedString" />
                    <xs:element name="response" type="languageTextType" />
                    <xs:element name="review" type="languageTextType" />
                    <xs:element name="antipassback" minOccurs="0">
                        <xs:complexType>
                            <xs:all>
                                <xs:element name="time" type="xs:integer" />
                                <xs:element name="node" type="xs:integer" />
                            </xs:all>
                        </xs:complexType>
                    </xs:element>
                    <xs:element name="responseSound" minOccurs="0" type="soundType" />
                    <xs:element name="relay" minOccurs="0" >
                        <xs:complexType>
                            <xs:all>
                                <xs:element name="ioboard" type="xs:integer" />
                                <xs:element name="relayNumber" type="xs:integer" />
                                <xs:element name="duration" type="xs:decimal" />
                            </xs:all>
                        </xs:complexType>
                    </xs:element>
                    <xs:element name="online" minOccurs="0" >
                        <xs:complexType>
                            <xs:all>
                                <xs:element name="timeout" type="xs:integer" />
                                <xs:element name="onlineOnly" type="xs:boolean" />
                            </xs:all>
                        </xs:complexType>
                    </xs:element>
                    <xs:element name="dataCollection" minOccurs="0" >
                        <xs:complexType>
                            <xs:all>
                                <xs:element name="id" type="xs:normalizedString" minOccurs="0" />
                                <xs:element name="actionType" type="xs:normalizedString" minOccurs="0"/>
                                <xs:element name="dataCollectionFlow" type="dataCollectionFlowType" minOccurs="0" />
                            </xs:all>
                        </xs:complexType>
                    </xs:element>
                </xs:all>
            </xs:complexType>
        """

    def getHelp(self):
        return """
        Clock employee.

        A clocking consists of the following parts:
        
         - Check antipassback (if enabled).
         - Create clocking transaction.
         - Save clocking information for clocking.lastclockings.
         - Show response message to user.
        
        A clocking is configured by the action parameter::
        
            <button>
                <pos>1</pos>
                <label>
                    <text language="en">Clock IN</text>
                    <text language="de">Einbuchen</text>
                </label>
                <action>
                    <ws.clocking>
                        <type>in</type>
                        <response>
                            <text language="en">clocked in</text>
                            <text language="de">eingebucht</text>                            
                        </response>
                        <review>
                            <text language="en">In</text>
                            <text language="de">eingebucht</text>
                        </review>
                        <antipassback>
                            <node>1</node>
                            <time>90</time>
                        </antipassback>
                    </ws.clocking>
                </action>
            </button>

        The *type* parameter is used inside the transaction data to identify
        a clocking. The *response* text is shown at the end of the clocking.
        The *review* text is used for *clocking.lastclockings* or 
        *emp.options.menu*.
        
        A clocking can be configured to use an online message to show a
        message returned from the server in real time. An *online* element
        needs to be added to the *ws.clocking* element to configure an online 
        clocking::
        
            <online>
              <timeout>5</timeout>
              <onlineOnly>true</onlineOnly>
            </online>

        The optional *timeout* parameter specifies the number of seconds to wait 
        for a server response (default is 5s). The optional *onlineOnly* parameter
        does not revert back to offline clocking when set. 
        
        The *antipassback* parameters are optional. But if supplied, a clocking
        is denied if there was another clocking with the same node within the
        given time (in seconds).

        In addition to the *response* text, the terminal can be configured to 
        play a sound file when a clocking was sent (e.g. *response* text is shown).

        Example::
        
          <responseSound>
            <sound language="en">welcome_en.wav</sound>
            <sound language="de">welcome_de.wav</sound>
          </responseSound>

        The *sound* element can be omitted, if the sound is not language specific, e.g.::
        
          <responseSound>welcome.wav</responseSound>

        The sound files are located within the application media (see :ref:`media_resources` 
        for a list of media files). It is also possible to specify the sound by inserting a base64
        encoded sound file::
        
          <responseSound>
              BASE64-WAV-FILE
          </responseSound>
        
        Another optional feature is to trigger a relay on an IO board when a clocking is made.
        
        Example::
        
          <relay>
            <ioboard>1</ioboard>
            <relayNumber>1</relayNumber>
            <duration>10</duration>
          </relay>
        
        The example configures the action to activate the first relay on the first IO board for 10 
        seconds. 
        
        Clocking with data collection
        -----------------------------
        
        It is also possible to execute a data collection flow within a clocking::

          <ws.clocking>
            <type>IN</type>
            <response>Clocking accepted</response>
            <dataCollection>
              <id>flow-id</id>
            </dataCollection>
          </ws.clocking>

        The example above is specifying a flow ID to be used but it is also possible to
        define the flow within the action (see :ref:`action_ws.dataCollection`).
        
        """


class LastClockingsAction(dynButtons.Action):
    
    def getName(self):
        return 'clocking.lastclockings'
    
    def getButtonText(self, actionParam, employee, languages):
        return _('Last Clockings')
    
    def getDialog(self, actionParam, employee, languages):
        timeFormat = None
        if (hasattr(actionParam, 'getText')):        
            timeFormat = actionParam.getText('timeFormat', languages)
        return lastClockingsDialog.Dialog(_('Last clockings on this terminal'), employee.getEmpID(), timeFormat, languages)

    def isEmployeeRequired(self, actionParam):
        return True

    def getXsd(self):
        return """
            <xs:complexType>
                <xs:all>
                    <xs:element name="timeFormat" minOccurs="0" type="xs:normalizedString" />
                </xs:all>
            </xs:complexType>
        """

    def getHelp(self):
        return """
        Show last clockings made on this terminal. The review text from 
        the clocking action configuration is used to show the type of
        clocking. 
        
        Example::
        
            <button>
              <pos>1</pos>
              <action>
                <clocking.lastclockings />
              </action>
            </button>
   
        
        The default time and date format can be changed by
        specifying a *timeFormat* action parameter (default is
        '%x %X').
          
        Example with time and date format::
        
            <button>
              <pos>1</pos>
              <action>
                <clocking.lastclockings>
                    <timeFormat>%d/%m/%Y %H:%M</timeFormat>
                </clocking.lastclockings>
              </action>
            </button>
   

        """

class ClockingsReviewAction(LastClockingsAction):
    
    def getName(self):
        return 'clocking.review'
    
    def getButtonText(self, actionParam, employee, languages):
        return _('Review')
    
    def getHelp(self):
        return """
        Show last clockings made on this terminal. This is the same as 
        *clocking.lastclockings* but with 'Review' as default label 
        text instead 'Last clockings'.


        Example::
        
            <button>
              <pos>1</pos>
              <action>
                <clocking.review />
              </action>
            </button>
   

        """


def loadPlugin():
    dynButtons.registerAction(ClockingAction())
    dynButtons.registerAction(LastClockingsAction())
    dynButtons.registerAction(ClockingsReviewAction())
    dynButtons.registerAction(ResendClockingsAction())
    dynButtons.registerAction(ClearClockingsAction())

