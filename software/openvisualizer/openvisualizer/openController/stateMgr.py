# Copyright (c) 2010-2013, Regents of the University of California.
# All rights reserved.
#
# Released under the BSD 3-Clause license as published at the link below.
# https://openwsn.atlassian.net/wiki/display/OW/License

'''


'''
import datetime as dt
import threading
from openvisualizer.eventBus import eventBusClient
import logging
log = logging.getLogger('stateMgr')
log.setLevel(logging.INFO)
log.addHandler(logging.NullHandler())


class stateMgr(eventBusClient.eventBusClient):

    def __init__(self):

        self.dataLock    = threading.Lock()
        self.enabledHops = {}
        self.failedHops  = {}
        self.timeoutVal  = dt.timedelta(seconds=600)
        self.pendingUpdate = {}
        self.roundTime   = dt.datetime.now()

        eventBusClient.eventBusClient.__init__(
            self,
            "stateMgr",
            registrations=[
                {
                    'sender': self.WILDCARD,
                    'signal': 'enabledHops',
                    'callback': self._hopsEnabled_update,
                },
                {
                    'sender': self.WILDCARD,
                    'signal': 'failedHops',
                    'callback': self._hopsFailed_update,
                }
            ]
        )

    # ====================== public ========================


    # ====================== private =======================

    def _hopsEnabled_update(self, sender,signal,data):
        (trackId, enabledHops, bitMap) = data
        self.pendingUpdate[trackId] = enabledHops
        newRoundTime = dt.datetime.now()
        if newRoundTime - self.roundTime > self.timeoutVal:
            self._update()


    def _hopsFailed_update(self, sender,singal,data):
        (trackId, failedHops, bitMap)  = data
        if self.pendingUpdate.get(trackId):
            (txTime, enabledHops) = self.pendingUpdate.get(trackId)
            with self.dataLock:
                for hop in enabledHops:
                    if hop in self.enabledHops.keys():
                        self.enabledHops[hop] = self.enabledHops[hop] + 1
                    else:
                        self.enabledHops[hop] = 1
                    print self.failedHops[hop] * 1.000 / self.enabledHops[hop] if hop in self.failedHops.keys() else 0
                for hop in failedHops:
                    if hop in self.failedHops.keys():
                        self.failedHops[hop] = self.failedHops[hop] + 1
                    else:
                        self.failedHops[hop] = 1

    def _update(self):

        reliability = {}
        for hop in self.enabledHops.keys():
            reliability[hop] = (1.000 - self.failedHops[hop]*1.000/self.enabledHops[hop]) if hop in self.failedHops.keys() else 1
        self.dispatch('updateLinkState', reliability)
        with self.dataLock:
            self.enabledHops.clear()
            self.failedHops.clear()
            self.roundTime = dt.datetime.now()
        log.debug('[Reliability] {0}\n'.format(reliability))