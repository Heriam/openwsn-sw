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
import copy
log = logging.getLogger('openController')
log.setLevel(logging.ERROR)
log.addHandler(logging.NullHandler())

import threading
from openvisualizer.moteState import moteState as mS



class openController():

    SLOTFRAMES               = 'slotFrames'
    ROOTLIST                 = 'rootList'

    CMD_TARGETSLOTFRAME      = 'slotFrame'
    CMD_OPERATION            = 'operation'
    CMD_PARAMS               = 'params'

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

    SLOTFRAME_DEFAULT        = '1'   # default id of slotframe
    ACTIVESLOTS_DEFAULT      = 15  # default nums of active slots

    OPT_ADD                  = 'add'
    OPT_OVERWRITE            = 'overwrite'
    OPT_REMAP                = 'remap'
    OPT_DELETE               = 'delete'
    OPT_LIST                 = 'list'
    OPT_CLEAR                = 'clear'
    OPT_SETFRAMELENGTH       = 'setFrameLength'
    OPT_ALL = [OPT_ADD, OPT_OVERWRITE, OPT_REMAP, OPT_DELETE, OPT_LIST, OPT_CLEAR, OPT_SETFRAMELENGTH]

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
        self.stateLock         = threading.Lock()
        self.app               = app
        self.simMode           = self.app.simulatorMode
        self.startupSchedule   = {self.ROOTLIST   : [],
                                  self.SLOTFRAMES : {}}
        self.rootList          = []
        self.slotFrames        = {self.SLOTFRAME_DEFAULT : {
                                     self.PARAMS_FRAMELENGTH : 20,
                                     self.PARAMS_CELL: []
                                 }}
        self.runningSchedule   = {self.ROOTLIST   : self.rootList,
                                  self.SLOTFRAMES : self.slotFrames}
        self.name = 'openController'

        # load startup schedule
        self.loadSchedule()



