from engine import dynButtons
from plugins.timecards.timecards import TimecardDialog


#
#
# Support functions for dynamic buttons
#
#
class TimecardAction(dynButtons.Action):

    def getName(self):
        return 'timecard'

    def getButtonText(self, actionParam, employee, languages):
        return _('Timecard Catchup')

    def getDialog(self, actionParam, employee, languages):
        diag = TimecardDialog()

        diag.data = {
            'Emp': employee,
            'IsStandalone': True,
            'SendAttestationResponse': False
        }

        return diag

    def isEmployeeRequired(self, actionParam):
        return True

    def getXsd(self):
        return """
        """

    def getHelp(self):
        return """
        Timecard Action.

        Example::

            <button>
                <pos>1</pos>
                <action>
                    <timecard />
                </action>
            </button>

        """


def loadPlugin():
    dynButtons.registerAction(TimecardAction())
