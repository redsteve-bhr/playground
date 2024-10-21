EasyClock-ws Application Release Notes 
=======================================
 
This document provides release notes for the EasyClock-ws clock application updates for the Grosvenor IT (Linux) terminals. 
EasyClock-ws Terminal application versions: 

v3.6.0
----------------------
- Added new table and file-handler for Schedules
- Added Online State
- Added basic Punch Restrictions, checking for Schedules and Last Punch
- Added check for Supervisor Override for Schedules
- Calendar view respects system locale and application settings.
- Fix for occasional error when decoding finger print templates.
- Minor internal stability fixes including UI fixes.
- There are no security related changes in this version.

v3.5
----------------------
- Added support for Action Requests from GtConnect
- Added support for Cloud Upload requested from GtConnect
- Added ExternalID to employees database table
- Fixed proxy server tunnel issue.
- Diagnostics added to Supervisor menu.
- Biometric consent added.
- Elatec reader support added.
- GtConnect metrics support added.
- Update applib v4.4.
- GT4-2 enhanced compatibility.
- There are no security related changes in this version.

v3.4
----------------------
- Added proxy-server support
- Added support for GT10-Linux
- Added support for custom themes
- Added Spanish translation file
- Amended visual appearance of idle screen
- Allow any HTTP 2nn code to be accepted for web-call response
- Added support for 'apprestart.xml' to restart application
- Added support for 'reboot.xml' to reboot application
- New application setting numeric_only_badge, set to True to reject non numeric badge codes.
- There are no security related changes in this version.

v3.3
----------------------
- Remove multi-decoding template work-around. This assumes that all templates in the database are now single-encoded.
- Fix re-enrol finger issue. Previously the old template was not replaced.
- There are no security related changes in this version.

v3.2
----------------------
- Added terminal support check to the Change Photo profile editor option
- Resolved Enter Pin option missing from profile editor.
- Added employee default verification method.
- Use PATCH instead of PUSH when sending Employee Update to web-service
- Send empty template when deleting last finger template from employee

v3.1 - 9th March 2021 
----------------------
- Added x-gt-serialnumber header. 
- Added serialNumber tag to Custom Exchange header.  
- Web service get employees returns a totalEmployeeCount of 0 if not specified. 
- GT4 fixed to not load profile photos. 


v3.0 - 26th March 2020 
-----------------------
- Biometric encryption support for Suprema reader. 
- Fixed unicode handling in relay schedules editor. 
- Fixed timeout for non SSL HTTP connections. 


v2.0 - 22nd August 2019 
-----------------------
- GT-4 compatibility. 


v1.4 - 22nd May 2019 
---------------------
- added timeout to web-client connection, controlled by webclient_timeout application setting. [767]


v1.3 - 3rd October 2017 
-----------------------
- Fix bug #367 - Relay schedule is updated incorrectly. 

 
v1.2 - 13th April 2017 
----------------------
- Terminal complains about missing certificate file [335]
- Customisable Themes [FR88]


v1.1 - 7th September 2016 
-------------------------
- Fix bug in DataCollection menu display  
- Fix bug which gives error when this in XML: 
     <action> 
        <ws.dataCollection.menu /> 
     </action>
 

v1.0 - 18th August 2015 
-----------------------
- Initial application released. 
