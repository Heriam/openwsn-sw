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

    CMD_TARGETSLOTFRAME      = 'slotFrame'
    CMD_OPERATION            = 'operation'
    CMD_PARAMS               = 'params'

    PARAMS_BFRID             = 'BFRId'
    PARAMS_NEIGHBOR          = 'neighbor'
    PARAMS_BITINDEX          = 'bitIndex'
    PARAMS_TYPE              = 'type'
    PARAMS_SHARED            = 'shared'
    PARAMS_CELLLIST          = 'cellList'
    PARAMS_REMAPTOCELL       = 'remaptocell'

    SLOTFRAME_DEFAULT        = 0

    OPT_ADD                  = 0
    OPT_OVERWRITE            = 1
    OPT_REMAP                = 2
    OPT_DELETE               = 3
    OPT_LIST                 = 4
    OPT_CLEAR                = 5

    TYPE_RX                  = 0
    TYPE_TX                  = 1


    def __init__(self, app):
        # log
        log.info("create instance")

        # store params
        self.stateLock      = threading.Lock()
        self.app            = app

        # todo: remove test
        targetSlotFrame = self.SLOTFRAME_DEFAULT
        operation       = self.OPT_ADD
        params          = {
            self.PARAMS_CELLLIST    : [(2, 0), (5, 0)],
            self.PARAMS_REMAPTOCELL : [(3, 0), (6, 0)],
            self.PARAMS_TYPE        : self.TYPE_TX,
            self.PARAMS_BITINDEX    : 3,
            self.PARAMS_NEIGHBOR    : '14-15-92-cc-00-00-00-03 (64b)',
            self.PARAMS_SHARED      : True,
            self.PARAMS_BFRID       : '0123456qw987SFG#$%^)(+|{":?><12ED'
        }
        self.testCMD = [targetSlotFrame, operation, params]


    def _sendSchedule(self, moteid, command):
        # send command [<targetSlotFrame>, <operation>, <params>] to <moteid>
        log.info('Send Schedule Command to moteid {0}'.format(moteid))
        ms = self.app.getMoteState(moteid)
        if ms:
            log.debug('Found mote {0} in moteStates'.format(moteid))
            ms.triggerAction([moteState.moteState.INSTALL_SCHEDULE] + command)
            return '{"result" : "success"}'
        else:
            log.debug('Mote {0} not found in moteStates'.format(moteid))
            return '{"result" : "fail"}'




