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
        
        headerBytes = input[:3]
        
        # extract moteId and statusElem
        try:
           (moteId,statusElem) = struct.unpack('<HB',''.join([chr(c) for c in headerBytes]))
        except struct.error:
            raise ParserException(ParserException.DESERIALIZE,"could not extract moteId and statusElem from {0}".format(headerBytes))
        
        # log
        if log.isEnabledFor(logging.DEBUG):
            log.debug("moteId={0} statusElem={1}".format(moteId,statusElem))
        
        # jump the header bytes
        input = input[3:]
        
        # call the next header parser
        for key in self.fieldsParsingKeys:
            if statusElem==key.val:
            
                # log
                if log.isEnabledFor(logging.DEBUG):
                    log.debug("parsing {0}, ({1} bytes) as {2}".format(input,len(input),key.name))
                
                # parse byte array
                try:
                    fields = struct.unpack(key.structure,''.join([chr(c) for c in input]))                     
                except struct.error as err:
                    raise ParserException(
                            ParserException.DESERIALIZE,
                            "could not extract tuple {0} by applying {1} to {2}; error: {3}".format(
                                key.name,
                                key.structure,
                                u.formatBuf(input),
                                str(err)
                            )
                        )
                
                # map to name tuple
                returnTuple = self.named_tuple[key.name](*fields)

                # log
                if log.isEnabledFor(logging.DEBUG):
                    log.debug("parsed into {0}".format(returnTuple))
                
                # map to name tuple
                return 'status', returnTuple
        
        # if you get here, no key was found
        raise ParserException(ParserException.NO_KEY, "type={0} (\"{1}\")".format(
            input[0],
            chr(input[0])))
    
    #======================== private =========================================
    
    def _addFieldsParser(self,index=None,val=None,name=None,structure=None,fields=None):
    
        # add to fields parsing keys
        self.fieldsParsingKeys.append(FieldParsingKey(index,val,name,structure,fields))
        
        # define named tuple
        self.named_tuple[name] = collections.namedtuple("Tuple_"+name, fields)