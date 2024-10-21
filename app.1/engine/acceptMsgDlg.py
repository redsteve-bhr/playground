# -*- coding: utf-8 -*-

from applib.gui import msg
import identificationRequestQueue


def acceptMsg(text, timeout=None, acceptReader=False, soundFile=None):
    """ Show accept message and accept card reads if *acceptReader* 
        is **True**. Card reads are put in the identification request
        queue. 
    """
    readerData = msg.passMsg(text, acceptReader=acceptReader, soundFile=soundFile)
    if (acceptReader and readerData):
        (valid, reader, decoder, data) = readerData
        identificationRequestQueue.addCardReaderRequest(valid, reader, decoder, data)
