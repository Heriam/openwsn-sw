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

    PARAMS_TRACKID           = 'trackId'
    PARAMS_NEIGHBOR          = 'neighbor'
    PARAMS_BITINDEX          = 'bitIndex'
    PARAMS_TYPE              = 'type'
    PARAMS_SHARED            = 'shared'
    PARAMS_CELL              = 'cell'
    PARAMS_REMAPTOCELL       = 'remaptocell'

    SLOTFRAME_DEFAULT        = 0

    OPT_ADD                  = 'add'
    OPT_OVERWRITE            = 'overwrite'
    OPT_REMAP                = 'remap'
    OPT_DELETE               = 'delete'
    OPT_LIST                 = 'list'
    OPT_CLEAR                = 'clear'
    OPT_ALL = [OPT_ADD, OPT_OVERWRITE, OPT_REMAP, OPT_DELETE, OPT_LIST, OPT_CLEAR]

    TYPE_OFF                 = 'off'
    TYPE_TX                  = 'tx'
    TYPE_RX                  = 'rx'
    TYPE_TXRX                = 'txrx'
    TYPE_SERIALRX            = 'serialrx'
    TYPE_MORESERIALRX        = 'moreserx'
    TYPE_ALL = [TYPE_OFF, TYPE_TX, TYPE_RX, TYPE_TXRX, TYPE_SERIALRX, TYPE_MORESERIALRX]


    def __init__(self, app):
        # log
        log.info("create instance")

        # store params
        self.stateLock      = threading.Lock()
        self.app            = app


    def _initiateSimSchedule(self):
        # initiate schedules
        log.info('initiate schedule')
        iniSlot = 10
        # Bit0, Slot4: 1 --> 2
        targetSlotFrame = self.SLOTFRAME_DEFAULT
        operation = self.OPT_ADD
        params = {
            self.PARAMS_CELL: (iniSlot, 0),
            self.PARAMS_TYPE: self.TYPE_TX,
            self.PARAMS_BITINDEX: 0,
            self.PARAMS_SHARED: False,
            self.PARAMS_TRACKID: 1,
            }
        self._sendSchedule('0001',[targetSlotFrame, operation, params])
        params[self.PARAMS_TYPE] = self.TYPE_RX
        self._sendSchedule('0002', [targetSlotFrame, operation, params])
        iniSlot+=1
        # Bit1, Slot5: 1 --> 3
        params = {
            self.PARAMS_CELL: (iniSlot, 0),
            self.PARAMS_TYPE: self.TYPE_TX,
            self.PARAMS_BITINDEX: 1,
            self.PARAMS_SHARED: False,
            self.PARAMS_TRACKID: 1,
        }
        self._sendSchedule('0001', [targetSlotFrame, operation, params])
        params[self.PARAMS_TYPE] = self.TYPE_RX
        self._sendSchedule('0003', [targetSlotFrame, operation, params])
        iniSlot+=1
        # Bit2, Slot6: 2 --> 3
        params = {
            self.PARAMS_CELL: (iniSlot, 0),
            self.PARAMS_TYPE: self.TYPE_TX,
            self.PARAMS_BITINDEX: 2,
            self.PARAMS_SHARED: False,
            self.PARAMS_TRACKID: 1,
        }
        self._sendSchedule('0002', [targetSlotFrame, operation, params])
        params[self.PARAMS_TYPE] = self.TYPE_RX
        self._sendSchedule('0003', [targetSlotFrame, operation, params])
        iniSlot += 1
        # Bit2, Slot7: 3 --> 2
        params = {
            self.PARAMS_CELL: (iniSlot, 0),
            self.PARAMS_TYPE: self.TYPE_TX,
            self.PARAMS_BITINDEX: 2,
            self.PARAMS_SHARED: False,
            self.PARAMS_TRACKID: 1,
        }
        self._sendSchedule('0003', [targetSlotFrame, operation, params])
        params[self.PARAMS_TYPE] = self.TYPE_RX
        self._sendSchedule('0002', [targetSlotFrame, operation, params])
        iniSlot += 1
        # Bit3, Slot8: 2 --> 4
        params = {
            self.PARAMS_CELL: (iniSlot, 0),
            self.PARAMS_TYPE: self.TYPE_TX,
            self.PARAMS_BITINDEX: 3,
            self.PARAMS_SHARED: False,
            self.PARAMS_TRACKID: 1,
        }
        self._sendSchedule('0002', [targetSlotFrame, operation, params])
        params[self.PARAMS_TYPE] = self.TYPE_RX
        self._sendSchedule('0004', [targetSlotFrame, operation, params])
        iniSlot += 1
        # Bit4, Slot9: 3 --> 4
        params = {
            self.PARAMS_CELL: (iniSlot, 0),
            self.PARAMS_TYPE: self.TYPE_TX,
            self.PARAMS_BITINDEX: 4,
            self.PARAMS_SHARED: False,
            self.PARAMS_TRACKID: 1,
        }
        self._sendSchedule('0003', [targetSlotFrame, operation, params])
        params[self.PARAMS_TYPE] = self.TYPE_RX
        self._sendSchedule('0004', [targetSlotFrame, operation, params])


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



