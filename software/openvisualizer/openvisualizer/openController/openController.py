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
from trackMgr    import trackMgr    as tm
from stateMgr    import stateMgr    as stm

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
        self.trackMgr       = tm()
        self.stateMgr       = stm()
        eventBusClient.eventBusClient.__init__(self,"openController", registrations=[

        ])


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
        return self.trackMgr.getDagRoot()


    def getTrackMgr(self):
        '''
        :returns: trackMgr

        '''
        return self.trackMgr


    def getScheduleMgr(self):
        '''
        :returns: scheduleMgr scheduleMgr

        '''
        return self.scheduleMgr


    # ============================ private ===================================


