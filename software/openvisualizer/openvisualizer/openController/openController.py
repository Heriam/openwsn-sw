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
from openvisualizer.moteState import moteState



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

    SLOTFRAME_DEFAULT        = 1   # default id of slotframe
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
        self.startupSchedule  = {self.ROOTLIST   : [],
                                  self.SLOTFRAMES : {}}
        self.runningSchedule   = {self.ROOTLIST   : [],
                                  self.SLOTFRAMES : {}}
        self.name = 'openController'

        # load startup schedule
        self.loadSchedule()



#   =============== public ==========================

    def installNewSchedule(self):
        self.installSchedule(self.startupSchedule)

    def installSchedule(self, scheduleSDict):
        '''
        it installs the schedule from scheduleSDict dictionary,
        and then stores the schedule configurations in the runningSchedule dictionary if successfully executed.
        '''

        newScheduleSDict = copy.deepcopy(scheduleSDict)
        rootList = newScheduleSDict.pop(self.ROOTLIST)

        # clear old schedules if any
        self.clearSchedule()
        # configure DAGroot and FrameLength if not yet configured
        if not self.runningSchedule[self.ROOTLIST]:
            self.toggleRootList(rootList)
        # install slots
        for frameKey in newScheduleSDict[self.SLOTFRAMES].keys():
            newFrame = True
            if frameKey in self.runningSchedule[self.SLOTFRAMES].keys():
                newFrame = False
            slotList = newScheduleSDict[self.SLOTFRAMES][frameKey][self.PARAMS_CELL]
            if newFrame:
                for slotEntry in slotList[:]:
                    installed = self._slotOperation(self.OPT_ADD, slotEntry, frameKey)[0]
                    if not installed:
                        slotList.remove(slotEntry)
                        log.debug("failed to install slot {0} on slotFrame {1}".format(slotEntry[self.PARAMS_SLOTOFF], frameKey))
                self.runningSchedule[self.SLOTFRAMES][frameKey] = newScheduleSDict[self.SLOTFRAMES][frameKey]
            else:
                for slotEntry in slotList[:]:
                    newSlot = True
                    for eachSlot in self.runningSchedule[self.SLOTFRAMES][frameKey][self.PARAMS_CELL]:
                        if slotEntry[self.PARAMS_SLOTOFF] == eachSlot[self.PARAMS_SLOTOFF]:
                            newSlot = False
                    if newSlot:
                        installed = self._slotOperation(self.OPT_ADD, slotEntry, frameKey)[0]
                        if not installed:
                            slotList.remove(slotEntry)
                            log.debug("failed to install slot {0} on slotFrame {1}".format(slotEntry[self.PARAMS_SLOTOFF], frameKey))
                    else:
                        slotList.remove(slotEntry)
                        log.debug("failed to install slot {0}, which is not available on slotFrame {1}".format(slotEntry[self.PARAMS_SLOTOFF], frameKey))
                self.runningSchedule[self.SLOTFRAMES][frameKey][self.PARAMS_CELL] += slotList


    def clearSchedule(self, includeshared=False):
        '''
        it clears all the schedules on all motes according to the configurations stored in the runningSchedule dictionary.
        '''
        moteList = self.app.getMoteList()
        for frameKey in self.runningSchedule[self.SLOTFRAMES].keys():
            self._clearDetFrame(moteList, frameKey)
            slotList = self.runningSchedule[self.SLOTFRAMES][frameKey][self.PARAMS_CELL]
            for slotEntry in slotList[:]:
                if slotEntry[self.PARAMS_SHARED]:
                    if includeshared:  # clear Shared slots
                        anyFailed = self._slotOperation(self.OPT_DELETE, slotEntry, frameKey)[1]
                        if not anyFailed:
                            slotList.remove(slotEntry)
                else:
                    slotList.remove(slotEntry)

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
                log.debug("failed to load default startupSchedule. " + err.message)



    def toggleRootList(self, rootList):
        '''
        specify schedule length if it is the first time toggling the DAGroot
        and then stores the schedule configurations in the runningSchedule dictionary if successfully executed.
        '''

        if not self.runningSchedule[self.ROOTLIST] and not self.runningSchedule[self.SLOTFRAMES] and self.startupSchedule[self.SLOTFRAMES]:
            for frameKey in self.startupSchedule[self.SLOTFRAMES].keys():
                frameLength = self.startupSchedule[self.SLOTFRAMES][frameKey][self.PARAMS_FRAMELENGTH]
                self._setSchedule_vars(rootList,
                                       frameLength,
                                       frameKey)
                log.info("Set schedule length " + str(frameLength))

        for moteid in rootList:
            ms = self.app.getMoteState(moteid)
            if ms:
                self._updateRunningRootList(moteid)
                ms.triggerAction(ms.TRIGGER_DAGROOT)
            else:
                log.debug('Mote {0} not found in moteStates'.format(moteid))

    def getRunningSchedule(self):
        return self.runningSchedule

    def getStartupSchedule(self):
        return self.startupSchedule



    #   ================= private =======================



    def _updateRunningRootList(self, moteid = None):
        '''
            updates rootList in runningSchedule dictionary
        '''
        DAGrootList = []
        for moteId in self.app.getMoteList():
            ms = self.app.getMoteState(moteId)
            if ms and json.loads(ms.getStateElem(ms.ST_IDMANAGER).toJson('data'))[0]['isDAGroot']:
                DAGrootList.append(moteId)
        if moteid:
            if moteid in DAGrootList:
                DAGrootList.remove(moteid)
            else:
                DAGrootList.append(moteid)
        self.runningSchedule[self.ROOTLIST] = DAGrootList
        return self.runningSchedule[self.ROOTLIST]


    #   ============================ Mote interactions ============================


    def _slotOperation(self, operation, slotInfoDict, frameKey = SLOTFRAME_DEFAULT):
        shared     = slotInfoDict[self.PARAMS_SHARED]
        ifanyFailed= False
        ifanyOK = False
        if shared:
            motelist = self.app.getMoteList()
            slotInfoDict[self.PARAMS_TYPE] = self.TYPE_TXRX
            for moteid in motelist:
                if self._sendScheduleCMD(moteid, [frameKey, operation, slotInfoDict]):
                    ifanyOK     = True
                else:
                    ifanyFailed = True

        else:
            txMote     = slotInfoDict[self.PARAMS_TXMOTEID]
            rxMoteList = slotInfoDict[self.PARAMS_RXMOTELIST]
            if txMote:
                slotInfoDict[self.PARAMS_TYPE] = self.TYPE_TX
                if self._sendScheduleCMD(txMote, [frameKey, operation, slotInfoDict]):
                    ifanyOK = True
                    if operation == self.OPT_DELETE:
                        txMote  = None
                else:
                    ifanyFailed = True
                    if operation == self.OPT_ADD:
                        txMote  = None

            if rxMoteList:
                slotInfoDict[self.PARAMS_TYPE] = self.TYPE_RX
                for rxMote in rxMoteList[:]:
                    if self._sendScheduleCMD(rxMote, [frameKey, operation, slotInfoDict]):
                        ifanyOK = True
                        if operation == self.OPT_DELETE:
                            rxMoteList.remove(rxMote)
                    else:
                        ifanyFailed = True
                        if operation == self.OPT_ADD:
                            rxMoteList.remove(rxMote)

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
            ms.triggerAction([moteState.moteState.INSTALL_SCHEDULE] + command)
            outcome = True
        else:
            log.debug('Mote {0} not found in moteStates'.format(moteid))

        return outcome