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
import moteDriver
from openvisualizer.moteState.moteState import moteState as msParam


class scheduleMgr(moteDriver.moteDriver):

    # schedule.json keys
    SLOTFRAMES               = 'slotFrames'
    ROOTLIST                 = 'rootList'

    # schedule parameters
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
    ACTIVESLOTS_DEFAULT      = 20

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


    def __init__(self, moteStates):

        # log
        log.info("create instance")

        # local variables
        self.stateLock         = threading.Lock()
        self.startupSchedule   = {self.ROOTLIST   : [],
                                  self.SLOTFRAMES : {}}
        self.rootList          = []
        self.slotFrames        = {self.SLOTFRAME_DEFAULT : {
                                     self.PARAMS_FRAMELENGTH : self.ACTIVESLOTS_DEFAULT,
                                     self.PARAMS_CELL: []
                                 }}
        self.runningSchedule   = {self.ROOTLIST   : self.rootList,
                                  self.SLOTFRAMES : self.slotFrames}

        # give this thread a name
        self.name = 'openController'

        # load startup schedule
        self.loadSchedule()

        # initiate parent class
        moteDriver.moteDriver.__init__(self, moteStates)


#   =============== public ==========================


    def installSchedule(self, scheduleSDict):
        '''
        triggers DAGroot and installs the schedule

        :param: scheduleSDict: a dictionary containing keys such as rootList and slotFrames

        '''

        # configure DAGroot and FrameLength if not yet configured
        if not self.rootList:
            self.toggleRootList(scheduleSDict[self.ROOTLIST])

        # install slots
        for frameKey, slotFrame in scheduleSDict[self.SLOTFRAMES].items():
            for slotEntry in slotFrame[self.PARAMS_CELL]:
                self._slotOperation(self.OPT_ADD, slotEntry, frameKey)

    def clearSchedule(self, includeshared=False):
        '''
        clears all the schedules on all motes according to the configurations stored in the runningSchedule dictionary.

        :param: includeshared: specifys if also clear shared slots
        '''

        for frameKey, slotFrame in self.slotFrames.items():
            self._clearDetFrame(frameKey)
            for slotEntry in slotFrame[self.PARAMS_CELL]:
                if slotEntry[self.PARAMS_SLOTOFF] and slotEntry[self.PARAMS_SHARED] and includeshared:
                    self._slotOperation(self.OPT_DELETE, slotEntry, frameKey)

    def loadSchedule(self, scheduleSDict = None):
        '''
        loads the schedule from scheduleSDict if explicitly specified into the startupSchedule dictionary,
        otherwise it loads the default schedule stored in schedule.json.
        '''

        if scheduleSDict:
            self.startupSchedule = scheduleSDict
        else:
            try:
                with open('openvisualizer/openController/schedule.json') as json_file:
                    self.startupSchedule = json.load(json_file)
            except IOError as err:
                log.debug("failed to load default startupSchedule. {0}".format(err))

    def toggleRootList(self, moteList):
        '''
        toggles DAGroot

        '''

        # specify schedule length if it is the first time toggling the DAGroot
        if self._isAtInit():
            for frameKey in self.startupSchedule[self.SLOTFRAMES].keys():
                frameLength = self.startupSchedule[self.SLOTFRAMES][frameKey][self.PARAMS_FRAMELENGTH]
                if self._setSchedule_vars(moteList,
                                       frameLength,
                                       frameKey):
                    log.info("Set schedule length " + str(frameLength))
                    self.slotFrames[frameKey][self.PARAMS_FRAMELENGTH] = frameLength

        for moteid in moteList:
            ms = self.getMoteState(moteid)
            if ms:
                log.debug('Found mote {0} in moteStates'.format(moteid))
                ms.triggerAction(ms.TRIGGER_DAGROOT)
            else:
                log.debug('Mote {0} not found in moteStates'.format(moteid))

    def updateRunningRootList(self):
        '''
            updates rootList info
        '''
        self.rootList[:] = []
        for ms in self.moteStates:
            if ms and json.loads(ms.getStateElem(ms.ST_IDMANAGER).toJson('data'))[0]['isDAGroot']:
                self.rootList.append(self.getMoteID(ms))

    def updateRunningSchedule(self, frameKey = SLOTFRAME_DEFAULT):
        '''
            updates runningSchedule info
        '''
        SchedCellList = []

        # gets the schedule of every mote
        for ms in self.moteStates:
            moteID = self.getMoteID(ms)
            moteSchedule = json.loads(ms.getStateElem(ms.ST_SCHEDULE).toJson('data'))

            # removes unscheduled cells
            for slot in moteSchedule[:]:
                if slot[self.PARAMS_TYPE] == '0 (OFF)':
                    moteSchedule.remove(slot)

            # stores slotEntries in runningSchedule dictionary
            for slotEntry in moteSchedule:
                t = slotEntry[self.PARAMS_TYPE]
                exist = self._existSlot(slotEntry, SchedCellList)
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
                    SchedCellList.append(slotEntry)
        self.slotFrames[frameKey][self.PARAMS_CELL] = SchedCellList

    def installNewSchedule(self):
        self.installSchedule(self.startupSchedule)

    def getRunningSchedule(self):
        self.updateRunningRootList()
        self.updateRunningSchedule()
        return self.runningSchedule

    def getStartupSchedule(self):
        return self.startupSchedule



    #   ================= private =======================

    def _sameSlot(self, slota, slotb):
        same = False
        if slota[self.PARAMS_SLOTOFF] == slotb[self.PARAMS_SLOTOFF]:
            if slota[self.PARAMS_CHANNELOFF] == slotb[self.PARAMS_CHANNELOFF]:
                same = True
        return same

    def _existSlot(self, slot, slotList):
        existAs = None
        for slotElem in slotList:
            if self._sameSlot(slot, slotElem):
                existAs = slotElem
        return existAs

    def _isAtInit(self):
        atInit = True
        for slotElem in self.slotFrames[self.SLOTFRAME_DEFAULT][self.PARAMS_CELL]:
            if slotElem[self.PARAMS_SLOTOFF] == 0:
                atInit = False
        return atInit

    def _isAvailable(self, slot, framekey = SLOTFRAME_DEFAULT):
        available = True
        schedCells = self.slotFrames[framekey][self.PARAMS_CELL]
        if self._existSlot(slot, schedCells):
            available = False
        return available

    #   ============================ Mote interactions ============================


    def _slotOperation(self, operation, slotInfoDict, frameKey = SLOTFRAME_DEFAULT):
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
            self.cmdAllMotes([msParam.INSTALL_SCHEDULE, frameKey, operation, slotInfoDict])

        else:
            txMote     = slotInfoDict[self.PARAMS_TXMOTEID]
            rxMoteList = slotInfoDict[self.PARAMS_RXMOTELIST]
            if txMote in rxMoteList:
                rxMoteList.remove(txMote)
            if txMote:
                slotInfoDict[self.PARAMS_TYPE] = self.TYPE_TX
                self.cmdMote(txMote, [msParam.INSTALL_SCHEDULE, frameKey, operation, slotInfoDict])

            if rxMoteList:
                slotInfoDict[self.PARAMS_TYPE] = self.TYPE_RX
                for rxMote in rxMoteList:
                    self.cmdMote(rxMote, [msParam.INSTALL_SCHEDULE, frameKey, operation, slotInfoDict])

            slotInfoDict.pop(self.PARAMS_TYPE)

    def _clearDetFrame(self,
                       targetSlotFrame = SLOTFRAME_DEFAULT,
                       moteList = {}):
        if moteList:
            for moteId in moteList:
                self.cmdMote(moteId, [msParam.INSTALL_SCHEDULE, targetSlotFrame, self.OPT_CLEAR])
        else:
            self.cmdAllMotes([msParam.INSTALL_SCHEDULE, targetSlotFrame, self.OPT_CLEAR])


    def _setSchedule_vars(self,
                        moteList,
                        frameLength,
                        targetSlotFrame = SLOTFRAME_DEFAULT,
                        ):

        for moteId in moteList:
            self.cmdMote(moteId,[msParam.INSTALL_SCHEDULE,
                                 targetSlotFrame,
                                 self.OPT_SETFRAMELENGTH,
                                 {self.PARAMS_FRAMELENGTH :frameLength}])