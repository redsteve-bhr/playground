# -*- coding: utf-8 -*-
#
# Copyright 2011 Grosvenor Technology
#
import itg
import log
from engine import dynButtons
from applib.gui import msg
import webClient


class InfoRequestDialog(itg.PseudoDialog):

    def __init__(self, employee, infoTypeID, offlineOnly=False):
        super(InfoRequestDialog, self).__init__()
        self.__emp = employee
        self.__infoTypeID = infoTypeID
        self.__failMsg = None
        self.__cancelled = False
        self.__offlineOnly = offlineOnly

    def __getOnlineInfo(self):
        reqQueue = webClient.getJobQueue()
        if (reqQueue == None):
            self.__failMsg = _('Action not available at this time. Please try again later.')
            return None
        infoReq = webClient.EmployeeInfoRequest(self.__emp, self.__infoTypeID)
        uiTimeout = webClient.getJobUITimeout()
        
        itg.waitbox(_('Contacting server, please wait...'), reqQueue.addJobAndWait, (infoReq, uiTimeout), infoReq.cancel)
        #log.info('job state = %s' % infoReq.getState())
        if (infoReq.hasTimedout()):
            log.dbg('Action has timed out')
            self.__failMsg = _('Action not available.\n Please try again later')
            return None
        if (infoReq.hasFailed() or infoReq.hasTimedout()):
            reason = infoReq.getFailedReason()
            if (reason != None):
                self.__failMsg = _('Server returned an error!\n')
            else:
                self.__failMsg = _('Action not available.\n Please try again later')
            return None
        #log.info('job state = %s' % infoReq.getState())
        if (infoReq.wasCancelled()):
            log.dbg('Action was cancelled')
            self.__cancelled = True
            return None
        empInfoResponse = infoReq.getResponse()
        return empInfoResponse

    def __getOfflineInfo(self):
        tblEmpInfo = webClient.getAppEmpInfo()
        empInfoResponse = tblEmpInfo.getEmpInfo(self.__emp.getEmpID(), self.__infoTypeID)
        if (empInfoResponse == None):
            log.dbg('Employee has no offline data for %s' % self.__infoTypeID)
            self.__failMsg = _('Feature not available.\n Please try again later')
            return None
        return empInfoResponse
    
    def run(self):
        empInfoResponse = None
        if (not self.__offlineOnly):
            empInfoResponse = self.__getOnlineInfo()
            if (self.__cancelled):
                log.dbg('Request was cancelled')
                return itg.ID_CANCEL
        if (empInfoResponse == None):
            empInfoResponse = self.__getOfflineInfo()
        if (empInfoResponse != None):
            contentType = empInfoResponse.getContentType() 
            if (contentType in ('text/plain', 'text/html') and hasattr(itg, 'TextView')):
                dlg = _TextInfoHtmlDialog(contentType, empInfoResponse.getTitle(), empInfoResponse.getData())
                return dlg.run()
            elif (contentType == 'text/msg'):
                dlg = _TextInfoMsgDialog(empInfoResponse.getTitle(), empInfoResponse.getData())
                return dlg.run()
            else:
                self.__failMsg = _('Information type not supported (%s)!') % contentType

        if (self.__failMsg != None):
            res = msg.failMsg(self.__failMsg)
        else:
            res = itg.ID_OK
        return res
            

class _TextInfoMsgDialog(itg.Dialog):

    def __init__(self, title, data):
        super(_TextInfoMsgDialog, self).__init__()
        view = itg.MsgBoxView()
        view.setText('\n'.join([title, data]))
        view.setButton(0, _('OK'), itg.ID_OK, self.quit)
        self.addView(view)


class _TextInfoHtmlDialog(itg.Dialog):
    
    def __init__(self, mimeType, title, data):
        super(_TextInfoHtmlDialog, self).__init__()
        view = itg.TextView(title, data, mimeType)
        view.setButton(_('OK'), itg.ID_OK, self.quit)
        self.addView(view)


#
#
# Support functions for dynamic buttons
#
#

class EmpInfoOnlineAction(dynButtons.Action):
    
    def getName(self):
        return 'ws.emp.info.online'
    
    def getButtonText(self, actionParam, employee, languages):
        return _('Action %s') % actionParam
    
    def getDialog(self, actionParam, employee, languages):
        ele = actionParam.getXMLElement('infoType')
        if (ele != None):
            infoTypeID = ele.text
        else:
            log.err('The infoType must be specified in the xml!')
            return None
        return InfoRequestDialog(employee, infoTypeID)

    def isEmployeeRequired(self, actionParam):
        return True
    
    def getXsd(self):
        return """
            <xs:complexType>
                <xs:all>
                    <xs:element name="infoType" type="xs:normalizedString" />
                </xs:all>
            </xs:complexType>
        """    
    
    def getHelp(self):
        return """
        Request and show real time information from server. What kind
        of information is specified by the infoType.
        
        Example with infoType set to balance::
        
            <button>
                <pos>1</pos>
                <label>Balance</label>
                <action>
                    <ws.emp.info.online>
                        <infoType>balance</infoType>
                    </ws.emp.info.online>
                </action>
            </button>        
        
        """

class EmpInfoOfflineAction(dynButtons.Action):
    
    def getName(self):
        return 'ws.emp.info.offline'
    
    def getButtonText(self, actionParam, employee, languages):
        return _('Action %s') % actionParam
    
    def getDialog(self, actionParam, employee, languages):
        ele = actionParam.getXMLElement('infoType')
        if (ele != None):
            infoTypeID = ele.text
        else:
            log.err('The infoType must be specified in the xml!')
            return None
        return InfoRequestDialog(employee, infoTypeID, offlineOnly=True)

    def isEmployeeRequired(self, actionParam):
        return True
    
    def getXsd(self):
        return """
            <xs:complexType>
                <xs:all>
                    <xs:element name="infoType" type="xs:normalizedString" />
                </xs:all>
            </xs:complexType>
        """    
    
    def getHelp(self):
        return """
        Show offline information previously down loaded from the server. The kind
        of information is specified by the infoType.
        
        Example with infoType set to balance::
        
            <button>
                <pos>1</pos>
                <label>Balance</label>
                <action>
                    <ws.emp.info.offline>
                        <infoType>balance</infoType>
                    </ws.emp.info.offline>
                </action>
            </button>        
        
        """



def loadPlugin():
    dynButtons.registerAction(EmpInfoOnlineAction())
    dynButtons.registerAction(EmpInfoOfflineAction())

