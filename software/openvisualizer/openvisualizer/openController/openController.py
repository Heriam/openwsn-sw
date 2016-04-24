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

    PARAMS_NEIGHBOR          = 'neighbor'
    PARAMS_BIT               = 'bit'
    PARAMS_CELLTYPE          = 'type'
    PARAMS_SHARED            = 'shared'
    PARAMS_SLOTOFFSET        = 'slotOffset'
    PARAMS_CHANNELOFFSET     = 'channelOffset'

    OPT_ADD                  = 'add'
    OPT_DELETE               = 'delete'
    OPT_LIST                 = 'list'
    OPT_OVERWRITE            = 'overwrite'
    OPT_REMAP                = 'remap'
    OPT_CLEAR                = 'clear'

    OPT_ALL = [OPT_ADD, OPT_OVERWRITE, OPT_REMAP, OPT_DELETE, OPT_LIST, OPT_CLEAR]


    def __init__(self, app):
        # log
        log.info("create instance")

        # store params
        self.stateLock      = threading.Lock()
        self.app            = app

    def _sendSchedule(self, moteid, command):
        # send command [<actionType>, <operation>, <params>, <targetSlotFrame>] to <moteid>
        log.info('Send Schedule Command to moteid {0}'.format(moteid))
        ms = self.app.getMoteState(moteid)
        if ms:
            log.debug('Found mote {0} in moteStates'.format(moteid))
            ms.triggerAction(command)
            return '{"result" : "success"}'
        else:
            log.debug('Mote {0} not found in moteStates'.format(moteid))
            return '{"result" : "fail"}'




