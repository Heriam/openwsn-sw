# Copyright (c) 2010-2013, Regents of the University of California.
# All rights reserved.
#
# Released under the BSD 3-Clause license as published at the link below.
# https://openwsn.atlassian.net/wiki/display/OW/License

'''
Contains openController component for centralized scheduling of the motes. It uses self.app.motestates to communicate with motes
'''

import logging
import json
log = logging.getLogger('scheduleMgr')
log.setLevel(logging.ERROR)
log.addHandler(logging.NullHandler())

import threading
from openvisualizer.moteState.moteState import moteState as msParam


class scheduleMgr():

    # schedule.json keys
    KEY_SLOTFRAMES               = 'slotFrames'
    KEY_ROOTLIST                 = 'rootList'

    # schedule parameters
    PARAMS_FRAMEID           = 'frameID'
    PARAMS_TRACKID           = 'trackID'
    PARAMS_NEIGHBOR          = 'neighbor'
    PARAMS_BITINDEX          = 'bitIndex'
    PARAMS_TYPE              = 'type'
    PARAMS_SHARED            = 'shared'
    PARAMS_CELL              = 'cells'
    PARAMS_REMAPSLOTOFF      = 'remapSlotOff'
    PARAMS_REMAPCHANOFF      = 'remapChanOff'
    PARAMS_TXMOTEID          = 'txMoteID'
    PARAMS_RXMOTELIST        = 'rxMoteList'
    PARAMS_SLOTOFF           = 'slotOffset'
    PARAMS_CHANNELOFF        = 'channelOffset'
    PARAMS_FRAMELENGTH       = 'frameLength'

    # default values
    SLOTFRAME_DEFAULT        = '1'
    FRAMELENGTH_DEFAULT      = 20

    # operation types
    OPT_ADD                  = 'add'
    OPT_OVERWRITE            = 'overwrite'
    OPT_REMAP                = 'remap'
    OPT_DELETE               = 'delete'
    OPT_LIST                 = 'list'
    OPT_CLEAR                = 'clear'
    OPT_SETFRAMELENGTH       = 'setFrameLength'
    OPT_ALL = [OPT_ADD, OPT_OVERWRITE, OPT_REMAP, OPT_DELETE, OPT_LIST, OPT_CLEAR, OPT_SETFRAMELENGTH]

    # cell types
    TYPE_OFF                 = 'off'
    TYPE_TX                  = 'tx'
    TYPE_RX                  = 'rx'
    TYPE_TXRX                = 'txrx'
    TYPE_SERIALRX            = 'serialrx'
    TYPE_MORESERIALRX        = 'moreserx'
    TYPE_ALL = [TYPE_OFF, TYPE_TX, TYPE_RX, TYPE_TXRX, TYPE_SERIALRX, TYPE_MORESERIALRX]


    def __init__(self, moteDriver):

        # log
        log.info("create instance")

        # local variables
        self.stateLock         = threading.Lock()
        self.frameLen          = self.FRAMELENGTH_DEFAULT
        self.frameID           = self.SLOTFRAME_DEFAULT
        self.runningFrame      = []
        self.md                = moteDriver

        # give this thread a name
        self.name = 'scheduleMgr@{0}'.format(self.frameID)



    #   =============== public ==========================


    def installFrame(self, newSlotFrame):
        '''
        installs the slotFrame

        :param: newSlotFrame: a slotFrameInfo

        '''

        # install slots
        for slotEntry in newSlotFrame:
            self._slotOperation(self.OPT_ADD, slotEntry)

    def clearBIERslots(self):
        '''
        clears BIER slots on all motes.

        '''

        self._frameOperation(self.OPT_CLEAR)


    def clearSharedSlots(self):
        '''
        clears Shared slots on all motes.

        '''

        for slot in self.runningFrame[:]:
            if slot[self.PARAMS_SHARED]:
                self._slotOperation(self.OPT_DELETE, slot)


    def getRunningFrame(self):
        '''
        updates and returns self.runningFrame
        :returns: self.runningFrame

        '''
        self._updateRunningFrame()
        return self.runningFrame

    def setFrameID(self, frameID):




    #   ================= private =======================



    def _sameSlot(self, slota, slotb):
        '''
        checks if slot A and slot B are the same slot according to slotOffset and channelOffset

        :param: slota, slotb: two slots to check identity
        :returns: ture or false on identity
        '''

        same = False
        if slota[self.PARAMS_SLOTOFF] == slotb[self.PARAMS_SLOTOFF]:
            if slota[self.PARAMS_CHANNELOFF] == slotb[self.PARAMS_CHANNELOFF]:
                same = True
        return same

    def _existSlot(self, slot, slotList):
        '''
        checks if the given slot exists in the given slotList

        :param: slotList: a list of slotInfo elements
        :returns: ture or false on existence
        '''

        existAs = None
        for slotElem in slotList:
            if self._sameSlot(slot, slotElem):
                existAs = slotElem
        return existAs

    def _isAtInit(self):
        '''
        checks if the network is initiated
        
        :returns: false if the 6tisch minimal active cell at slot ZERO is scheduled
        '''
        
        atInit = True
        for slotElem in self.runningFrame:
            if slotElem[self.PARAMS_SLOTOFF] == 0:
                atInit = False
        return atInit

    def _isAvailable(self, slot):
        '''
        checks if the given slot is available on the given slotFrame

        :returns: ture or false on availability
        '''
        
        available = True
        if self._existSlot(slot, self.runningFrame):
            available = False
        return available

    #   ============================ Mote interactions ============================


    def _slotOperation(self, operation, slotInfoDict):
        '''
        configures a slot

        :param: operation: specifys the action to execute, e.g, add,delete,etc.
                slotInfoDict: parameters of the slot to operate
        '''

        shared     = slotInfoDict[self.PARAMS_SHARED]
        if shared:
            if operation == self.OPT_ADD and not self._isAvailable(slotInfoDict):
                return
            slotInfoDict[self.PARAMS_TYPE] = self.TYPE_TXRX
            self.md.cmdAllMotes([msParam.INSTALL_SCHEDULE, self.frameID, operation, slotInfoDict])

        else:
            txMote     = slotInfoDict[self.PARAMS_TXMOTEID]
            rxMoteList = slotInfoDict[self.PARAMS_RXMOTELIST]
            if txMote in rxMoteList:
                rxMoteList.remove(txMote)
            if txMote:
                slotInfoDict[self.PARAMS_TYPE] = self.TYPE_TX
                self.md.cmdMote(txMote, [msParam.INSTALL_SCHEDULE, self.frameID, operation, slotInfoDict])

            if rxMoteList:
                slotInfoDict[self.PARAMS_TYPE] = self.TYPE_RX
                for rxMote in rxMoteList:
                    self.md.cmdMote(rxMote, [msParam.INSTALL_SCHEDULE, self.frameID, operation, slotInfoDict])

            slotInfoDict.pop(self.PARAMS_TYPE)

    def _frameOperation(self, operation, slotFrameInfo = None, moteList = "all"):
        '''
        configures a slotFrame

        :param: slotFrameInfo: an element of stored slotFrames
        '''

        if moteList== 'all':
            self.md.cmdAllMotes([msParam.INSTALL_SCHEDULE, self.frameID, operation, slotFrameInfo])
        else:
            for moteID in moteList:
                self.md.cmdMote(moteID, [msParam.INSTALL_SCHEDULE, self.frameID, operation, slotFrameInfo])

    def _updateRunningFrame(self):
        '''
        gets runningSlotFrame info
        '''

        self.runningFrame[:] = []

        # gets the schedule of every mote
        for ms in self.md.moteStates:
            moteID = self.md.getMoteID(ms)
            moteSchedule = json.loads(ms.getStateElem(ms.ST_SCHEDULE).toJson('data'))

            # removes unscheduled cells
            for slot in moteSchedule[:]:
                if slot[self.PARAMS_TYPE] == '0 (OFF)':
                    moteSchedule.remove(slot)

            for slotEntry in moteSchedule:
                t = slotEntry[self.PARAMS_TYPE]
                exist = self._existSlot(slotEntry, self.runningFrame)
                if exist:
                    if t.startswith('1'):
                        exist[self.PARAMS_TXMOTEID] = moteID
                    elif t.startswith('2'):
                        exist[self.PARAMS_RXMOTELIST].append(moteID)
                else:
                    for i in ['lastUsedAsn','numTx','neighbor','numRx','numTxACK']:
                        slotEntry.pop(i)
                    if t.startswith('1'):
                        slotEntry.pop('type')
                        slotEntry[self.PARAMS_TXMOTEID] = moteID
                        slotEntry[self.PARAMS_RXMOTELIST] = []
                    elif t.startswith('2'):
                        slotEntry.pop('type')
                        slotEntry[self.PARAMS_TXMOTEID] = None
                        slotEntry[self.PARAMS_RXMOTELIST] = [moteID]
                    self.runningFrame.append(slotEntry)