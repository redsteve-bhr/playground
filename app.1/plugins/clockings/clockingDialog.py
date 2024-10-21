# -*- coding: utf-8 -*-
#
# Copyright 2011 Grosvenor Technology
#
import datetime
import itg
import log
import xml.etree.cElementTree as ET
from applib.db import sqlTime
from applib.gui import msg
from applib.utils import crashReport, restartManager, relayManager
from engine import acceptMsgDlg
import plugins


import webClient
import tblAntipassback
import tblLastClockings
import lastClockingsData
import punchRestrictionsWizardDialog
            

class ClockingDialog(itg.PseudoDialog):
    
    def __init__(self, clocking, employee):
        super(ClockingDialog, self).__init__()
        self._clocking = clocking
        self._emp      = employee
        if (clocking.isOnlineClocking()):
            self._preClockingSteps  = [checkSystemTime,
                                       relayTrigger,
                                       antipassbackCheck,
                                       checkRestrictions,
                                       dataCollectionFlow,
                                       clockingPost ]
            self._postClockingSteps = [antipassbackSave, 
                                       lastClockingsSave,
                                       clockingResponse ]
        else:
            self._preClockingSteps  = [checkSystemTime,
                                       relayTrigger,
                                       antipassbackCheck,
                                       checkRestrictions,
                                       dataCollectionFlow,
                                       clockingCommit ]
            self._postClockingSteps = [antipassbackSave, 
                                       lastClockingsSave,
                                       clockingResponse ]

    
    def run(self):
        with restartManager.PreventRestartLock():
            # check clocking is ok and set time
            if (self._clocking == None or not self._clocking.getType()):
                log.err('Clocking type not set!')
                itg.msgbox(itg.MB_OK, _('Clocking configuration error!'))
                return
            self._clocking.setTime(sqlTime.getSqlTimestampNow())
            # run pre-clocking steps
            try:
                for step in self._preClockingSteps:
                    result = step(self._emp, self._clocking)
                    if (result == False):
                        log.warn('Clocking step returned False, please change to return itg.ID!')
                        return itg.ID_CANCEL
                    elif (result not in (None, True, itg.ID_OK, itg.ID_NEXT)):
                        return result
            except Exception as e:
                log.err('Clocking error: %s' % e)
                msg.failMsg(_('Clocking error: %s') % e)
                return itg.ID_CANCEL
            # run post-clocking steps
            for step in self._postClockingSteps:
                try:
                    step(self._emp, self._clocking)
                except Exception as e:
                    log.err('Post clocking step error: %s' % e)
                    crashReport.createCrashReportFromException()
            return itg.ID_OK
    

            
def clockingPost(emp, clocking):
    if clocking.getIsSent():
        return itg.ID_OK
    # create job
    clockingTag = clocking.getClockingTag()
    actionType = clocking.getActionType()
    if clockingTag.find('time') is None:
        if actionType is not None:
            ET.SubElement(clockingTag, 'actionType').text = actionType
        ET.SubElement(clockingTag, 'time').text = sqlTime.sqlTime2MyLocalTime(clocking.getTime(), '%Y-%m-%dT%H:%M:%S%z')
    
    responseText = clocking.getResponseText(emp.getLanguages())
    if responseText is None or responseText.strip() == "":
        responseText = "Booking accepted"
    job = webClient.OnlineTransactionJob(clockingTag, emp, responseText=responseText)
    # get queue and check if busy
    queue = webClient.getJobQueue()
    if (queue.isBusy()):
        errMsg = 'server not available'
    else:
        itg.waitbox(_("Contacting server"), queue.addJobAndWait, (job, clocking.getTimeout()))
        if (job.hasFinished()):
            if (job.hasFailIndicator()):
                msg.failMsg(job.getResponseText())
                return itg.ID_CANCEL
            # store response
            clocking.setOnlineResponseText(job.getResponseText())
            return itg.ID_OK
        elif (job.hasTimedout()):
            errMsg = 'timeout'
        else:
            errMsg = job.getFailedReason()
        
    # sending clocking did not work or queue busy
    if (clocking.isOnlineOnly()):
        raise Exception(errMsg)
    else:
        try:
            # send transaction offline
            job.commitTransaction()
        except Exception as e:
            msg.failMsg("Failed to store transaction: " % e)
            log.err("Failed to store transaction: " % e)
    

