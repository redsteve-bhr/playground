from engine import dynButtons
from plugins.transfers.transfer import TransferDialog


class TransferAction(dynButtons.Action):

    def getName(self):
        return 'transfer'

    def getButtonText(self, actionParam, employee, languages):
        return _('Transfer')

    def getDialog(self, actionParam, employee, languages):
        if hasattr(actionParam, 'getList'):
            promptLevels = set(actionParam.getList('promptLevel'))
        else:
            promptLevels = set()

        transferType = None
        if hasattr(actionParam, 'getParam'):
            transferType = actionParam.getParam('type')

        if transferType is None or transferType == '':
            transferType = 'transfer'

        diag = TransferDialog()

        diag.data = {
            'Emp': employee,
            'PromptLevels': promptLevels,
            'IsStandalone': True,
            'Type': transferType
        }

        return diag

    def isEmployeeRequired(self, actionParam):
        return True

    def getHelp(self):
        return """
        Show selection job levels / job codes menu to add transaction data to a clocking
        Note: If no <promptLevel> tags are specified then all job categories / levels are loaded

        Example::

            <button>
                <pos>1</pos>
                <action>
                    <transfer>
                        <promptLevel>1</promptLevel>
                        <promptLevel>3</promptLevel>
                    </transfer>
                </action>
            </button>

        """


def loadPlugin():
    dynButtons.registerAction(TransferAction())
