from engine import dynButtons
from plugins.schedules.scheduleOverride import ScheduleOverrideDialog
from plugins.schedules.viewSchedules import ViewSchedulesDialog


class ViewSchedulesAction(dynButtons.Action):

    def getName(self):
        return 'schedule.view'

    def getButtonText(self, actionParam, employee, languages):
        return _('View Schedules')

    def getDialog(self, actionParam, employee, languages):
        return ViewSchedulesDialog(employee)

    def isEmployeeRequired(self, actionParam):
        return True

    def getHelp(self):
        return """
        View the employees offline schedules.

        Example::

            <button>
                <pos>6</pos>
                <action>
                    <schedule.view/>
                </action>
            </button>

        """


#
#
# Support functions for dynamic buttons
#
#
class ScheduleOverrideAction(dynButtons.Action):

    def getName(self):
        return 'schedule.override'

    def getButtonText(self, actionParam, employee, languages):
        return _('Override Schedule')

    def getDialog(self, actionParam, employee, languages):
        return ScheduleOverrideDialog(actionParam, employee, languages)

    def isEmployeeRequired(self, actionParam):
        return True

    def getXsd(self):
        return """
        """

    def getHelp(self):
        return """
        Schedule Override Action.

        Allows a supervisor to raise Punch Restrictions for the next Punch by 
        the selected Employee

        Example::

            <button>
                <pos>1</pos>
                <action>
                    <schedule.override />
                </action>
                <options>
                    <switchEmployee />
                </options>
            </button>

        """

def loadPlugin():
    dynButtons.registerAction(ViewSchedulesAction())
    dynButtons.registerAction(ScheduleOverrideAction())