def clockingCommit(emp, clocking):
    """ Create clocking transaction. """        
    if clocking.getIsSent():
        return itg.ID_OK
    transactions = webClient.getAppTransactions()
    if (not transactions.hasSpace()):
        raise Exception(_('Transaction buffer full!'))
    clockingTag = clocking.getClockingTag()
    actionType = clocking.getActionType()
    if clockingTag.find('time') is None:
        if actionType is not None:
            ET.SubElement(clockingTag, 'actionType').text = actionType
        if not clocking.isOnlineClocking():
            ET.SubElement(clockingTag, 'offline');
        ET.SubElement(clockingTag, 'time').text = sqlTime.sqlTime2MyLocalTime(clocking.getTime(), '%Y-%m-%dT%H:%M:%S%z')
    transactions.addTransaction(clockingTag, emp)

def clockingResponse(emp, clocking):
    """ Show clocking response. """
    response = clocking.getOnlineResponseText()
    if (not response):
        response = '%s\n%s' % (emp.getName(), clocking.getResponseText(emp.getLanguages()) or 'clocked')
    acceptMsgDlg.acceptMsg(response, acceptReader=True, soundFile=clocking.getResponseSoundFile(emp.getLanguages()))

def relayTrigger(emp, clocking):
    """ Trigger relay, if configured. """
    (ioBoard, relay, duration) = clocking.getRelayTrigger()
    if (duration > 0):
        try:
            relayManager.setRelayOn(ioBoard, relay, duration)
        except Exception as e:
            log.err('Failed to trigger relay: %s' % (e,))

def checkSystemTime(emp, clocking):
    """Check the transaction time is not in the past"""
    clkTime = datetime.datetime.strptime(clocking.getTime(), sqlTime.sqlTimeFormat)
    if (clkTime.date().year < 2023):
        log.err('Clocking time %s is before 2023' % clocking.getTime())
        # TODO: the translation needs to be sorted and the Spanish below split out.
        msg.failMsg(_('Clocking not accepted.\nConfiguration is invalid, please see supervisor.\n\nNo se acepta transacción.\nLa configuración no es válida, consulte al supervisor'))
        return itg.ID_CANCEL
    return True


def antipassbackCheck(emp, clocking):
    """ Check antipassback and fail if necessary. """
    (apTime, apNode) = clocking.getApTimeAndNode()
    if (apTime != None and apNode != None):
        antipassback = tblAntipassback.getAppAntipassback()
        # check if already clocked
        if (not antipassback.check(clocking.getTime(), emp.getEmpID(), apNode)):
            msg.failMsg(_('Already clocked within last %s seconds.') % apTime)
            return itg.ID_CANCEL
    return True

def antipassbackSave(emp, clocking):
    """ Save clocking information for antipassback. """
    (apTime, apNode) = clocking.getApTimeAndNode()
    if (apTime != None and apNode != None):
        antipassback = tblAntipassback.getAppAntipassback()
        antipassback.save(clocking.getTime(), emp.getEmpID(), apNode, apTime)

def lastClockingsSave(emp, clocking):
    """ Save clocking for last clockings/review feature. """
    lastClockings = tblLastClockings.getAppLastClocking()
    if (emp.getUsedVerificationMethod() == 'cam') and  (emp.getVerifyPhoto() != None):
        dataID = lastClockingsData.writeClockingDataToUSB('image/jpeg', clocking.getTime(), emp.getEmpID(), emp.getVerifyPhoto())
    elif (emp.getUsedVerificationMethod() == 'voice') and (emp.getVerifyVoice() != None):
        dataID = lastClockingsData.writeClockingDataToUSB('audio/x-wav', clocking.getTime(), emp.getEmpID(), emp.getVerifyVoice())
    else:
        dataID = None
    lastClockings.add(clocking.getType(), clocking.getTime(), emp.getEmpID(), dataID, clocking.getMultiLanguageReviewText())

def dataCollectionFlow(emp, clocking):
    """ Handle data collection if specified. """
    flow = clocking.getDataCollectionFlow(emp)
    if (flow == None):
        return itg.ID_OK
    dlg = plugins.dataCollection.DataCollectionFlowDialog(emp.getLanguages(), flow.getLevels())
    resID = dlg.run()
    if (resID in (itg.ID_OK, itg.ID_NEXT)):
        resultTag = dlg.getDataCollectionResult(actionType=clocking.getActionType())
        clocking.getClockingTag().append(resultTag)
        return itg.ID_OK
    return resID

def checkRestrictions(emp, clocking):
    """If required, display the PunchRestrictions wizard dialog to go through
    the Punch Restriction Check process.
    """
    if clocking.getRestrictions().enabled:
        dlg = punchRestrictionsWizardDialog.PunchRestrictionsWizardDialog(emp, clocking)
        resID = dlg.run()
    else:
        resID = itg.ID_OK
    return resID
