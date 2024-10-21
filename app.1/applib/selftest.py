# -*- coding: utf-8 -*-
#
# Copyright 2013 Grosvenor Technology
#

from utils import countries
from utils import timeUtils
from db import sqlTime
import os
import time
import datetime
import locale

def _utc2local(utcStr, tzRule):
    # get UTC calendar time
    origTZ = os.environ['TZ'] if ('TZ' in os.environ) else ''
    if (utcStr):
        os.environ['TZ'] = ''
        time.tzset() #@UndefinedVariable
        if (time.timezone != 0):
            raise Exception('Changing timezones does not work!')
        tm = time.strptime(utcStr, '%Y-%m-%dT%H:%M:%S')
        t =  time.mktime(tm)
    else:
        t = None
    # create time string in localtime
    os.environ['TZ'] = tzRule
    time.tzset() #@UndefinedVariable
    ltime   = time.localtime(t)
    offset  = -time.altzone if ltime.tm_isdst else -time.timezone
    timeStr = time.strftime('%Y-%m-%dT%H:%M:%S', ltime)
    timeStr += '%+03d%02d %s' % (offset / 3600, (offset % 3600) / 60, time.tzname[ltime.tm_isdst])
    os.environ['TZ'] = origTZ
    time.tzset() #@UndefinedVariable  
    return timeStr


def testCountries():
    if (not hasattr(time, 'tzset')):
        print '    Unable to execute test, tzset not available (upgrade to FW >= 2.0.0)'
        return 1
    errors = 0
    count  = 0
    for c in countries.getAll():
        # timezones
        for t in c.getTimezones():
            tests = t.getTestData()
            if (tests):
                hadError = False
                for (utcStr, localStr) in tests:
                    result = _utc2local(utcStr, t.getRule())
                    if (result != localStr):
                        if (not hadError):
                            print '    Error while testing %s/%s!' % (c.getCountry(), t.getName())
                            hadError = True
                        print '      UTC time %s calculated to %s, but %s expected' % (utcStr, result, localStr)
                        errors += 1
                    count += 1
    return (count, errors)


def _sql2local(sqlStr, tzRule):
    # get UTC calendar time
    origTZ = os.environ['TZ'] if ('TZ' in os.environ) else ''
    if (not sqlStr):
        raise Exception('sqlStr not set?')
    try:
        os.environ['TZ'] = ''
        time.tzset() #@UndefinedVariable
        if (time.timezone != 0):
            raise Exception('Changing timezones does not work!')
        # create time string in localtime
        os.environ['TZ'] = tzRule
        time.tzset() #@UndefinedVariable
        timeStr = sqlTime.sqlTime2MyLocalTime(sqlStr, '%Y-%m-%dT%H:%M:%S%z %Z')
        return timeStr
    finally:
        os.environ['TZ'] = origTZ
        time.tzset() #@UndefinedVariable  


def _local2sql(localStr, tzRule):
    # get UTC calendar time
    origTZ = os.environ['TZ'] if ('TZ' in os.environ) else ''
    if (not localStr):
        raise Exception('localStr not set?')
    try:
        os.environ['TZ'] = ''
        time.tzset() #@UndefinedVariable
        if (time.timezone != 0):
            raise Exception('Changing timezones does not work!')
        # create time string in localtime
        os.environ['TZ'] = tzRule
        time.tzset() #@UndefinedVariable
        localTime = datetime.datetime.strptime(localStr[:19], '%Y-%m-%dT%H:%M:%S')
        timeStr = sqlTime.localTime2SqlTime(localTime)
        return timeStr
    finally:
        os.environ['TZ'] = origTZ
        time.tzset() #@UndefinedVariable  


def testSqlTime():
    if (not hasattr(time, 'tzset')):
        print '    Unable to execute test, tzset not available (upgrade to FW >= 2.0.0)'
        return 1
    errors = 0
    count  = 0
    for c in countries.getAll():
        # timezones
        for t in c.getTimezones():
            tests = t.getTestData()
            if (tests):
                hadError = False
                for (utcStr, localStr) in tests:
                    sqlStr = utcStr.replace('T', ' ')
                    result = _sql2local(sqlStr, t.getRule())
                    if (result != localStr):
                        if (not hadError):
                            print '    Error while testing time conversion for time zone %s/%s!' % (c.getCountry(), t.getName())
                            hadError = True
                        print '      UTC time %s calculated to %s, but %s expected' % (sqlStr, result, localStr)
                        errors += 1
                    count += 1
                    if (localStr[13:19] in (':05:00',':55:00')):
                        continue
                    result = _local2sql(localStr, t.getRule())
                    if (result != sqlStr):
                        if (not hadError):
                            print '    Error while testing time conversion for time zone %s/%s!' % (c.getCountry(), t.getName())
                            hadError = True
                        print '      Local time %s calculated to %s, but %s expected' % (localStr, result, sqlStr)
                        errors += 1
                    count += 1
    return (count, errors)


