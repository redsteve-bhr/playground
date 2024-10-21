# -*- coding: utf-8 -*-
#
# Copyright 2013 Grosvenor Technology
#
import itg
from engine import dynButtons


class StaticTextDialog(itg.Dialog):

    def __init__(self, employee, title, text):
        super(StaticTextDialog, self).__init__()
        if (not title):
            title = ''
        if (not text):
            text = ''
        if (employee != None):
            text  = text.replace('$EMP', employee.getName())
            title = title.replace('$EMP', employee.getName())
        view = itg.TextView(title, text, 'text/plain')
        view.setButton(_('OK'), itg.ID_OK, self.quit)
        self.addView(view)


class StaticHTMLDialog(itg.Dialog):

    def __init__(self, employee, title, text):
        super(StaticHTMLDialog, self).__init__()
        if (not title):
            title = ''
        if (not text):
            text = ''
        if (employee != None):
            text  = text.replace('$EMP', employee.getName())
            title = title.replace('$EMP', employee.getName())
        view = itg.TextView(title, text, 'text/html')
        view.setButton(_('OK'), itg.ID_OK, self.quit)
        self.addView(view)
           
#
# Support functions for dynamic buttons
#
#

class StaticTextAction(dynButtons.Action):
    
    def getName(self):
        return 'static.text'
    
    def getButtonText(self, actionParam, employee, languages):
        return 'Static Text'
    
    def getDialog(self, actionParam, employee, languages):
        if (hasattr(actionParam, 'getParam')):
            title = actionParam.getParam('title')
            text  = actionParam.getParam('text')
        else:
            textLines = actionParam.splitlines()
            if (len(textLines) > 1):
                title = textLines[0]
                text  = '\n'.join(textLines[1:])
            else:
                title = ''
                text = actionParam
        return StaticTextDialog(employee, title, text)

    def getXsd(self):
        return """
            <xs:complexType>
                <xs:all>
                    <xs:element name="title" type="xs:string" />
                    <xs:element name="text" type="xs:string" />
                </xs:all>
            </xs:complexType>
        """

    def getHelp(self):
        return """
        Display static text. 

        This action displays static text and is mainly intended for 
        demonstration purposes. The static text needs to be placed 
        in a *text* tag inside the action tag.
        
        Example::
        
            <button>
                <pos>1</pos>
                <action>
                    <static.text>
                        <title>Static Title</title>
                        <text>Static Text
            -----------
         
            This is plain text with newlines and everything.
                    
                        </text>
                    </static.text>
                </action>
            </button>

        """        

class StaticHTMLAction(dynButtons.Action):
    
    def getName(self):
        return 'static.html'
    
    def getButtonText(self, actionParam, employee, languages):
        return 'Static HTML'
    
    def getDialog(self, actionParam, employee, languages):
        if (hasattr(actionParam, 'getParam')):
            title = actionParam.getParam('title')
            text  = actionParam.getParam('text')
        else:
            textLines = actionParam.splitlines()
            if (len(textLines) > 1):
                title = textLines[0]
                text  = '\n'.join(textLines[1:])
            else:
                title = ''
                text = actionParam
        return StaticHTMLDialog(employee, title, text)

    def getXsd(self):
        return """
            <xs:complexType>
                <xs:all>
                    <xs:element name="title" type="xs:string" />
                    <xs:element name="text" type="xs:string" />
                </xs:all>
            </xs:complexType>
        """

    def getHelp(self):
        return """
        Display static HTML. 

        This action displays static HTML and is mainly intended for 
        demonstration purposes. The static HTML needs to be placed
        in a *text* tag inside the action tag.
        
        Example::
        
            <button>
                <pos>1</pos>
                <action>
                    <static.html>
                        <title>Static Title</title>
                        <text><![CDATA[<html><body>
                            <h1>Static HTML</h1>

                            This is HTML text with an item list: 
                             <ul>
                                 <li>Item1</li>
                                 <li>item2</li>
                                 <li>item3</li>                                 
                             </ul>
                        </body></html>
                        ]]></text>
                    </static.html>
                </action>
            </button>

        """        


def loadPlugin():
    dynButtons.registerAction(StaticTextAction())
    dynButtons.registerAction(StaticHTMLAction())


