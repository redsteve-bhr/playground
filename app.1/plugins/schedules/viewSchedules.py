# -*- coding: utf-8 -*-
#
import itg
import tblSchedules
from datetime import datetime


class ViewSchedulesDialog(itg.Dialog):

    def __init__(self, emp):
        super(ViewSchedulesDialog, self).__init__()
        self.__emp = emp

        view = itg.MenuView(_('View Schedules'))
        view.setBackButton(_('OK'), self.cancel)
        view.removeAllRows()

        schedules = tblSchedules.getAppSchedules().getSchedulesByEmpID(self.__emp.getEmpID())

        view.appendRow(_('Date'), _('Start - End'))

        for schedule in schedules:
            startTime = datetime.strptime(schedule['StartDateTime'], '%Y-%m-%dT%H:%M:%S')
            endTime =  datetime.strptime(schedule['EndDateTime'], '%Y-%m-%dT%H:%M:%S')

            view.appendRow(
                startTime.strftime('%A %d'),
                '%s - %s' % (startTime.strftime('%H:%M'), endTime.strftime('%H:%M'))
            )

        self.addView(view)







