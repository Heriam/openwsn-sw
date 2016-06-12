# Copyright (c) 2010-2013, Regents of the University of California.
# All rights reserved.
#
# Released under the BSD 3-Clause license as published at the link below.
# https://openwsn.atlassian.net/wiki/display/OW/License

'''
stores and manages the information about the devices, their capabilities, reachability, and so on.

'''
from openvisualizer.eventBus import eventBusClient
import threading
import logging
import networkx as nx

log = logging.getLogger('topologyMgr')
log.setLevel(logging.ERROR)
log.addHandler(logging.NullHandler())

class topologyMgr(eventBusClient.eventBusClient):

    def __init__(self):

        # log
        log.info("create instance")

        # store params
        self.stateLock         = threading.Lock()
        self.topo              = nx.Graph()

        eventBusClient.eventBusClient.__init__(
            self,
            name='topologyMgr',
            registrations=[]
        )

    def updateTopology(self):
        '''
        updates topology
        '''

        self.topo.clear()

        returnVal = self._dispatchAndGetResult(
            signal='getStateElem',
            data='Neighbors'
        )

        # gets the schedule of every mote
        for mote64bID, neiList in returnVal.items():
            for neiInfo in neiList[:]:
                if neiInfo['addr'] == " (None)":
                    neiList.remove(neiInfo)
                else:
                    neiInfo['addr'] = tuple([int(i,16) for i in neiInfo['addr'].split(' ')[0].split('-')])
                    self.topo.add_edge(mote64bID, neiInfo['addr'])

        print list(nx.shortest_simple_paths(self.topo,(20, 21, 146, 204, 0, 0, 0, 1), (20, 21, 146, 204, 0, 0, 0, 8)))





