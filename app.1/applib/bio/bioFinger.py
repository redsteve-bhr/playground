# -*- coding: utf-8 -*-
#
# Copyright 2015 Grosvenor Technology
#

def getFingerNameByCode(fingerCode):
    fingerNames = { 'lp': _('left pinky'),
                    'lr': _('left ring'),
                    'lm': _('left middle'),
                    'li': _('left index'),
                    'lt': _('left thumb'),
                    'rt': _('right thumb'),
                    'ri': _('right index'),
                    'rm': _('right middle'),
                    'rr': _('right ring'),
                    'rp': _('right pinky')}
    return fingerNames.get(fingerCode)


class BioFinger(object):
    
    def __init__(self, fingerCode, templates, quality):
        self.__fingerCode = fingerCode
        self.__templates = templates
        self.__quality = quality
    
    def getTemplates(self):
        return self.__templates
    
    def getFingerCode(self):
        return self.__fingerCode
    
    def getQuality(self):
        return self.__quality