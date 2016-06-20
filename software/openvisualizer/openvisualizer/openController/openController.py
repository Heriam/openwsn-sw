# Copyright (c) 2010-2013, Regents of the University of California.
# All rights reserved.
#
# Released under the BSD 3-Clause license as published at the link below.
# https://openwsn.atlassian.net/wiki/display/OW/License

'''
Contains openController component for centralized scheduling of the motes. It uses self.app.motestates to communicate with motes



'''
import threading
import logging
log = logging.getLogger('openController')
log.setLevel(logging.ERROR)
log.addHandler(logging.NullHandler())

from openvisualizer.eventBus import eventBusClient
from moteDriver  import moteDriver  as md
from scheduleMgr import scheduleMgr as sm


class openController(eventBusClient.eventBusClient):


    def __init__(self, moteStates):

        # log
        log.info("create instance")

        # store params
        self.stateLock      = threading.Lock()
        self.name           = 'openController'

        # initiate scheduleMgr
        self.moteDriver     = md(moteStates)
        self.scheduleMgr    = sm()

        eventBusClient.eventBusClient.__init__(self,"openController", registrations=[])


    # ==================== public =======================

    def getMoteDriver(self):
        '''
        :returns moteDriver

        '''
        return self.moteDriver

    def getScheduleMgr(self):
        '''
        :returns: scheduleMgr scheduleMgr

        '''
        return self.scheduleMgr


    # ============================ private ===================================

