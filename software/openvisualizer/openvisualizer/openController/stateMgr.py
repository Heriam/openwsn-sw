# Copyright (c) 2010-2013, Regents of the University of California.
# All rights reserved.
#
# Released under the BSD 3-Clause license as published at the link below.
# https://openwsn.atlassian.net/wiki/display/OW/License

'''


'''
import datetime as dt
import time
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
        self.timeoutVal  = dt.timedelta(seconds=6)
        self.pendingUpdate = {}
        self.dropRates   = []

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

        self.threads = []
        t = threading.Thread(target=self._update())
        t.setDaemon(True)
        t.start()
        self.threads.append(t)

    # ====================== public ========================


    # ====================== private =======================

    def _hopsEnabled_update(self, sender,signal,data):
        (trackId, enabledHops, bitMap) = data
        self.pendingUpdate[trackId] = enabledHops


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
        while True:
            time.sleep(600)
            hopEntry = {}
            for hop in self.enabledHops.keys():
                hopEntry[hop] = self.failedHops[hop]*1.000/self.enabledHops[hop] if hop in self.failedHops.keys() else 0
            self.dropRates.append(hopEntry)
            with self.dataLock:
                self.enabledHops.clear()
                self.failedHops.clear()
            log.debug('[DropRate] {0}\n'.format(hopEntry))