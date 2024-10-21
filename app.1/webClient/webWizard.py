# -*- coding: utf-8 -*-
#
# Copyright 2011 Grosvenor Technology
#

from applib.gui import appWizard
import itg
import webClient

# TODO: Test on IT11
# TODO: Test new wizard settings
    
class WebClientWizardHostPage(appWizard.AppWizardPage, itg.Dialog):
    
    def __init__(self, title=None):
        super(WebClientWizardHostPage, self).__init__()
        self.__title = title
    
    def onCreate(self):
        super(WebClientWizardHostPage, self).onCreate()
        if (self.__isIPv4(self.__getHost())):
            self.__onIPView()
        else:
            self.__onHostnameView()
        self.disableTimeout()
        
    def __setHost(self, hostName):
        self._settings['app']['webclient_host'] = hostName

    def __getHost(self):
        return self._settings['app']['webclient_host']
        
    def __isIPv4(self, value):
        try:
            if (value.count('.') != 3):
                return False
            for n in value.strip().split('.'):
                int(n)
        except:
            return False
        return True        
        
    def __onIPView(self, btnID=0):
        lastView = self.getView()   
        if (self.__title == None):
            view = itg.IPInputView(_('Server IP address'))            
        else:
            view = itg.IPInputView(self.__title)
        view.setButton(0, _('Next'), itg.ID_NEXT, self.__onOK)
        view.setButton(1, _('Hostname'), itg.ID_NETWORK, self.__onHostnameView)        
        view.setButton(2, _('Back'), itg.ID_BACK, self.back)
        view.setButton(3, _('Cancel'), itg.ID_CANCEL, self.cancel)
        self.addView(view)
        if (lastView != None):
            value = lastView.getValue()
        else:
            value = self.__getHost()
        view.setValue(value)            
        view.show()
    
    def __onHostnameView(self, btnID=0):
        lastView = self.getView()
        if (self.__title == None):
            view = itg.TextInputView(_('Server hostname'))            
        else:
            view = itg.TextInputView(self.__title)
        view.setButton(0, _('Next'), itg.ID_NEXT, self.__onOK)
        view.setButton(1, _('IP Address'), itg.ID_NETWORK, self.__onIPView)
        view.setButton(2, _('Back'), itg.ID_BACK, self.back)
        view.setButton(3, _('Cancel'), itg.ID_CANCEL, self.cancel)       
        self.addView(view)
        if (lastView != None and lastView.getValue() != '0.0.0.0'):
            value = lastView.getValue()
        else:
            value = self.__getHost()
        view.setValue(value)            
        view.show()       

    def __onOK(self, btnID):
        hostname = self.getView().getValue()
        if (not hostname or hostname == '0.0.0.0'):
            itg.msgbox(itg.MB_OK, _('Please enter a valid hostname or IP address.'))
        else:
            self.__setHost(hostname)
            self.quit(itg.ID_NEXT)

    def skip(self):
        if (self._settings['app'].get('wiz_webclient_prompt_host') == 'False'):
            return True
        return False    



class WebClientWizardRegisterPage(appWizard.AppWizardPage, itg.Dialog):
    
    def onCreate(self):
        super(WebClientWizardRegisterPage, self).onCreate()        
        view = itg.MsgBoxView()
        view.setText(_('Failed to register with web service!'))
        if (self._settings['app'].get('wiz_webclient_register') == 'required'):
            btnOfs = 0
        else:
            btnOfs = 1
            btnId = itg.ID_SKIP if hasattr(itg, 'ID_SKIP') else itg.ID_OK
            view.setButton(0, _('Skip'), btnId, self.__onSkip)
        view.setButton(btnOfs+0, _('Retry'), itg.ID_RETRY, self.__onRetry)        
        view.setButton(btnOfs+1, _('Back'), itg.ID_BACK, self.back)        
        view.setButton(btnOfs+2, _('Cancel'), itg.ID_CANCEL, self.cancel)
        self.addView(view)
    
    def skip(self):
        if (self._settings['app'].get('wiz_webclient_register') == 'never'):
            return True
        return False 
     
    def __onSkip(self, btnID):
        self.quit(itg.ID_NEXT)
    
    def __onRetry(self, btnID):
        isRegistered = self.__register()
        if (isRegistered):
            self.quit(itg.ID_NEXT)
                
    def onRefreshData(self):
        self.__isRegistered = self.__register()
        
    def run(self):
        if (self.__isRegistered):
            self.setResultID(itg.ID_NEXT)
            return self.getResultID()
        return super(WebClientWizardRegisterPage, self).run()

    def __setFailText(self, msg):
        self.getView().setText(msg)
        
    def __register(self):
        reqQueue = webClient.getJobQueue()
        if (reqQueue == None):
            self.__setFailText(_('Registration not available at this time. Please try again later.'))
        else:
            registerRequest = webClient.RegisterDeviceRequest(
                                        self._settings['app']['webclient_host'],
                                        self._settings['app']['webclient_ssl'] == 'True',
                                        self._settings['app']['webclient_resource'],
                                        self._settings['app']['webclient_username'],
                                        self._settings['app']['webclient_password'],
                                        self._settings['app']['webclient_check_certificate'] == 'True',
                                        self._settings['app']['clksrv_id'])
            uiTimeout = 10
            itg.waitbox(_('Contacting server, please wait...'), reqQueue.addJobAndWait, (registerRequest,uiTimeout), registerRequest.cancel)
            if (registerRequest.wasCancelled()):
                self.__setFailText(_('Registration was cancelled.'))
            elif (registerRequest.hasTimedout()):
                self.__setFailText(_('Registration timed out.'))
            elif (registerRequest.isRegistered()):
                self._settings['app']['webclient_auth_token'] = registerRequest.getToken()
                self._settings['app']['webclient_buttons_revision'] = ''
                self._settings['app']['webclient_itcfg_revision'] = ''
                self._settings['app']['webclient_employees_revision'] = ''
                self._settings['app']['webclient_employeeinfo_revision'] = ''
                self._settings['app']['webclient_datacollection_revision'] = ''        
                self.getView().setText(_('Device is registered.'))            
                return True
            elif (registerRequest.hasFailed() and registerRequest.getFailedReason()):
                self.__setFailText(_('Registration failed: %s' % registerRequest.getFailedReason()))
            else:
                self.__setFailText(_('Registration failed!'))
        return False

    
    
