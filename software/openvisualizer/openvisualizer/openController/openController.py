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

from moteDriver  import moteDriver  as md
from scheduleMgr import scheduleMgr as sm

class openController():


    def __init__(self, moteStates):

        # log
        log.info("create instance")

        # store params
        self.stateLock      = threading.Lock()
        self.name           = 'openController'

        # initiate startupConfig
        self.startupConfig  = {sm.KEY_ROOTLIST: [],
                               sm.KEY_SLOTFRAMES: {}}
        self.loadConfig()

        # initiate scheduleMgr
        self.moteDriver     = md(moteStates)
        self.scheduleMgrs   = [sm(frameID) for frameID in self.startupConfig[sm.KEY_SLOTFRAMES].keys()]


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
        for frameID, slotFrame in self.startupConfig[sm.KEY_SLOTFRAMES].items():
            smgr = self.getScheduleMgr(frameID)
            if smgr:
                smgr.installFrame(slotFrame, newRoots)
            else:
                log.debug('Not scheduleMgr found for slotFrame {0}'.format(frameID))

        # Toggle DAGroot if not yet configured
        if not self.getRootList():
            for moteid in newRoots:
                ms = self.moteDriver.getMoteState(moteid)
                if ms:
                    log.debug('Found mote {0} in moteStates'.format(moteid))
                    ms.triggerAction(ms.TRIGGER_DAGROOT)
                else:
                    log.debug('Mote {0} not found in moteStates'.format(moteid))

    def getRootList(self):
        '''
        :returns rootList

        '''
        return self.moteDriver.getRootList()

    def getScheduleMgr(self, frameID):
        '''
        :returns: scheduleMgr Object

        '''
        for schemgr in self.scheduleMgrs:
            if schemgr.getFrameID() == frameID:
                return schemgr

        return None

    def getRunningSchedule(self):
        '''
        :returns: running Schedule on WebUI

        '''
        schedule = {
            sm.KEY_ROOTLIST: self.getRootList(),
            sm.KEY_SLOTFRAMES: {}
        }
        for smgr in self.scheduleMgrs:
            schedule[sm.KEY_SLOTFRAMES].update(smgr.getRunningFrame())
        return schedule

    def getStartupSchedule(self):
        '''
        :returns: startup Schedule on WebUI

        '''
        return self.startupConfig


    # ============================ private ===================================

