# -*- coding: utf-8 -*-
#
# Copyright 2023 Grosvenor Technology
#
import base64
import datetime
import itg
from applib.db import sqlTime
from consentManager import ConsentStatus, ConsentConfig, ConsentMessages
import emps
import updateit
import gtmetrics
   
class ConsentDialog(itg.WizardDialog):
    
    def __init__(self, html, employee, timeout = 30, overrideStatus = None, forEnrol = False):
        
        super(ConsentDialog, self).__init__()
        
        self.html = html
        self.employee = employee
        self.overrideStatus = overrideStatus
        self.forEnrol = forEnrol
        
        # See if IT51 or IT71
        terminalType = updateit.get_type().lower()[0:4]
        if terminalType != "it51" and terminalType != "it71":
            text_segments = self.segmentTextBlock(self.html)
        else:
            text_segments = [self.html]
        
        self.data = {
            "html": self.html,
            "consentPages": text_segments,
            "consentStatus": ConsentStatus.PENDING,
            "isSkipped": False
        }
        
    def run(self):
        
        self.pages = []
        
        # Add initial dialog
        self.pages.append(_InitialPageDialog(html="In order to use biometric data you must first read and accept the following terms and conditions.", employee=self.employee, overrideStatus = self.overrideStatus, forEnrol = self.forEnrol))

        for consentPage in self.data["consentPages"]:        
            self.pages.append(_ConsentPageDialog(consentPage, employee=self.employee))

        self.pages.append(_ConsentConfirmDialog(employee=self.employee))

        # Apply shared dictionary (self.data)
        for p in self.pages:
            p.data = self.data
            
        # Run wizard
        self._runWizard(self.pages)
        resID = self.getResultID()
        # Check result, including ID_UNKNOWN (this will be returned if ALL the pages were skipped)
        if (resID in (itg.ID_OK, itg.ID_NEXT, itg.ID_UNKNOWN)):
            resID = itg.ID_OK
        return resID
    
    def segmentTextBlock(self, text, max_len=284):
        text = text.replace("\n", " ").replace("\r", " ")
        words = text.split(' ')
        
        segments = []
        current_segment = []
    
        current_length = 0
        
        for word in words:
            word_length = len(word)
            
            # If words are 4chars or longer, treat as though they are approx. 25% bigger than they are to account for wider chars. Optimised for fast running.
            k_word_length = word_length + (word_length>>2)
    
            if current_length + len(current_segment) + k_word_length <= max_len:
                current_segment.append(word)
                current_length += k_word_length
            else:
                segments.append(" ".join(current_segment))
                current_segment = [word]
                current_length = k_word_length
    
        if current_segment:
            segments.append(" ".join(current_segment))
    
        # If the last segment is too small (less than 9 words), re-run with a shorter max length to more evenly spread segments.
        while(segments[-1].count(" ") < 8): # Increase the decimal here to make the final page longer.
            segments = self.segmentTextBlock(text, max_len-32)  # Theoretically possible to go negative after 8 tries. Usually successful in under 4.
        
        return segments
        
    def getConsentStatus(self):
        """ Return accepted/declined status"""            
        return self.data["consentStatus"]
    