#   =============== public ==========================

    def installNewSchedule(self):
        self.installSchedule(self.startupSchedule)

    def installSchedule(self, scheduleSDict):
        '''
        it triggers DAGroot and installs the schedule

        :param: scheduleSDict: a dictionary containing keys such as rootList and slotFrames

        '''

        rootList = scheduleSDict[self.ROOTLIST]

        # configure DAGroot and FrameLength if not yet configured
        if not self.rootList:
            self.toggleRootList(rootList)

        # install slots
        for frameKey, slotFrame in scheduleSDict[self.SLOTFRAMES].items():
            for slotEntry in slotFrame[self.PARAMS_CELL]:
                self._slotOperation(self.OPT_ADD, slotEntry, frameKey)

    def clearSchedule(self, includeshared=False):
        '''
        it clears all the schedules on all motes according to the configurations stored in the runningSchedule dictionary.

        :param: includeshared: specifys if also clear shared slots
        '''

        moteList = self.app.getMoteDict().keys()
        for frameKey, slotFrame in self.slotFrames.items():
            self._clearDetFrame(moteList, frameKey)
            for slotEntry in slotFrame[self.PARAMS_CELL]:
                if slotEntry[self.PARAMS_SLOTOFF] and slotEntry[self.PARAMS_SHARED] and includeshared:
                    self._slotOperation(self.OPT_DELETE, slotEntry, frameKey)


    def loadSchedule(self, scheduleSDict = {}):
        '''
        it loads the schedule from scheduleSDict if explicitly specified into the startupSchedule dictionary,
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
        specify schedule length if it is the first time toggling the DAGroot

        '''
        if self._isAtInit():
            for frameKey in self.startupSchedule[self.SLOTFRAMES].keys():
                frameLength = self.startupSchedule[self.SLOTFRAMES][frameKey][self.PARAMS_FRAMELENGTH]
                if self._setSchedule_vars(moteList,
                                       frameLength,
                                       frameKey):
                    log.info("Set schedule length " + str(frameLength))
                    self.slotFrames[frameKey][self.PARAMS_FRAMELENGTH] = frameLength

        for moteid in moteList:
            ms = self.app.getMoteState(moteid)
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
        for moteId in self.app.getMoteDict().keys():
            ms = self.app.getMoteState(moteId)
            if ms and json.loads(ms.getStateElem(ms.ST_IDMANAGER).toJson('data'))[0]['isDAGroot']:
                self.rootList.append(moteId)
        return self.rootList

    def updateRunningSchedule(self, frameKey = SLOTFRAME_DEFAULT):
        '''
            updates runningSchedule info
        '''
        SchedCellList = []
        motelist = self.app.getMoteDict().keys()
        for moteid in motelist:
            moteSlotList = self._getMoteSchedule(moteid)
            for slotEntry in moteSlotList:
                t = slotEntry[self.PARAMS_TYPE]
                exist = self._existSlot(slotEntry, SchedCellList)
                if exist:
                    if t.startswith('1'):
                        exist[self.PARAMS_TXMOTEID] = moteid
                    elif t.startswith('2'):
                        exist[self.PARAMS_RXMOTELIST].append(moteid)
                else:
                    for i in ['lastUsedAsn','numTx','neighbor','numRx','numTxACK']:
                        slotEntry.pop(i)
                    if t.startswith('1'):
                        slotEntry.pop('type')
                        slotEntry[self.PARAMS_TXMOTEID] = moteid
                        slotEntry[self.PARAMS_RXMOTELIST] = []
                    elif t.startswith('2'):
                        slotEntry.pop('type')
                        slotEntry[self.PARAMS_TXMOTEID] = None
                        slotEntry[self.PARAMS_RXMOTELIST] = [moteid]
                    SchedCellList.append(slotEntry)
        self.slotFrames[frameKey][self.PARAMS_CELL] = SchedCellList
        return self.slotFrames

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
        shared     = slotInfoDict[self.PARAMS_SHARED]
        ifanyFailed= False
        ifanyOK = False
        if shared:
            if not self._isAvailable(slotInfoDict):
                return
            motelist = self.app.getMoteDict().keys()
            slotInfoDict[self.PARAMS_TYPE] = self.TYPE_TXRX
            for moteid in motelist:
                if self._sendScheduleCMD(moteid, [frameKey, operation, slotInfoDict]):
                    ifanyOK     = True
                else:
                    ifanyFailed = True

        else:
            txMote     = slotInfoDict[self.PARAMS_TXMOTEID]
            rxMoteList = slotInfoDict[self.PARAMS_RXMOTELIST]
            if txMote in rxMoteList:
                rxMoteList.remove(txMote)
            if txMote:
                slotInfoDict[self.PARAMS_TYPE] = self.TYPE_TX
                if self._sendScheduleCMD(txMote, [frameKey, operation, slotInfoDict]):
                    ifanyOK = True
                else:
                    ifanyFailed = True

            if rxMoteList:
                slotInfoDict[self.PARAMS_TYPE] = self.TYPE_RX
                for rxMote in rxMoteList:
                    if self._sendScheduleCMD(rxMote, [frameKey, operation, slotInfoDict]):
                        ifanyOK = True
                    else:
                        ifanyFailed = True

            slotInfoDict.pop(self.PARAMS_TYPE)

        return [ifanyOK, ifanyFailed]

    def _clearDetFrame(self,
                       moteList,
                       targetSlotFrame = SLOTFRAME_DEFAULT):
        sentList = []
        for moteId in moteList:
            if self._sendScheduleCMD(moteId, [targetSlotFrame, self.OPT_CLEAR]):
                sentList.append(moteId)
        return sentList

    def _setSchedule_vars(self,
                        moteList,
                        frameLength,
                        targetSlotFrame = SLOTFRAME_DEFAULT,
                        ):
        sentList = []
        for moteId in moteList:
            if self._sendScheduleCMD(moteId,[targetSlotFrame,self.OPT_SETFRAMELENGTH,{self.PARAMS_FRAMELENGTH :frameLength}]):
                sentList.append(moteId)
        return sentList

    def _sendScheduleCMD(self, moteid, command):
        # send command [<targetSlotFrame>, <operation>, <params>] to <moteid>
        outcome = False
        log.info('Send Schedule Command to moteid {0}'.format(moteid))
        ms = self.app.getMoteState(moteid)
        if ms:
            log.debug('Found mote {0} in moteStates'.format(moteid))
            ms.triggerAction([mS.moteState.INSTALL_SCHEDULE] + command)
            outcome = True
        else:
            log.debug('Mote {0} not found in moteStates'.format(moteid))

        return outcome

    def _getMoteSchedule(self, moteid):
        '''
        Collects schedule data for the provided mote.

        :param moteid: 16-bit ID of mote
        '''
        log.debug('Get JSON data for moteid {0}'.format(moteid))
        ms = self.app.getMoteState(moteid)
        if ms:
            log.debug('Found mote {0} in moteStates'.format(moteid))
            moteSchedule = json.loads(ms.getStateElem(ms.ST_SCHEDULE).toJson('data'))
            for slot in moteSchedule[:]:
                if slot[self.PARAMS_TYPE] == '0 (OFF)':
                    moteSchedule.remove(slot)
        else:
            log.debug('Mote {0} not found in moteStates'.format(moteid))
            moteSchedule = {}

        return moteSchedule