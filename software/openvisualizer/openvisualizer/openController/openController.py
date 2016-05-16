# Copyright (c) 2010-2013, Regents of the University of California.
# All rights reserved.
#
# Released under the BSD 3-Clause license as published at the link below.
# https://openwsn.atlassian.net/wiki/display/OW/License

'''
Contains openController component for centralized scheduling of the motes. It uses self.app.motestates to communicate with motes
'''
import os
import logging
import json
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
    PARAMS_REMAPTOCELL       = 'remaptocell'
    PARAMS_TXMOTEID          = 'txMoteID'
    PARAMS_RXMOTELIST        = 'rxMoteList'
    PARAMS_SLOTOFF           = 'slotOffset'
    PARAMS_CHANNELOFF        = 'channelOffset'
    PARAMS_FRAMELENGTH       = 'frameLength'
    PARAMS_MAXACTSLOTS       = 'maxActiveSlots'

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
        self.stateLock        = threading.Lock()
        self.app              = app
        self.simMode          = self.app.simulatorMode
        self.runningSchedule  = {}
        self.startupSchedule  = self.getDefaultSchedule()
        self.rootList         = []
        self.name = 'openController'



#   =============== public ==========================

    def installNewSchedule(self, scheduleSDict):
        '''
        Install new chedule either from default configuration or somewhere else.

        :param scheduleSDict: a dictionary contains scheduling params as in schedule.json
        '''

        if not scheduleSDict:
            return

        moteList = self.app.getMoteList()
        newRootList            = scheduleSDict[self.ROOTLIST]

        for scheduleDict in scheduleSDict[self.SLOTFRAMES]:
            slotFrame       = scheduleDict[self.CMD_TARGETSLOTFRAME]
            slotList        = scheduleDict[self.PARAMS_CELL]
            frameLength     = scheduleDict[self.PARAMS_FRAMELENGTH]
            maxActiveSlots  = scheduleDict[self.PARAMS_MAXACTSLOTS]

            if self.runningSchedule:
                self._clearDetFrame(moteList, slotFrame)
            elif not self.rootList:
                self._setSchedule_vars(newRootList,
                                       moteList,
                                       frameLength,
                                       maxActiveSlots,
                                       slotFrame)
                for newMoteid in newRootList:
                    self.toggleRoot(newMoteid)
                self.rootList = newRootList

            for slotEntry in slotList:
                if slotEntry[self.PARAMS_SHARED] == False:
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
                else:
                    self._addSharedSlot(
                        slotEntry[self.PARAMS_SLOTOFF],
                        slotEntry[self.PARAMS_CHANNELOFF],
                        self.OPT_ADD,
                        slotFrame)

        self.runningSchedule = scheduleSDict

    def toggleRoot(self, moteid):
        ms = self.app.getMoteState(moteid)
        if ms:
            ms.triggerAction(ms.TRIGGER_DAGROOT)
            self.updateRootList(moteid)
        else:
            log.debug('Mote {0} not found in moteStates'.format(moteid))

    def updateRootList(self, moteid):
        self.rootList = self.getDAGrootList()
        if moteid in self.rootList:
            self.rootList.remove(moteid)
        else:
            self.rootList.append(moteid)

    def getDAGrootList(self):
        DAGrootList = []
        for moteId in self.app.getMoteList():
            ms = self.app.getMoteState(moteId)
            if ms and json.loads(ms.getStateElem(ms.ST_IDMANAGER).toJson('data'))[0]['isDAGroot']:
                DAGrootList.append(moteId)
        return DAGrootList

    def installDefaultSchedule(self):
        self.installNewSchedule(self.getDefaultSchedule())

    def refreshRunningSchedule(self):
        self.installNewSchedule(self.getStartupSchedule())

    def getDefaultSchedule(self):
        try:
            with open(os.getcwd() + '/openvisualizer/openController/schedule.json') as json_file:
                return json.load(json_file)
        except IOError as err:
            return None

    def getStartupSchedule(self):
        return self.startupSchedule

    def getRunningSchedule(self):
        return self.runningSchedule

#   ================= private =======================
    # schedule operations

    def _addDetSlot(self,
                    txMote,
                    rxMoteList,
                    slotOff,
                    bitIndex,
                    opt = OPT_ADD,
                    trackID = 1,
                    targetSlotFrame = SLOTFRAME_DEFAULT,
                    channelOff = 0,
                    shared = False):
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

    def _addSharedSlot(self,
                       slotOff,
                       channelOff,
                       opt = OPT_ADD,
                       targetSlotFrame = SLOTFRAME_DEFAULT):
        motelist = self.app.getMoteList()

        params = {
            self.PARAMS_BITINDEX   : 0,
            self.PARAMS_CELL       : (slotOff, channelOff),
            self.PARAMS_SHARED     : True,
            self.PARAMS_TRACKID    : 0,
            self.PARAMS_TYPE       : self.TYPE_TXRX
        }

        for moteid in motelist:
            self._sendSchedule(moteid, [targetSlotFrame, opt, params])


    def _remapDetSlot(self,
                      txMote,
                      rxMoteList,
                      slotOff,
                      remapSlotOff,
                      channelOff = 0,
                      remapChannel = 0,
                      targetSlotFrame = SLOTFRAME_DEFAULT):
        params = {
            self.PARAMS_CELL: (slotOff, channelOff),
            self.PARAMS_REMAPTOCELL: (remapSlotOff, remapChannel)
        }
        if txMote:
            self._sendSchedule(txMote, [targetSlotFrame, self.OPT_REMAP, params])
        if rxMoteList:
            for rxMote in rxMoteList:
                self._sendSchedule(rxMote, [targetSlotFrame, self.OPT_REMAP, params])

    def _deleteDetSlot(self,
                       txMote,
                       rxMoteList,
                       slotOff,
                       channelOff = 0,
                       targetSlotFrame = SLOTFRAME_DEFAULT):
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

    def _clearDetFrame(self,
                       moteList,
                       targetSlotFrame = SLOTFRAME_DEFAULT):

        for moteId in moteList:
            self._sendSchedule(moteId, [targetSlotFrame, self.OPT_CLEAR])

    def _setSchedule_vars(self,
                        newRootList,
                        moteList,
                        frameLength,
                        maxActiveSlots  = ACTIVESLOTS_DEFAULT,
                        targetSlotFrame = SLOTFRAME_DEFAULT,
                        ):

        for moteId in moteList:
            if moteId in newRootList:
                self._sendSchedule(
                            moteId,
                    [       targetSlotFrame,
                            self.OPT_SETFRAMELENGTH,
                        {   self.PARAMS_FRAMELENGTH : frameLength,
                            self.PARAMS_MAXACTSLOTS : maxActiveSlots
                        }
                    ]
                )
            else:
                self._sendSchedule(
                    moteId,
                    [targetSlotFrame,
                     self.OPT_SETFRAMELENGTH,
                     {self.PARAMS_FRAMELENGTH: 0,
                      self.PARAMS_MAXACTSLOTS: maxActiveSlots
                      }
                     ]
                )

    def _sendSchedule(self, moteid, command):
        # send command [<targetSlotFrame>, <operation>, <params>] to <moteid>
        log.info('Send Schedule Command to moteid {0}'.format(moteid))
        ms = self.app.getMoteState(moteid)
        if ms:
            log.debug('Found mote {0} in moteStates'.format(moteid))
            ms.triggerAction([moteState.moteState.INSTALL_SCHEDULE] + command)
        else:
            log.debug('Mote {0} not found in moteStates'.format(moteid))