class _BasePageDialog(itg.Dialog):
    
    def __init__(self, employee):
        super(_BasePageDialog, self).__init__()
        self.employee = employee

    def skip(self):
        if self.data["isSkipped"]:
            return True
        else:
            return False
        
    def onTimeout(self):
        self.data["consentStatus"] = ConsentStatus.TIMEDOUT
        self.sendConsentStatus()
        self.quit(itg.ID_CANCEL)

    def onCancel(self, btn):
        if self.data["consentStatus"] != ConsentStatus.EXPIRED:
            self.data["consentStatus"] = ConsentStatus.CANCELLED
        self.sendConsentStatus()
        self.quit(itg.ID_CANCEL)

    def sendConsentStatus(self):

        consents = self.employee.getConsents()
        self.html = self.data['html']
        
        if self.data["consentStatus"] == ConsentStatus.ENROLLED or self.data["consentStatus"] == ConsentStatus.RENEWED:
            # Send full templates + consent
            timeNow = datetime.datetime.utcnow()
            timeNowTimeStamp = sqlTime.sqlTime2MyLocalTime(sqlTime.getSqlTimestampNow(), '%Y-%m-%dT%H:%M:%S%z')
            
            # Calculate the expiry date, based on the Consents Configuration
            expiryDays = ConsentConfig().getExpiryTimeInDays()
            delta = datetime.timedelta(days=expiryDays)
            expiryTime = timeNow + delta
            
            # Jump through some hoops to get a date/time string with time+offset
            expiryTimeStr = expiryTime.strftime('%Y-%m-%d %H:%M:%S%z')
            expiryTimeStamp = sqlTime.sqlTime2MyLocalTime(expiryTimeStr, '%Y-%m-%dT%H:%M:%S%z')
            
            # Store the consent
            consents.add(timeNowTimeStamp, expiryTimeStamp, self.data["consentStatus"], self.html)

            # If we are coming here via the Enrol dialog, the template data 
            # will be sent by the Enrol dialog itself once the user has fully 
            # enrolled. We just need to save the consents to the Employee so 
            # that they will be picked up when the templates are sent.
            self.employee.setConsents(consents)
            
            # If we are coming here from anywhere other than the Profile 
            # Enrolment dialog, we must send the data now.
            if not self.forEnrol:
                # templates = emps.getAppEmps().getTemplateRepository().getTemplates(self.employee.getEmpID())
                fingers = emps.getAppEmps().getTemplateRepository().getFingers(self.employee.getEmpID())
                # The setFingers() function will attach the new consents
                # to the templates and send them.
                try:
                    self.employee.setFingers(fingers)
                except Exception as e:
                    itg.msgbox(itg.MB_OK, str(e))
            
        else:
            # Send consent only
            empId = self.employee.getEmpID()
            status = self.data["consentStatus"]
            message = None

            if status == ConsentStatus.DECLINED or status == ConsentStatus.EXPIRED:
                # Delete consents and templates
                consents.clear()
                self.employee.setConsents(consents)
                emps.getAppEmps().getTemplateRepository().deleteTemplates(self.employee.getEmpID())

            consent = consents.getActiveConsent()
            if consent:
                consent.consentText = self.html
                consentStr = consent.asJSONStr()
            else:
                consentStr = ''

            base64ConsentData = base64.b64encode(consentStr)
            if status == ConsentStatus.CANCELLED: 
                message = ConsentMessages.fingerConsentCancelled(empId, base64ConsentData)
            elif status == ConsentStatus.DECLINED:
                message = ConsentMessages.declineFinger(empId, base64ConsentData)
            elif status == ConsentStatus.DEFERRED:
                message = ConsentMessages.deferFingerRenewal(empId, base64ConsentData)
            elif status == ConsentStatus.TIMEDOUT:
                message = ConsentMessages.fingerConsentTimedOut(empId, base64ConsentData)
            elif status == ConsentStatus.EXPIRED:
                gtmetrics.gtEvent(gtmetrics.EVT_FINGER_CONSENT_EXPIRED)
            
            if message:    
                consents.queueConsentData(empId, message)

