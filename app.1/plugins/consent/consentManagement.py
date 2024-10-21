# -*- coding: utf-8 -*-
#
# Copyright 2023 Grosvenor Technology
#
import itg
from applib.utils import timeUtils
import miscUtils
from consentManager import ConsentConfig, ConsentRecord, ConsentStatus
from consentDialog import ConsentDialog

class ManageConsentDialog(itg.Dialog):
    
    def __init__(self, employee):
        """ Create dialog."""
        super(ManageConsentDialog, self).__init__()
        self.__employee = employee
        view = itg.MsgBoxView()
        view.setText(self.__getConsentMessage())
        consents = self.__employee.getConsents()
        if consents is not None and consents.count() > 0:
            view.setButton(0, _('Renew'), itg.ID_OK,   cb=self.__onManage)
            view.setButton(1, _('Cancel'),  itg.ID_CANCEL, cb=self.cancel)
        else:
            view.setButton(0, _('OK'),  itg.ID_OK, cb=self.cancel)
        self.addView(view)

    def __getConsentMessage(self, renewed=False):
        consents = self.__employee.getConsents()
        consent = None
        hasConsent = True
        if consents is not None:
            consent = consents.getActiveConsent()
        if consent is None:
            consent = ConsentRecord()
            consent.time = ""
            consent.expiry = ""
            hasConsent = False
        
        if renewed:
            title = "Consent Renewed"
        else:
            title = "Consent"

        if hasConsent:
            consentDate = timeUtils.getDatetimeFromISO8601(consent.time)
            consentDateStr = miscUtils.userFriendlyDate(consentDate, includeTime=False)
            expiryDate = timeUtils.getDatetimeFromISO8601(consent.expiry)
            expiryDateStr = miscUtils.userFriendlyDate(expiryDate, includeTime=False)
            msg = '{}\n\nEnrolled on: {}\nExpires on: {}'.format(title, consentDateStr, expiryDateStr)
        else:
            msg = "No consent found"
        
        return msg

    def __onManage(self, btn):
        empLanguage = self.__employee.getLanguage(useManagerIfAvailable=False)
        config = ConsentConfig(empLanguage=empLanguage)
        dlg = ConsentDialog(config.getMessage(), self.__employee, overrideStatus=ConsentStatus.PENDING)
        resID = dlg.run()
        if resID is itg.ID_OK:
            itg.msgbox(itg.MB_OK, _(self.__getConsentMessage(renewed=True)))
        self.quit(resID)