_pcLocales = {
    'aa_DJ.UTF-8': ('%l:%M:%S', '%d.%m.%Y'), 
    'aa_ER.UTF-8': ('%l:%M:%S', '%d/%m/%Y'), 
    'aa_ET.UTF-8': ('%l:%M:%S', '%d/%m/%Y'), 
    'af_ZA.UTF-8': ('%T', '%d/%m/%Y'), 
    'am_ET.UTF-8': ('%l:%M:%S', '%d/%m/%Y'), 
    'an_ES.UTF-8': ('%T', '%d/%m/%y'), 
    'ar_AE.UTF-8': ('%Z %I:%M:%S ', '%d %b, %Y'), 
    'ar_BH.UTF-8': ('%Z %I:%M:%S ', '%d %b, %Y'), 
    'ar_DZ.UTF-8': ('%Z %I:%M:%S ', '%d %b, %Y'), 
    'ar_EG.UTF-8': ('%Z %I:%M:%S ', '%d %b, %Y'), 
    'ar_IN.UTF-8': ('%I:%M:%S  %Z', '%A %d %B %Y'), 
    'ar_IQ.UTF-8': ('%Z %I:%M:%S ', '%d %b, %Y'), 
    'ar_JO.UTF-8': ('%Z %I:%M:%S ', '%d %b, %Y'), 
    'ar_KW.UTF-8': ('%Z %I:%M:%S ', '%d %b, %Y'), 
    'ar_LB.UTF-8': ('%Z %I:%M:%S ', '%d %b, %Y'), 
    'ar_LY.UTF-8': ('%Z %I:%M:%S ', '%d %b, %Y'), 
    'ar_MA.UTF-8': ('%Z %I:%M:%S ', '%d %b, %Y'), 
    'ar_OM.UTF-8': ('%Z %I:%M:%S ', '%d %b, %Y'), 
    'ar_QA.UTF-8': ('%Z %I:%M:%S ', '%d %b, %Y'), 
    'ar_SA.UTF-8': ('%k:%M:%S', '%A %e %B %Y'), 
    'ar_SD.UTF-8': ('%Z %I:%M:%S ', '%d %b, %Y'), 
    'ar_SY.UTF-8': ('%Z %I:%M:%S ', '%d %b, %Y'), 
    'ar_TN.UTF-8': ('%Z %I:%M:%S ', '%d %b, %Y'), 
    'ar_YE.UTF-8': ('%Z %I:%M:%S ', '%d %b, %Y'), 
    'as_IN.UTF-8': ('%I.%M.%S %p', '%e-%m-%Y'), 
    'ast_ES.UTF-8': ('%T', '%d/%m/%y'), 
    'az_AZ.UTF-8': ('%T', '%d.%m.%Y'), 
    'be_BY.UTF-8': ('%T', '%d.%m.%Y'), 
    'ber_DZ.UTF-8': ('%T', '%d.%m.%Y'), 
    'ber_MA.UTF-8': ('%T', '%d.%m.%Y'), 
    'bg_BG.UTF-8': ('%k,%M,%S', '%e.%m.%Y'), 
    'bn_BD.UTF-8': ('%I:%M:%S  %Z', '%A %d %b %Y'), 
    'bn_IN.UTF-8': ('%I:%M:%S  %Z', '%A %d %b %Y'), 
    'bo_CN.UTF-8': ('ཆུ་ཚོད%Hཀསར་མ%Mཀསར་ཆ%S', 'པསྱི་ལོ%yཟལ%mཚེས%d'), 
    'bo_IN.UTF-8': ('ཆུ་ཚོད%Hཀསར་མ%Mཀསར་ཆ%S', 'པསྱི་ལོ%yཟལ%mཚེས%d'), 
    'br_FR.UTF-8': ('%T', '%d.%m.%Y'), 
    'bs_BA.UTF-8': ('%T', '%d.%m.%Y'), 
    'byn_ER.UTF-8': ('%l:%M:%S', '%d/%m/%Y'), 
    'ca_AD.UTF-8': ('%T', '%d/%m/%y'), 
    'ca_ES.UTF-8': ('%T', '%d/%m/%y'), 
    'ca_FR.UTF-8': ('%T', '%d/%m/%y'), 
    'ca_IT.UTF-8': ('%T', '%d/%m/%y'), 
    'crh_UA.UTF-8': ('%T', '%d.%m.%Y'), 
    'csb_PL.UTF-8': ('%T', '%Y-%m-%d'), 
    'cs_CZ.UTF-8': ('%H:%M:%S', '%-d.%-m.%Y'), 
    'cy_GB.UTF-8': ('%T', '%d.%m.%y'), 
    'da_DK.UTF-8': ('%T', '%d-%m-%Y'), 
    'de_AT.UTF-8': ('%T', '%Y-%m-%d'), 
    'de_BE.UTF-8': ('%T', '%Y-%m-%d'), 
    'de_CH.UTF-8': ('%T', '%d.%m.%Y'), 
    'de_DE.UTF-8': ('%T', '%d.%m.%Y'), 
    'de_LI.UTF-8': ('%T', '%d.%m.%Y'), 
    'de_LU.UTF-8': ('%T', '%Y-%m-%d'), 
    'dv_MV.UTF-8': ('%H:%M:%S', '%d/%m/%Y'), 
    'dz_BT.UTF-8': ('ཆུ་ཚོད%Hཀསར་མ%Mཀསར་ཆ%S', 'པསྱི་ལོ%yཟལ%mཚེས%d'), 
    'el_CY.UTF-8': ('%r', '%d/%m/%Y'), 
    'el_GR.UTF-8': ('%r', '%d/%m/%Y'), 
    'en_AG.UTF-8': ('%T', '%d/%m/%y'), 
    'en_AU.UTF-8': ('%T', '%d/%m/%y'), 
    'en_BW.UTF-8': ('%T', '%d/%m/%Y'), 
    'en_CA.UTF-8': ('%r', '%d/%m/%y'), 
    'en_DK.UTF-8': ('%T', '%Y-%m-%d'), 
    'en_GB.UTF-8': ('%T', '%d/%m/%y'), 
    'en_HK.UTF-8': ('%I:%M:%S %Z', '%A, %B %d, %Y'), 
    'en_IE.UTF-8': ('%T', '%d/%m/%y'), 
    'en_IN.UTF-8': ('%I:%M:%S  %Z', '%A %d %B %Y'), 
    'en_NG.UTF-8': ('%T', '%d/%m/%Y'), 
    'en_NZ.UTF-8': ('%T', '%d/%m/%y'), 
    'en_PH.UTF-8': ('%I:%M:%S  %Z', '%A, %d %B, %Y'), 
    'en_SG.UTF-8': ('%I:%M:%S  %Z', '%A %d,%B,%Y'), 
    'en_US.UTF-8': ('%r', '%m/%d/%Y'), 
    'en_ZA.UTF-8': ('%T', '%d/%m/%Y'), 
    'en_ZW.UTF-8': ('%T', '%d/%m/%Y'), 
    'es_AR.UTF-8': ('%T', '%d/%m/%y'), 
    'es_BO.UTF-8': ('%T', '%d/%m/%y'), 
    'es_CL.UTF-8': ('%T', '%d/%m/%y'), 
    'es_CO.UTF-8': ('%T', '%d/%m/%y'), 
    'es_CR.UTF-8': ('%T', '%d/%m/%Y'), 
    'es_DO.UTF-8': ('%T', '%d/%m/%y'), 
    'es_EC.UTF-8': ('%T', '%d/%m/%y'), 
    'es_ES.UTF-8': ('%T', '%d/%m/%y'), 
    'es_GT.UTF-8': ('%T', '%d/%m/%y'), 
    'es_HN.UTF-8': ('%T', '%d/%m/%y'), 
    'es_MX.UTF-8': ('%T', '%d/%m/%y'), 
    'es_NI.UTF-8': ('%T', '%d/%m/%y'), 
    'es_PA.UTF-8': ('%T', '%d/%m/%y'), 
    'es_PE.UTF-8': ('%T', '%d/%m/%y'), 
    'es_PR.UTF-8': ('%T', '%d/%m/%y'), 
    'es_PY.UTF-8': ('%T', '%d/%m/%y'), 
    'es_SV.UTF-8': ('%T', '%d/%m/%y'), 
    'es_US.UTF-8': ('%T', '%d/%m/%y'), 
    'es_UY.UTF-8': ('%T', '%d/%m/%y'), 
    'es_VE.UTF-8': ('%T', '%d/%m/%y'), 
    'et_EE.UTF-8': ('%T', '%d.%m.%Y'), 
    'eu_ES.UTF-8': ('%T', '%a, %Y.eko %bren %da'), 
    'eu_FR.UTF-8': ('%T', '%a, %Y.eko %bren %da'), 
    'fa_IR.UTF-8': ('%OH:%OM:%OS', '%Oy/%Om/%Od'), 
    'fi_FI.UTF-8': ('%H.%M.%S', '%d.%m.%Y'), 
    'fil_PH.UTF-8': ('%r', '%m/%d/%y'), 
    'fo_FO.UTF-8': ('%T', '%d/%m-%Y'), 
    'fr_BE.UTF-8': ('%T', '%d/%m/%y'), 
    'fr_CA.UTF-8': ('%T', '%Y-%m-%d'), 
    'fr_CH.UTF-8': ('%T', '%d. %m. %y'), 
    'fr_FR.UTF-8': ('%T', '%d/%m/%Y'), 
    'fr_LU.UTF-8': ('%T', '%d.%m.%Y'), 
    'fur_IT.UTF-8': ('%T', '%d. %m. %y'), 
    'fy_DE.UTF-8': ('%T', '%d.%m.%Y'), 
    'fy_NL.UTF-8': ('%T', '%d-%m-%y'), 
    'ga_IE.UTF-8': ('%T', '%d.%m.%y'), 
    'gd_GB.UTF-8': ('%T', '%d/%m/%y'), 
    'gez_ER.UTF-8': ('%l:%M:%S', '%d/%m/%Y'), 
    'gez_ET.UTF-8': ('%l:%M:%S', '%d/%m/%Y'), 
    'gl_ES.UTF-8': ('%T', '%d/%m/%y'), 
    'gu_IN.UTF-8': ('%I:%M:%S  %Z', '%A %d %b %Y'), 
    'gv_GB.UTF-8': ('%T', '%d/%m/%y'), 
    'ha_NG.UTF-8': ('%r', '%d/%m/%y'), 
    'he_IL.UTF-8': ('%H:%M:%S', '%d/%m/%y'), 
    'hi_IN.UTF-8': ('%I:%M:%S  %Z', '%A %d %b %Y'), 
    'hne_IN.UTF-8': ('%I:%M:%S  %Z', '%A %d %b %Y'), 
    'hr_HR.UTF-8': ('%T', '%d.%m.%Y'), 
    'hsb_DE.UTF-8': ('%T', '%d.%m.%Y'), 
    'ht_HT.UTF-8': ('%t', '%d/%m/%y'), 
    'hu_HU.UTF-8': ('%H.%M.%S', '%Y-%m-%d'), 
    'hy_AM.UTF-8': ('%r', '%m/%d/%y'), 
    'id_ID.UTF-8': ('%T', '%d/%m/%y'), 
    'ig_NG.UTF-8': ('%r', '%d/%m/%y'), 
    'ik_CA.UTF-8': ('%r', '%d/%m/%y'), 
    'is_IS.UTF-8': ('%T', '%a %e.%b %Y'), 
    'it_CH.UTF-8': ('%T', '%d. %m. %y'), 
    'it_IT.UTF-8': ('%T', '%d/%m/%Y'), 
    'iu_CA.UTF-8': ('%r', '%m/%d/%y'), 
    'iw_IL.UTF-8': ('%H:%M:%S', '%d/%m/%y'), 
    'ja_JP.UTF-8': ('%H時%M分%S秒', '%Y年%m月%d日'), 
    'ka_GE.UTF-8': ('%T', '%m/%d/%Y'), 
    'kk_KZ.UTF-8': ('%T', '%d.%m.%Y'), 
    'kl_GL.UTF-8': ('%T', '%d %b %Y'), 
    'km_KH.UTF-8': ('%H:%M:%S', '%e %B %Y'), 
    'kn_IN.UTF-8': ('%I:%M:%S  %Z', '%A %d %b %Y'), 
    'ko_KR.UTF-8': ('%H시 %M분 %S초', '%Y년 %m월 %d일'), 
    'ks_IN.UTF-8': ('%I:%M:%S  %Z', '%A %d %b %Y'), 
    'ku_TR.UTF-8': ('%T', '%d/%m/%Y'), 
    'kw_GB.UTF-8': ('%T', '%d/%m/%y'), 
    'ky_KG.UTF-8': ('%T', '%d.%m.%Y'), 
    'lg_UG.UTF-8': ('%T', '%d/%m/%y'), 
    'li_BE.UTF-8': ('%T', '%d.%m.%Y'), 
    'li_NL.UTF-8': ('%T', '%d.%m.%Y'), 
    'lo_LA.UTF-8': ('%H:%M:%S', '%d/%m/%Ey'), 
    'lt_LT.UTF-8': ('%T', '%Y.%m.%d'), 
    'lv_LV.UTF-8': ('%T', '%Y.%m.%d.'), 
    'mai_IN.UTF-8': ('%I:%M:%S  %Z', '%A %d %b %Y'), 
    'mg_MG.UTF-8': ('%T', '%d.%m.%Y'), 
    'mi_NZ.UTF-8': ('%T', '%d/%m/%y'), 
    'mk_MK.UTF-8': ('%T', '%d.%m.%Y'), 
    'ml_IN.UTF-8': ('%I:%M:%S  %Z', '%A %d %B %Y'), 
    'mn_MN.UTF-8': ('%T', '%Y.%m.%d'), 
    'mr_IN.UTF-8': ('%I:%M:%S  %Z', '%A %d %b %Y'), 
    'ms_MY.UTF-8': ('%I:%M:%S  %Z', '%A %d %b %Y'), 
    'mt_MT.UTF-8': ('%I:%M:%S  %Z', '%A, %d ta %b, %Y'), 
    'my_MM.UTF-8': ('%OI:%OM:%OS %p', '%OC%Oy %b %Od %A'), 
    'nb_NO.UTF-8': ('kl. %H.%M %z', '%d. %b %Y'), 
    'nds_DE.UTF-8': ('%T', '%d.%m.%Y'), 
    'nds_NL.UTF-8': ('%T', '%d.%m.%Y'), 
    'ne_NP.UTF-8': ('%I:%M:%S  %Z', '%A %d %b %Y'), 
    'nl_AW.UTF-8': ('%T', '%d-%m-%y'), 
    'nl_BE.UTF-8': ('%T', '%d-%m-%y'), 
    'nl_NL.UTF-8': ('%T', '%d-%m-%y'), 
    'nn_NO.UTF-8': ('kl. %H.%M %z', '%d. %b %Y'), 
    'nr_ZA.UTF-8': ('%T', '%d/%m/%Y'), 
    'nso_ZA.UTF-8': ('%T', '%d/%m/%Y'), 
    'oc_FR.UTF-8': ('%T', '%d.%m.%Y'), 
    'om_ET.UTF-8': ('%l:%M:%S', '%d/%m/%Y'), 
    'om_KE.UTF-8': ('%l:%M:%S', '%d/%m/%Y'), 
    'or_IN.UTF-8': ('%OI:%OM:%OS %p', '%Od-%Om-%Oy'), 
    'pa_IN.UTF-8': ('%I:%M:%S  %Z', '%A %d %b %Y'), 
    'pap_AN.UTF-8': ('%T', '%d-%m-%y'), 
    'pa_PK.UTF-8': ('%H:%M:%S', '%d/%m/%Y'), 
    'pl_PL.UTF-8': ('%T', '%d.%m.%Y'), 
    'ps_AF.UTF-8': ('%H:%M:%S', 'د %Y د %B %e'), 
    'pt_BR.UTF-8': ('%T', '%d-%m-%Y'), 
    'pt_PT.UTF-8': ('%T', '%d-%m-%Y'), 
    'ro_RO.UTF-8': ('%T', '%d.%m.%Y'), 
    'ru_RU.UTF-8': ('%T', '%d.%m.%Y'), 
    'ru_UA.UTF-8': ('%T', '%d.%m.%Y'), 
    'rw_RW.UTF-8': ('%T', '%d.%m.%Y'), 
    'sa_IN.UTF-8': ('%I:%M:%S  %Z', '%A %d %b %Y'), 
    'sc_IT.UTF-8': ('%T', '%d. %m. %y'), 
    'sd_IN.UTF-8': ('%I:%M:%S  %Z', '%A %d %b %Y'), 
    'se_NO.UTF-8': ('%T', '%Y-%m-%d'), 
    'shs_CA.UTF-8': ('%r', '%d/%m/%y'), 
    'sid_ET.UTF-8': ('%l:%M:%S', '%d/%m/%Y'), 
    'si_LK.UTF-8': ('%H:%M:%S', '%Y-%m-%d'), 
    'sk_SK.UTF-8': ('%H:%M:%S', '%d.%m.%Y'), 
    'sl_SI.UTF-8': ('%T', '%d. %m. %Y'), 
    'so_DJ.UTF-8': ('%l:%M:%S', '%d.%m.%Y'), 
    'so_ET.UTF-8': ('%l:%M:%S', '%d/%m/%Y'), 
    'so_KE.UTF-8': ('%l:%M:%S', '%d/%m/%Y'), 
    'so_SO.UTF-8': ('%l:%M:%S', '%d/%m/%Y'), 
    'sq_AL.UTF-8': ('%I.%M.%S. %Z', '%Y-%b-%d'), 
    'sr_ME.UTF-8': ('%T', '%d.%m.%Y.'), 
    'sr_RS.UTF-8': ('%T', '%d.%m.%Y.'), 
    'ss_ZA.UTF-8': ('%T', '%d/%m/%Y'), 
    'st_ZA.UTF-8': ('%T', '%d/%m/%Y'), 
    'sv_FI.UTF-8': ('%H.%M.%S', '%d.%m.%Y'), 
    'sv_SE.UTF-8': ('%H.%M.%S', '%Y-%m-%d'), 
    'ta_IN.UTF-8': ('%I:%M:%S  %Z', '%A %d %B %Y'), 
    'te_IN.UTF-8': ('%p%I.%M.%S %Z', '%B %d %A %Y'), 
    'tg_TJ.UTF-8': ('%T', '%d.%m.%Y'), 
    'th_TH.UTF-8': ('%H:%M:%S', '%d/%m/%Ey'), 
    'ti_ER.UTF-8': ('%l:%M:%S', '%d/%m/%Y'), 
    'ti_ET.UTF-8': ('%l:%M:%S', '%d/%m/%Y'), 
    'tig_ER.UTF-8': ('%l:%M:%S', '%d/%m/%Y'), 
    'tk_TM.UTF-8': ('%T', '%d.%m.%Y'), 
    'tl_PH.UTF-8': ('%r', '%m/%d/%y'), 
    'tn_ZA.UTF-8': ('%T', '%d/%m/%Y'), 
    'tr_CY.UTF-8': ('%T', '%d-%m-%Y'), 
    'tr_TR.UTF-8': ('%T', '%d-%m-%Y'), 
    'ts_ZA.UTF-8': ('%T', '%d/%m/%Y'), 
    'tt_RU.UTF-8': ('%T', '%d.%m.%Y'), 
    'ug_CN.UTF-8': ('%T', '%Y-%m-%d'), 
    'uk_UA.UTF-8': ('%T', '%d.%m.%y'), 
    'ur_PK.UTF-8': ('%H:%M:%S', '%d/%m/%Y'), 
    'uz_UZ.UTF-8': ('%T', '%d/%m/%y'), 
    've_ZA.UTF-8': ('%T', '%d/%m/%Y'), 
    'vi_VN.UTF-8': ('%T', '%d/%m/%Y'), 
    'wa_BE.UTF-8': ('%H:%M:%S', '%d/%m/%Y'), 
    'wo_SN.UTF-8': ('%T', '%d.%m.%Y'), 
    'xh_ZA.UTF-8': ('%T', '%d/%m/%Y'), 
    'yi_US.UTF-8': ('%H:%M:%S', '%d/%m/%y'), 
    'yo_NG.UTF-8': ('%r', '%d/%m/%y'), 
    'zh_CN.UTF-8': ('%H时%M分%S秒', '%Y年%m月%d日'), 
    'zh_HK.UTF-8': ('%I時%M分%S秒 %Z', '%Y年%m月%d日 %A'), 
    'zh_SG.UTF-8': ('%H时%M分%S秒 %Z', '%Y年%m月%d日'), 
    'zh_TW.UTF-8': ('%H時%M分%S秒', '%Y年%m月%d日'), 
    'zu_ZA.UTF-8': ('%T', '%d/%m/%Y'), 
}