class _InitialPageDialog(_BasePageDialog):
    # Cancel, Next, Skip (Optional - only if status == EXPIRING)
    def __init__(self, html, employee, timeout = 30, overrideStatus = None, forEnrol = False):
        super(_InitialPageDialog, self).__init__(employee)
        self.html = html
        self.forEnrol = forEnrol
        displayHtml = html
        consents = employee.getConsents()
        if overrideStatus is not None:
            status = overrideStatus
        else:
            status = consents.getStatus()
        self.forRenewal = (consents.count() > 0)
        view = itg.MsgBoxView()
        
        if status == ConsentStatus.EXPIRING:
            displayHtml = "Consent is expiring\n" + html
            view.setButton(0,_('Next'), itg.ID_OK, cb=self.quit)
            view.setButton(1,_('Cancel'), itg.ID_CANCEL, cb=self.onCancel)
            view.setButton(2,_('Skip'), itg.ID_IGNORE, cb=self.__onSkip)
            self._countdownBtn = 0
            self._countdownLabel = _('Skip (%s)')
        elif status in [ConsentStatus.EXPIRED]:
            displayHtml = "Consent not available.\n\nYou must re-enrol before continuing."
            view.setButton(0,_('Ok'), itg.ID_CANCEL, cb=self.onCancel)
            self._countdownBtn = 0
            self._countdownLabel = _('Ok (%s)')
        else:
            view.setButton(0,_('Next'),  itg.ID_OK,     cb=self.quit)
            view.setButton(1,_('Cancel'),  itg.ID_CANCEL, cb=self.onCancel)
            self._countdownBtn = 1
            self._countdownLabel = _('Cancel (%s)')
        view.setText(displayHtml)
        
        self.employee = employee
        # Enable timeout
        self.setTimeout(timeout)
        self.addView(view)
                
    def __onSkip(self, btn):
        """Leave consent status unchanged and continue the current operation"""
        self.data["consentStatus"] = ConsentStatus.DEFERRED
        self.data["isSkipped"] = True
        self.sendConsentStatus()
        self.quit(itg.ID_OK)

class _ConsentPageDialog(_BasePageDialog):

    def __init__(self, page, employee):
        super(_ConsentPageDialog, self).__init__(employee)
        self.page = page
            
        view = itg.MsgBoxView()
        view.setText(self.page)

        view.setButton(1, 'Back', itg.ID_BACK, self.quit)
        view.setButton(0, 'Next', itg.ID_NEXT, self.quit)
        self.addView(view)

class _ConsentConfirmDialog(_BasePageDialog):
    
    def __init__(self, employee, timeout = 30, overrideStatus = None, forEnrol = False):

        super(_ConsentConfirmDialog, self).__init__(employee)
        
        self.html = "Please confirm your consent."
        self.forEnrol = forEnrol
        
        displayHtml = self.html
        consents = employee.getConsents()
        status = consents.getStatus()
        self.forRenewal = (consents.count() > 0)
        
        view = itg.MsgBoxView()
        if overrideStatus:
            status = overrideStatus
        else:
            status = employee.getConsents().getStatus()
        if status == ConsentStatus.EXPIRING:
            displayHtml = "Consent is expiring\n" + self.html
            view.setButton(0,_('Accept'), itg.ID_OK, cb=self.__onAccept)
            view.setButton(1,_('Decline'), itg.ID_ABORT, cb=self.__onDecline)
            view.setButton(2,_('Skip'), itg.ID_IGNORE, cb=self.__onSkip)
            self._countdownBtn = 0
            self._countdownLabel = _('Skip (%s)')
        else:
            view.setButton(0,_('Accept'),  itg.ID_OK,     cb=self.__onAccept)
            view.setButton(1,_('Decline'), itg.ID_ABORT,  cb=self.__onDecline)
            view.setButton(2,_('Cancel'),  itg.ID_CANCEL, cb=self.onCancel)
            self._countdownBtn = 2
            self._countdownLabel = _('Cancel (%s)')
        view.setText(displayHtml)
            
        self.employee = employee
        # Enable timeout
        self.setTimeout(timeout)
        self.addView(view) 
       
    def __onSkip(self, btn): 
        """Leave consent status unchanged and continue the current operation"""
        self.data["consentStatus"] = ConsentStatus.DEFERRED
        self.sendConsentStatus()
        self.quit(itg.ID_OK)
        
    def __onAccept(self, btn):
        """ Set consent status to accepted"""
        status = self.employee.getConsents().getStatus()
        if status == ConsentStatus.EXPIRING or self.forRenewal:
            self.data["consentStatus"] = ConsentStatus.RENEWED
        else:
            self.data["consentStatus"] = ConsentStatus.ENROLLED
        self.sendConsentStatus()
        self.quit(itg.ID_OK)
    
    def __onDecline(self, btn):
        """ Set consent status to declined"""
        resID = itg.msgbox(itg.MB_OK_CANCEL, _('This will delete all your templates'))
        if resID == itg.ID_OK:
            self.data["consentStatus"] = ConsentStatus.DECLINED
            self.sendConsentStatus()
            self.quit(itg.ID_CANCEL)
