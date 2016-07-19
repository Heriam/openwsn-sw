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
    
    HEADER_LENGTH       = 4
    
    def __init__(self):
        
        # log
        log.info("create instance")
        
        # initialize parent class
        Parser.Parser.__init__(self,self.HEADER_LENGTH)
        

    
    #======================== public ==========================================
    
    def parseInput(self,input):
        
        # log
        if log.isEnabledFor(logging.DEBUG):
            log.debug("received input={0}".format(input))
        
        # ensure input not short longer than header
        self._checkLength(input)
        
        print input