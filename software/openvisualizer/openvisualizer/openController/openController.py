# Copyright (c) 2010-2013, Regents of the University of California.
# All rights reserved.
#
# Released under the BSD 3-Clause license as published at the link below.
# https://openwsn.atlassian.net/wiki/display/OW/License

'''


'''
import threading
import scheduleMgr
import json
import logging
log = logging.getLogger('openController')
log.setLevel(logging.ERROR)
log.addHandler(logging.NullHandler())

import moteDriver
from scheduleMgr import scheduleMgr as sm

class openController():


    def __init__(self, moteStates):

        # log
        log.info("create instance")

        # store params
        self.stateLock = threading.Lock()
        self.name = 'openController'

        # initiate startupConfig
        self.startupConfig = {sm.KEY_ROOTLIST: [],
                              sm.KEY_SLOTFRAMES: {}}
        self.loadConfig()

        # initiate scheduleMgr
        self.moteDriver    = moteDriver.moteDriver(moteStates)
        self.scheduleMgr   = scheduleMgr.scheduleMgr(moteDriver)


    # ==================== public =======================

    def loadConfig(self, config=None):
        '''
        loads the configDict if explicitly specified
        otherwise it loads the default configFile stored in schedule.json.
        '''

        if config:
            self.startupConfig = config
        else:
            try:
                with open('openvisualizer/openController/schedule.json') as json_file:
                    self.startupConfig = json.load(json_file)
            except IOError as err:
                log.debug("failed to load default startupSchedule. {0}".format(err))


    def initNetwork(self):
        '''
        installs the schedule

        :param: scheduleSDict: a slotFrameInfo dictionary containing frameLength, frameID, slotInfoList

        '''

        newRoots = self.startupConfig[sm.KEY_ROOTLIST]

        # installs schedule
        for frameID, slotFrame in scheduleSDict[self.KEY_SLOTFRAMES].items():

            # configures schedule length if the slotFrame is not initiated yet
            if self._isAtInit(frameID):
                self._frameOperation(self.OPT_SETFRAMELENGTH, slotFrame, frameID, newRoots)
                self.frameLen = slotFrame[self.PARAMS_FRAMELENGTH]

            # install slots
            for slotEntry in slotFrame[self.PARAMS_CELL]:
                self._slotOperation(self.OPT_ADD, slotEntry, frameID)

        # Toggle DAGroot if not yet configured
        if not self.rootList:
            self.toggleRootList(newRoots)





    def toggleRootList(self, moteList):
        '''
        toggles DAGroot

        '''

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

