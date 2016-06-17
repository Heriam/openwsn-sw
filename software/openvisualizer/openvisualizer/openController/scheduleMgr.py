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
import json
from openvisualizer.eventBus.eventBusClient import eventBusClient


class Schedule():

    # slot parameters
    PARAMS_TRACKID = 'trackID'
    PARAMS_BITINDEX = 'bitIndex'
    PARAMS_TYPE = 'type'
    PARAMS_SHARED = 'shared'
    PARAMS_REMAPSLOTOFF = 'remapSlotOff'
    PARAMS_REMAPCHANOFF = 'remapChanOff'
    PARAMS_TXMOTEID = 'txMoteID'
    PARAMS_RXMOTELIST = 'rxMoteList'
    PARAMS_SLOTOFF = 'slotOffset'
    PARAMS_CHANNELOFF = 'channelOffset'

    # schedule parameters
    PARAMS_FRAMEID = 'frameID'
    PARAMS_FRAMELENGTH = 'frameLength'
    PARAMS_FIRSTFREESLOT = 'firstfreeslot'
    PARAMS_CELL = 'cells'

    # default values
    CHANNELOFF_DEFAULT = 0
    SLOTFRAME_DEFAULT = '1'
    FRAMELENGTH_DEFAULT = 20

    # operation types
    OPT_ADD = 'add'
    OPT_OVERWRITE = 'overwrite'
    OPT_REMAP = 'remap'
    OPT_DELETE = 'delete'
    OPT_LIST = 'list'
    OPT_CLEAR = 'clear'
    OPT_SETFRAMELENGTH = 'setFrameLength'
    OPT_ALL = [OPT_ADD, OPT_OVERWRITE, OPT_REMAP, OPT_DELETE, OPT_LIST, OPT_CLEAR, OPT_SETFRAMELENGTH]

    # cell types
    TYPE_OFF = 'off'
    TYPE_TX = 'tx'
    TYPE_RX = 'rx'
    TYPE_TXRX = 'txrx'
    TYPE_SERIALRX = 'serialrx'
    TYPE_MORESERIALRX = 'moreserx'
    TYPE_ALL = [TYPE_OFF, TYPE_TX, TYPE_RX, TYPE_TXRX, TYPE_SERIALRX, TYPE_MORESERIALRX]

    def __init__(self, scheduleMgr):

        self.frameLock       = threading.Lock()
        self.frameLen        = self.FRAMELENGTH_DEFAULT
        self.frameID         = self.SLOTFRAME_DEFAULT
        self.slotFrame       = [None] * self.frameLen
        self.sm              = scheduleMgr

    # ========================== public ===========================


    def clearSharedSlots(self):
        '''
        clears Shared slots on all motes.

        '''
        sharedList = []
        for slot in self.slotFrame[:]:
            if slot and slot[self.PARAMS_SHARED] and slot[self.PARAMS_SLOTOFF]:
                sharedList.append(slot)
        self.configSlot(self.OPT_DELETE, sharedList)

    def installTrack(self, track):
        '''
        installs a track on slot frame

        '''
        self._update()
        with self.frameLock:
            slotFrame = self.slotFrame[:]

        trackID = track.graph['trackID']
        newArcs = track.graph['newArcs']
        slotList = []
        for arcEdges in newArcs:
            for (rxMote, txMote) in arcEdges:
                if None in slotFrame:
                    slotOff = slotFrame.index(None)
                else:
                    log.debug('Warning! No enough available slots')
                    return
                txMoteID = ''.join(['%02x' % b for b in txMote[6:]])
                rxMoteID = ''.join(['%02x' % b for b in rxMote[6:]])
                bitIndex = track[rxMote][txMote]['bitIndex']
                slotList.append({
                    self.PARAMS_TXMOTEID: txMoteID,
                    self.PARAMS_RXMOTELIST: [rxMoteID],
                    self.PARAMS_BITINDEX: bitIndex,
                    self.PARAMS_TRACKID: trackID,
                    self.PARAMS_SHARED: False,
                    self.PARAMS_CHANNELOFF: self.CHANNELOFF_DEFAULT,
                    self.PARAMS_SLOTOFF: slotOff
                })
                slotFrame[slotOff] = slotList[-1]
        self.configSlot(self.OPT_ADD, slotList)

    def configSlot(self, operation, slotList):
        '''
        configs slots on slot frame

        '''
        with self.frameLock:
            slotFrame = self.slotFrame[:]
        for slotInfo in slotList:
            shared = slotInfo[self.PARAMS_SHARED]
            occupied = slotFrame[slotInfo[self.PARAMS_SLOTOFF]]
            if shared:
                if operation== self.OPT_ADD and occupied:
                    continue
                slotInfo[self.PARAMS_TYPE] = self.TYPE_TXRX
                self._cmdAllMotes(['schedule',
                                   self.frameID,
                                   operation,
                                   slotInfo])

            else:
                txMote = slotInfo[self.PARAMS_TXMOTEID]
                rxMoteList = slotInfo[self.PARAMS_RXMOTELIST]
                if txMote in rxMoteList:
                    rxMoteList.remove(txMote)
                if txMote:
                    slotInfo[self.PARAMS_TYPE] = self.TYPE_TX
                    self._cmdMote([txMote],
                                  ['schedule',
                                   self.frameID,
                                   operation,
                                   slotInfo])

                if rxMoteList:
                    slotInfo[self.PARAMS_TYPE] = self.TYPE_RX
                    self._cmdMote(rxMoteList,
                                  ['schedule',
                                   self.frameID,
                                   operation,
                                   slotInfo])

                slotInfo.pop(self.PARAMS_TYPE)

    def configFrame(self, operation, slotFrameInfo=None, moteList="all"):
        '''
        configures a slotFrame

        :param: slotFrameInfo: an element of stored slotFrames

        '''

        if moteList == 'all':
            self._cmdAllMotes(['schedule',
                               self.frameID, operation,
                               slotFrameInfo])
        else:
            self._cmdMote(moteList,
                          ['schedule',
                           self.frameID, operation,
                           slotFrameInfo])

    def getFrameID(self):
        '''
        :returns frame ID

        '''
        return self.frameID

    def getSlotFrame(self):
        '''
        :returns slotFrame

        '''
        self._update()
        return self.slotFrame

    def getFrameLen(self):
        '''
        :returns frameLength

        '''
        return self.frameLen

    def getFirstFreeSlot(self):
        '''
        :returns first available slotOffset

        '''
        return self.slotFrame.index(None) if None in self.slotFrame else 'FULL'

    def initWith(self, frameID, frameInfo, rootList):
        '''
        initiate schedule parameters
        :param frameInfo: contains frame parameters
               frameID: frame ID
               rootList: a list of root candidates

        '''
        with self.frameLock:
            self.frameID   = frameID
            self.frameLen  = frameInfo[self.PARAMS_FRAMELENGTH]
            self.slotFrame = [None] * self.frameLen
        self.configFrame(Schedule.OPT_SETFRAMELENGTH, frameInfo, rootList)
        self.configSlot(Schedule.OPT_ADD, frameInfo[Schedule.PARAMS_CELL])

    # ========================= private ===========================

    def _cmdAllMotes(self, cmd):

        # dispatch command
        self.sm.dispatch(
            signal='cmdAllMotes',
            data=cmd
        )

    def _cmdMote(self, motelist, cmd):
        '''
        :param: cmd: ['motelist':[], 'cmd':]

        '''

        # dispatch command
        self.sm.dispatch(
            signal='cmdMote',
            data={
                'motelist': motelist,
                'cmd': cmd
            }
        )

    def _update(self):
        '''
        updates runningSlotFrame info from moteStates

        '''

        returnVal = self.sm._dispatchAndGetResult(
            signal='getStateElem',
            data='Schedule'
        )

        slotFrame = [None] * self.frameLen
        # gets the schedule of every mote
        for mote64bID, moteSchedule in returnVal.items():
            moteID = ''.join(['%02x' % b for b in mote64bID[6:]])
            # removes unscheduled cells
            for slotEntry in moteSchedule[:]:
                if slotEntry[self.PARAMS_TYPE] == '0 (OFF)':
                    moteSchedule.remove(slotEntry)
                    continue
                t = slotEntry[self.PARAMS_TYPE]
                existSlot = slotFrame[slotEntry[self.PARAMS_SLOTOFF]]
                if existSlot:
                    if t.startswith('1'):
                        existSlot[self.PARAMS_TXMOTEID] = moteID
                    elif t.startswith('2'):
                        existSlot[self.PARAMS_RXMOTELIST].append(moteID)
                else:
                    for i in ['lastUsedAsn', 'numTx', 'neighbor', 'numRx', 'numTxACK']:
                        slotEntry.pop(i)
                    if t.startswith('1'):
                        slotEntry.pop('type')
                        slotEntry[self.PARAMS_TXMOTEID] = moteID
                        slotEntry[self.PARAMS_RXMOTELIST] = []
                    elif t.startswith('2'):
                        slotEntry.pop('type')
                        slotEntry[self.PARAMS_TXMOTEID] = None
                        slotEntry[self.PARAMS_RXMOTELIST] = [moteID]
                    slotFrame[slotEntry[self.PARAMS_SLOTOFF]] = slotEntry

        with self.frameLock:
            self.slotFrame[:] = slotFrame