def testLocales():
    errors = 0
    count  = 0
    for c in countries.getAll():
        # locales
        for lang in c.getLanguages():
            lc = lang.getLocale()
            try:
                locale.setlocale(locale.LC_ALL, lc)
                t_fmt = locale.nl_langinfo(locale.T_FMT) # @UndefinedVariable
                d_fmt = locale.nl_langinfo(locale.D_FMT) # @UndefinedVariable
                count += 1
                if (lc not in _pcLocales):
                    print 'Cannot test locale %s' % lc
                    errors += 1                    
                else:
                    (pc_t_fmt, pc_d_fmt) = _pcLocales[lc]
                    if (pc_t_fmt != t_fmt):
                        print 'Time format for locale %s differs' % lc
                        print 'PC      : %s' % pc_t_fmt
                        print 'Terminal: %s' % t_fmt
                        errors += 1
                    count += 1                        
                    if (pc_d_fmt != d_fmt):
                        print 'Date format for locale %s differs' % lc
                        print 'PC      : %s' % pc_d_fmt
                        print 'Terminal: %s' % d_fmt
                        errors += 1
                    count += 1                        
            except Exception as e:
                print '    Error while testing %s/%s (%s): %s' % (c.getCountry(), lang.getName(), lc, e) 
                errors += 1
    return (count, errors)


