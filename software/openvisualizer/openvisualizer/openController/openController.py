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
    PARAMS_CELLTYPE          = 'type'
    PARAMS_SHARED            = 'shared'
    PARAMS_CELL              = 'cell'
    PARAMS_REMAPTOCELL       = 'remaptocell'

    OPT_ADD                  = 'add'
    OPT_DELETE               = 'delete'
    OPT_LIST                 = 'list'
    OPT_OVERWRITE            = 'overwrite'
    OPT_REMAP                = 'remap'
    OPT_CLEAR                = 'clear'

    SLOTFRAME_DEFAULT        = 'default'
    SLOTFRAME_CONTROL        = 'control'
    SLOTFRAME_DATA           = 'data'
    SLOTFRAME_ALL            = 'all'

    OPT_LIST = [OPT_ADD, OPT_OVERWRITE, OPT_REMAP, OPT_DELETE, OPT_LIST, OPT_CLEAR]
    SLOTFRAME_LIST = [SLOTFRAME_DEFAULT, SLOTFRAME_CONTROL, SLOTFRAME_DATA, SLOTFRAME_ALL]


    def __init__(self, app):
        # log
        log.info("create instance")

        # store params
        self.stateLock      = threading.Lock()
        self.app            = app

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