class scheduleMgr(eventBusClient):

    # schedule.json keys
    KEY_SLOTFRAMES = 'slotFrames'
    KEY_ROOTLIST = 'rootList'

    def __init__(self):

        # log
        log.info("create instance")

        # local variables
        self.stateLock          = threading.Lock()
        self.defaultSchedule    = Schedule(self)
        self.rootList           = []

        # give this thread a name
        self.name = 'scheduleMgr'

        # initiate parent class
        eventBusClient.__init__(
            self,
            self.name,
            registrations=[
                {
                    'sender': self.WILDCARD,
                    'signal': 'infoDagRoot',
                    'callback': self._updateRoot
                },
                {
                    'sender'  : self.WILDCARD,
                    'signal'  : 'updateTrackSchedule',
                    'callback': self._installTrack
                }
            ]
        )


    #   =============== public ==========================

    def installSchedule(self, startupSchedule):
        '''
        installs the schedule

        :param: startupSchedule: a dictionary keyed with rootList and slotFrames

        '''
        frameInfo = startupSchedule[self.KEY_SLOTFRAMES][Schedule.SLOTFRAME_DEFAULT]
        newRoots = startupSchedule[self.KEY_ROOTLIST]
        if self.defaultSchedule.getSlotFrame()[0]:
            self.defaultSchedule.configSlot(Schedule.OPT_ADD, frameInfo[Schedule.PARAMS_CELL])
        else:
            self.defaultSchedule.initWith(Schedule.SLOTFRAME_DEFAULT, frameInfo, newRoots)
            self.dispatch(signal='cmdMote', data={'motelist': newRoots, 'cmd': 'DAGroot'})

    def getRunningFrames(self):
        '''
        :returns: running Schedules for WebUI

        '''
        rootlist = [''.join(['%02x' % b for b in addr[6:]]) for addr in self.rootList]
        runningConfig = {}
        runningConfig[self.KEY_ROOTLIST] = rootlist
        runningConfig[self.KEY_SLOTFRAMES] = {}
        runningConfig[self.KEY_SLOTFRAMES]\
            .update({self.defaultSchedule.getFrameID():
                {
                    Schedule.PARAMS_FIRSTFREESLOT: self.defaultSchedule.getFirstFreeSlot(),
                    Schedule.PARAMS_FRAMELENGTH: self.defaultSchedule.getFrameLen(),
                    Schedule.PARAMS_CELL: self.defaultSchedule.getSlotFrame()
                }})
        return runningConfig

    def getSchedule(self):
        '''
        :returns: schedule Object

        '''
        return self.defaultSchedule

    #   ================= private =======================

    def _updateRoot(self, sender, signal, data):
        '''
        Record the DAGroot's EUI64 address.

        '''
        addr = tuple(data['eui64'])
        if data['isDAGroot'] == 1:
            if addr not in self.rootList:
                self.rootList.append(addr)
        elif addr in self.rootList:
            self.rootList.remove(addr)

    def _installTrack(self, sender, signal, data):
        '''
        installs a new Track

        '''
        self.defaultSchedule.installTrack(data)


