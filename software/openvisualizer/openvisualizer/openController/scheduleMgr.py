# Copyright (c) 2010-2013, Regents of the University of California.
# All rights reserved.
#
# Released under the BSD 3-Clause license as published at the link below.
# https://openwsn.atlassian.net/wiki/display/OW/License

'''
Contains openController component for centralized scheduling of the motes. It uses self.app.motestates to communicate with motes
'''

import logging
log = logging.getLogger('scheduleMgr')
log.setLevel(logging.ERROR)
log.addHandler(logging.NullHandler())
import threading
from openvisualizer.eventBus.eventBusClient import eventBusClient


class scheduleMgr(eventBusClient):

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
    CHANNELOFF_DEFAULT       = 0
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


    def __init__(self, frameID):

        # log
        log.info("create instance")

        # local variables
        self.stateLock         = threading.Lock()
        self.frameLen          = self.FRAMELENGTH_DEFAULT
        self.frameID           = frameID
        self.runningFrame      = []
        self.firstAvailableSlot= 4

        # give this thread a name
        self.name = 'scheduleMgr@{0}'.format(self.frameID)

        # initiate parent class
        eventBusClient.__init__(
            self,
            self.name,
            registrations=[
                {
                    'sender'  : self.WILDCARD,
                    'signal'  : 'installTrack',
                    'callback': self._installNewTrack
                }
            ]
        )


    #   =============== public ==========================


    def installFrame(self, newFrameInfo, rootList):
        '''
        installs the slotFrame

        :param: newSlotFrame: a slotFrameInfo

        '''
        # set parameters
        if rootList and self._isAtInit():
            self._frameOperation(self.OPT_SETFRAMELENGTH, newFrameInfo, rootList)
            self.frameLen = newFrameInfo[self.PARAMS_FRAMELENGTH]

        # install slots
        for slotEntry in newFrameInfo[self.PARAMS_CELL]:
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
            if slot[self.PARAMS_SHARED] and slot[self.PARAMS_SLOTOFF]:
                self._slotOperation(self.OPT_DELETE, slot)


    def getRunningFrame(self):
        '''
        updates and returns self.runningFrame
        :returns: self.runningFrame

        '''
        with self.stateLock:
            self._updateRunningFrame()

        schedule = {self.frameID: {
             self.PARAMS_FRAMELENGTH: self.frameLen,
             self.PARAMS_CELL: self.runningFrame}}

        return schedule


    def getFrameID(self):
        '''
        gets slotFrame ID

        '''
        return self.frameID

    def getFrameLen(self):
        '''
        gets slotFrame length

        '''
        return self.frameLen



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
        for slotElem in self.runningFrame[:]:
            if slotElem[self.PARAMS_SLOTOFF] == 0:
                atInit = False
        return atInit

    def _isAvailable(self, slot):
        '''
        checks if the given slot is available on the given slotFrame

        :returns: ture or false on availability
        '''
        
        available = True
        if self._existSlot(slot, self.runningFrame[:]):
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
            self._cmdAllMotes(['schedule',
                               self.frameID,
                               operation,
                               slotInfoDict])

        else:
            txMote     = slotInfoDict[self.PARAMS_TXMOTEID]
            rxMoteList = slotInfoDict[self.PARAMS_RXMOTELIST]
            if txMote in rxMoteList:
                rxMoteList.remove(txMote)
            if txMote:
                slotInfoDict[self.PARAMS_TYPE] = self.TYPE_TX
                self._cmdMote([txMote],
                               ['schedule',
                               self.frameID,
                               operation,
                               slotInfoDict])

            if rxMoteList:
                slotInfoDict[self.PARAMS_TYPE] = self.TYPE_RX
                self._cmdMote(rxMoteList,
                               ['schedule',
                               self.frameID,
                               operation,
                               slotInfoDict])

            slotInfoDict.pop(self.PARAMS_TYPE)

    def _frameOperation(self, operation, slotFrameInfo = None, moteList = "all"):
        '''
        configures a slotFrame

        :param: slotFrameInfo: an element of stored slotFrames

        '''

        if moteList== 'all':
            self._cmdAllMotes(['schedule',
                               self.frameID, operation,
                               slotFrameInfo])
        else:
            self._cmdMote(moteList,
                           ['schedule',
                           self.frameID, operation,
                           slotFrameInfo])

    def _cmdAllMotes(self, cmd):

        #dispatch command
        self.dispatch(
            signal = 'cmdAllMotes',
            data   = cmd
        )

    def _cmdMote(self, motelist, cmd):
        '''
        :param: cmd: ['motelist':[], 'cmd':]

        '''

        #dispatch command
        self.dispatch(
            signal = 'cmdMote',
            data   = {
                'motelist': motelist,
                'cmd'     : cmd
            }
        )

    def _updateRunningFrame(self):
        '''
        updates runningSlotFrame info
        '''

        self.runningFrame[:] = []

        returnVal  = self._dispatchAndGetResult(
            signal = 'getStateElem',
            data   = 'Schedule'
        )

        # gets the schedule of every mote
        for mote64bID, moteSchedule in returnVal.items():
            moteID = ''.join(['%02x' % b for b in mote64bID[6:]])
            # removes unscheduled cells
            for slotEntry in moteSchedule[:]:
                if slotEntry[self.PARAMS_TYPE] == '0 (OFF)':
                    moteSchedule.remove(slotEntry)
                    continue
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

    def _installOnFirstAvailableSlot(self, slotInfo):

        slotInfo[self.PARAMS_SLOTOFF] = self.firstAvailableSlot
        while not self._isAvailable(slotInfo):
            self.firstAvailableSlot += 1
            slotInfo[self.PARAMS_SLOTOFF] = self.firstAvailableSlot

        self._slotOperation(self.OPT_ADD, slotInfo)
        self.firstAvailableSlot +=1

    # ========================= eventbus ===================================

    def _installNewTrack(self,sender,signal,data):

        newTrack = data
        trackID  = newTrack.graph['trackID']
        edges = newTrack.graph['orderList']
        for (txMote, rxMote) in edges:
            txMoteID = ''.join(['%02x' % b for b in txMote[6:]])
            rxMoteID = ''.join(['%02x' % b for b in rxMote[6:]])
            bitIndex = newTrack[txMote][rxMote]['bitIndex']
            newSlotInfo = {
                self.PARAMS_TXMOTEID   : txMoteID,
                self.PARAMS_RXMOTELIST : [rxMoteID],
                self.PARAMS_BITINDEX   : bitIndex,
                self.PARAMS_TRACKID    : trackID,
                self.PARAMS_SHARED     : False,
                self.PARAMS_CHANNELOFF : self.CHANNELOFF_DEFAULT
            }
            self._installOnFirstAvailableSlot(newSlotInfo)