def testISO8601():
    tests = (   ('2013-01-15T14:39:00Z'     , '2013-01-15 14:39:00' ),
                ('2013-01-15T06:39:00-08'   , '2013-01-15 14:39:00' ),
                ('2013-01-15T06:39:00-800'  , '2013-01-15 14:39:00' ),
                ('2013-01-15T06:39:00-0800' , '2013-01-15 14:39:00' ),
                ('2013-01-15T06:39:00-08:00', '2013-01-15 14:39:00' ),
                ('2013-01-15T06:39:00-08:00', '2013-01-15 14:39:00' ),
                ('2013-01-15T07:39:00-07:00', '2013-01-15 14:39:00' ),
                ('2013-01-15T08:39:00-06:00', '2013-01-15 14:39:00' ),
                ('2013-01-15T09:09:00-05:30', '2013-01-15 14:39:00' ),
                ('2013-01-15T09:39:00-05:00', '2013-01-15 14:39:00' ),
                ('2013-01-15T23:39:00+09'   , '2013-01-15 14:39:00' ),
                ('2013-01-15T23:39:00+900'  , '2013-01-15 14:39:00' ),
                ('2013-01-15T23:39:00+0900' , '2013-01-15 14:39:00' ),
                ('2013-01-15T23:39:00+09:00', '2013-01-15 14:39:00' ),
                ('2013-01-16T00:39:00+10'   , '2013-01-15 14:39:00' ),
                ('2013-01-16T00:39:00+1000' , '2013-01-15 14:39:00' ),
                ('2013-01-16T00:39:00+10:00', '2013-01-15 14:39:00' ), )
    errors = 0
    count  = 0
    for (isoTime, expectedUTC) in tests:
        result = timeUtils.getUTCDatetimeFromISO8601(isoTime).strftime('%Y-%m-%d %H:%M:%S')        
        if (result != expectedUTC):
            errors += 1
            print '    Error: %s was parsed as %s, but expected %s' % (isoTime, result, expectedUTC)
        count += 1
    return (count, errors)            
            

def runSelfTest():
    totalErrors = 0
    tests = ( ('timezones'                  , testCountries) ,
              ('sqlTime'                    , testSqlTime) ,
              ('locales'                    , testLocales) ,
              ('ISO8601 date & time'        , testISO8601) , )
    print 'Starting self-test...'
    for (name, testFunc) in tests:
        print '  Testing %s... ' % name
        (count, errors) = testFunc()
        totalErrors += errors
        if (errors):
            print '    Tests ended with %d errors.' % errors
        else:
            print '    Completed (%d tests)' % (count)
    print 'End of self-test, %d errors' % totalErrors
        
#
# Entry point for executing tests
#
if __name__ == '__main__':
    runSelfTest()
