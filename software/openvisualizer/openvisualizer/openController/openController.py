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

    PARAMS_TRACKID           = 'trackID'
    PARAMS_NEIGHBOR          = 'neighbor'
    PARAMS_BITINDEX          = 'bitIndex'
    PARAMS_TYPE              = 'type'
    PARAMS_SHARED            = 'shared'
    PARAMS_CELL              = 'cells'
    PARAMS_REMAPTOCELL       = 'remaptocell'
    PARAMS_TXMOTEID          = 'txMoteID'
    PARAMS_RXMOTELIST        = 'rxMoteList'
    PARAMS_SLOTOFF           = 'slotOffset'
    PARAMS_CHANNELOFF        = 'channelOffset'

    SLOTFRAME_DEFAULT        = 1   #id of slotframe

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



#   =============== public ==========================


    def initiateSimSchedule(self):
        # initiate schedules
        log.info('initiate schedule')
        # Bit0, Slot4: 1 --> 2
        self._addDetSlot('0001', ['0002'], 4, 0)
        # Bit0, Slot5: 1 --> 2
        self._addDetSlot('0001', ['0002'], 5, 0)
        # Bit1, Slot6: 1 --> 3
        self._addDetSlot('0001', ['0003'], 6, 1)
        # Bit2, Slot7: 2 --> 3
        self._addDetSlot('0002', ['0003'], 7, 2)
        # Bit2, Slot8: 3 --> 2
        self._addDetSlot('0003', ['0002'], 8, 2)
        # Bit3, Slot9: 2 --> 4
        self._addDetSlot('0002', ['0004'], 9, 3)
        # Bit4, Slot10: 3 --> 4
        self._addDetSlot('0003', ['0004'], 10, 4)


    def installNewSchedule(self, scheduleDict):
        moteList    = self.app.getMoteList()
        slotFrame   = scheduleDict[self.CMD_TARGETSLOTFRAME]
        slotList    = scheduleDict[self.PARAMS_CELL]
        self._clearDetFrame(moteList, slotFrame)
        for slotEntry in slotList:
            self._addDetSlot(
                slotEntry[self.PARAMS_TXMOTEID],     # txMote
                slotEntry[self.PARAMS_RXMOTELIST],   # rxMoteList
                slotEntry[self.PARAMS_SLOTOFF],      # slotOffset
                slotEntry[self.PARAMS_BITINDEX],     # bitIndex
                self.OPT_ADD,                        # operation
                slotEntry[self.PARAMS_TRACKID],      # trackID
                slotFrame,                           # slotFrame
                slotEntry[self.PARAMS_CHANNELOFF],   # channelOffset
                slotEntry[self.PARAMS_SHARED]        # shared
            )


#   ================= private =======================
    # schedule operations

    def _addDetSlot(self, txMote, rxMoteList, slotOff, bitIndex, opt = OPT_ADD, trackID = 1, targetSlotFrame = SLOTFRAME_DEFAULT, channelOff = 0, shared = False):
        params = {
            self.PARAMS_CELL: (slotOff, channelOff),
            self.PARAMS_TYPE: self.TYPE_TX,
            self.PARAMS_BITINDEX: bitIndex,
            self.PARAMS_SHARED: shared,
            self.PARAMS_TRACKID: trackID,
        }
        if txMote:
            self._sendSchedule(txMote, [targetSlotFrame, opt, params])
        if rxMoteList:
            params[self.PARAMS_TYPE] = self.TYPE_RX
            for rxMote in rxMoteList:
                self._sendSchedule(rxMote, [targetSlotFrame, opt, params])

    def _remapDetSlot(self, txMote, rxMoteList, slotOff, remapSlotOff, channelOff = 0, remapChannel = 0, targetSlotFrame = SLOTFRAME_DEFAULT):
        params = {
            self.PARAMS_CELL: (slotOff, channelOff),
            self.PARAMS_REMAPTOCELL: (remapSlotOff, remapChannel)
        }
        if txMote:
            self._sendSchedule(txMote, [targetSlotFrame, self.OPT_REMAP, params])
        if rxMoteList:
            for rxMote in rxMoteList:
                self._sendSchedule(rxMote, [targetSlotFrame, self.OPT_REMAP, params])

    def _deleteDetSlot(self, txMote, rxMoteList, slotOff, channelOff = 0, targetSlotFrame = SLOTFRAME_DEFAULT):
        params = {
            self.PARAMS_CELL: (slotOff, channelOff),
        }
        if txMote:
            self._sendSchedule(txMote, [targetSlotFrame, self.OPT_DELETE, params])
        if rxMoteList:
            for rxMote in rxMoteList:
                self._sendSchedule(rxMote, [targetSlotFrame, self.OPT_DELETE, params])

    def _listDetSlot(self, moteList, targetSlotFrame = SLOTFRAME_DEFAULT):
        for moteId in moteList:
            self._sendSchedule(moteId, [targetSlotFrame, self.OPT_LIST])

    def _clearDetFrame(self, moteList, targetSlotFrame = SLOTFRAME_DEFAULT):
        for moteId in moteList:
            self._sendSchedule(moteId, [targetSlotFrame, self.OPT_CLEAR])

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


