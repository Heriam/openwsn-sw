# Copyright (c) 2010-2013, Regents of the University of California.
# All rights reserved.
#
# Released under the BSD 3-Clause license as published at the link below.
# https://openwsn.atlassian.net/wiki/display/OW/License

'''
Contains
'''

import logging
log = logging.getLogger('openController')
log.setLevel(logging.ERROR)
log.addHandler(logging.NullHandler())
import threading
from openvisualizer.moteState import moteState


class openController():

    OV_SERIAL            = 'serial'
    OV_MOTEID            = 'moteID'
    OV_CM                = 'command'
    OV_IPV6ADDR          = 'ipv6Addr'
    OV_MACADDR           = 'macAddr'

    CM_TARGETSLOTFRAME   = 'slotFrame'
    CM_OPERATION         = 'operation'
    CM_PARAMS            = 'params'

    PARAMS_SLOTOFFSET        = 'slotOffset'
    PARAMS_CELLTYPE          = 'type'
    PARAMS_SHARED            = 'shared'
    PARAMS_CHANNELOFFSET     = 'channelOffset'
    PARAMS_NEIGHBOR          = 'neighbor'
    PARAMS_BIT               = 'bit'


    def __init__(self, moteStates):
        # log
        log.info("create instance")

        # store params
        self.stateLock = threading.Lock()
        self.moteStates     = moteStates
        self.motelist       = []
        self.scheduledict   = {}
        self.trackdict      = {}



    def _sendScheduleCmd(self, ovmsg):





