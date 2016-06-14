# Copyright (c) 2010-2013, Regents of the University of California.
# All rights reserved.
#
# Released under the BSD 3-Clause license as published at the link below.
# https://openwsn.atlassian.net/wiki/display/OW/License

'''


'''
import threading
import logging
log = logging.getLogger('openController')
log.setLevel(logging.ERROR)
log.addHandler(logging.NullHandler())

from openvisualizer.eventBus import eventBusClient
from moteDriver  import moteDriver  as md
from scheduleMgr import scheduleMgr as sm
from topologyMgr import topologyMgr as tm

class openController(eventBusClient.eventBusClient):


    def __init__(self, moteStates):

        # log
        log.info("create instance")

        # store params
        self.stateLock      = threading.Lock()
        self.name           = 'openController'

        # initiate scheduleMgr
        self.moteDriver     = md(moteStates)
        self.topologyMgr    = tm()
        self.scheduleMgr    = sm()

        eventBusClient.eventBusClient.__init__(self,"openController", registrations=[])


    # ==================== public =======================

    def getMoteDriver(self):
        '''
        :returns moteDriver

        '''
        return self.moteDriver

    def getDagRootList(self):
        '''
        :returns rootList

        '''
        return self.topologyMgr.getDagRootList()


    def getTopoMgr(self):
        '''
        :returns: topoMgr

        '''
        return self.topologyMgr


    def getScheduleMgr(self):
        '''
        :returns: scheduleMgr scheduleMgr

        '''
        return self.scheduleMgr


    # ============================ private ===================================

