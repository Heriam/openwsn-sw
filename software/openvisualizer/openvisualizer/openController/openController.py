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

    SLOTFRAME_DEFAULT        = 'default'

    OPT_ADD                  = 'add'
    OPT_DELETE               = 'delete'
    OPT_LIST                 = 'list'
    OPT_OVERWRITE            = 'overwrite'
    OPT_REMAP                = 'remap'
    OPT_CLEAR                = 'clear'

    PARAMS_BFRID             = 'BFRId'
    PARAMS_NEIGHBOR          = 'neighbor'
    PARAMS_BITINDEX          = 'bitIndex'
    PARAMS_TYPE              = 'type'
    PARAMS_SHARED            = 'shared'
    PARAMS_CELL              = 'cell'
    PARAMS_REMAPTOCELL       = 'remaptocell'

    TYPE_RX                  = 'Rx'
    TYPE_TX                  = 'Tx'
    TYPE_SE                  = 'Se'

    SLOTFRAME_LIST = [SLOTFRAME_DEFAULT]
    OPT_LIST = [OPT_ADD, OPT_OVERWRITE, OPT_REMAP, OPT_DELETE, OPT_LIST, OPT_CLEAR]
    TYPE_LIST = [TYPE_TX, TYPE_RX, TYPE_SE]

    def __init__(self, app):
        # log
        log.info("create instance")

        # store params
        self.stateLock      = threading.Lock()
        self.app            = app

        # test
        targetSlotFrame = self.SLOTFRAME_DEFAULT
        operation       = self.OPT_ADD
        params          = {
            self.PARAMS_CELL        : (2, 0),
            self.PARAMS_REMAPTOCELL : (2, 0),
            self.PARAMS_TYPE        : self.TYPE_TX,
            self.PARAMS_BITINDEX    : 3,
            self.PARAMS_NEIGHBOR    : '14-15-92-cc-00-00-00-03 (64b)',
            self.PARAMS_SHARED      : True,
            self.PARAMS_BFRID       : '0123456qw987SFG#$%^)(+|{":?><12ED'
        }
        testCMD = [targetSlotFrame, operation, params]
        self._sendSchedule('0002', testCMD)


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




