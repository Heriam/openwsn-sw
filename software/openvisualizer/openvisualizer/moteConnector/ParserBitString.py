# Copyright (c) 2010-2013, Regents of the University of California. 
# All rights reserved. 
#  
# Released under the BSD 3-Clause license as published at the link below.
# https://openwsn.atlassian.net/wiki/display/OW/License
import logging
log = logging.getLogger('ParserString')
log.setLevel(logging.ERROR)
log.addHandler(logging.NullHandler())

import collections
import struct

from ParserException import ParserException
import Parser
import openvisualizer.openvisualizer_utils as u


class ParserBitString(Parser.Parser):
    
    HEADER_LENGTH       = 5
    
    def __init__(self):
        
        # log
        log.info("create instance")
        
        # initialize parent class
        Parser.Parser.__init__(self,self.HEADER_LENGTH)

    
    #======================== public ==========================================
    
    def parseInput(self,input):

        # ensure input not short longer than header
        self._checkLength(input)

        headerBytes = input[:5]
        try:
            (moteId, trackId, seq) = struct.unpack('<HBH', ''.join([chr(c) for c in headerBytes]))
        except struct.error:
            raise ParserException(ParserException.DESERIALIZE,
                                  "could not extract trackId and moteId from {0}".format(headerBytes))

        asnBytes = input[5:10]
        try:
            (asn) = struct.unpack('<HHB',''.join([chr(c) for c in asnBytes]))
        except struct.error:
            raise ParserException(ParserException.DESERIALIZE,
                                  "could not extract asn from {0}".format(asnBytes))
        bitBytes = (input[10:])
        returnTuple = (trackId,moteId,asn,seq,bitBytes)

        return 'bitString', returnTuple