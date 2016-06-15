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

    SINGLE_PATH   = 'single'
    PARALLEL_PATH = 'parallel'
    FULL_PATH     = 'full'

    def __init__(self):

        # log
        log.info("create instance")

        # store params
        self.topoLock         = threading.Lock()
        self.topo              = nx.Graph()
        self.rootEui64List     = []
        self.tracks            = []
        self.bitmaps           = {} #{dst:{'single': , 'parallel': , 'full': }}
        self.repType           = self.SINGLE_PATH

        #  { <trackID>: DiGraph}


        eventBusClient.eventBusClient.__init__(
            self,
            name='topologyMgr',
            registrations=[
                {
                    'sender': self.WILDCARD,
                    'signal': 'infoDagRoot',
                    'callback': self._updateRoot,
                },
                {
                    'sender': self.WILDCARD,
                    'signal': 'updateParents',
                    'callback': self._updateTopology,
                },
                {
                    'sender': self.WILDCARD,
                    'signal': 'getBitmap',
                    'callback': self._bitmapRequest,
                }
            ]
        )

    # ============================== public ====================================

    def getDagRootList(self):
        return self.rootEui64List

    def getBitmap(self, dst):

        if dst in self.bitmaps.keys() and self.repType in self.bitmaps[dst]:
            return self.bitmaps[dst][self.repType]
        else:
            return None

    def getTrack(self, dst):

        for DiGraph in self.tracks:
            if dst in DiGraph:
                return DiGraph

        return None

    def getRepType(self):

        return self.repType

    def setRepTYpe(self, t):

        self.repType = t

    # ============================== eventbus ===================================


    def _updateTopology(self,sender,signal,data):
        '''
        updates topology
        '''

        returnVal = self._dispatchAndGetResult(
            signal='getStateElem',
            data='Neighbors'
        )

        with self.topoLock:
            self.topo.clear()
            # gets the schedule of every mote
            for mote64bID, neiList in returnVal.items():
                for neiInfo in neiList[:]:
                    if neiInfo['addr'] == " (None)":
                        neiList.remove(neiInfo)
                    else:
                        neiInfo['addr'] = tuple([int(i,16) for i in neiInfo['addr'].split(' ')[0].split('-')])
                        self.topo.add_edge(mote64bID, neiInfo['addr'])

    def _updateRoot(self, sender, signal, data):
        '''
        Record the DAGroot's EUI64 address.

        '''
        addr = tuple(data['eui64'])
        if data['isDAGroot'] == 1:
            if addr not in self.rootEui64List:
                self.rootEui64List.append(addr)
        elif addr in self.rootEui64List:
            self.rootEui64List.remove(addr)

    def _bitmapRequest(self, sender, signal, data):
        '''
        returns bitmap for corresponded destination.

        '''
        dst = tuple(data)

        bitMap = self.getBitmap(dst)
        if bitMap:
            print '======  inTrack Destination  ======'
            return bitMap
        else:
            inTrack = self.getTrack(dst)
            if not inTrack:
                self._installNewTrack(dst)
            else:
                print '======  inTrack Destination  ======'
            return self._computeBitmap(dst)

    # ================================ private ==============================



    def _installNewTrack(self, dst):

        newTrack = self._computeNewTrack(dst)
        newTrackID = len(self.tracks) + 1
        newTrack.graph['trackID'] = newTrackID
        self._cmdInstallTrack(newTrack)
        self.tracks.append(newTrack)

    def _computeBitmap(self, dst):
        track = self.getTrack(dst)
        paths = list(nx.shortest_simple_paths(track, self.rootEui64List[0], dst))
        if self.repType == self.SINGLE_PATH:
            path = paths[0]
            bitmap = []
            while len(bitmap) < track.graph['bitmapLength']:
                bitmap.append('0')
            txMote = None
            for rxMote in path:
                if txMote:
                    bitIndex = track[txMote][rxMote]['bitIndex']
                    bitmap[bitIndex] = '1'
                txMote = rxMote
            newBitmap = ''.join([bit for bit in bitmap])
            if dst not in self.bitmaps:
                self.bitmaps[dst] = {}
            self.bitmaps[dst][self.SINGLE_PATH] = newBitmap
            return newBitmap

    def _computeNewTrack(self, dst):

        with self.topoLock:
            furthestNode = list(nx.bfs_tree(self.topo, self.rootEui64List[0]))[0]
            backboneTrack = self._computeTrack(furthestNode)
            if dst in backboneTrack:
                return backboneTrack
            else:
                return self._computeTrack(dst)

    def _computeTrack(self, dstAddr):

        shortPath = nx.shortest_path(self.topo, self.rootEui64List[0], dstAddr)
        newTrack = nx.DiGraph()
        preNode  = None
        bitOffset = 0
        orderList = []
        for nexNode in shortPath:
            if preNode:
                newTrack.add_edge(preNode, nexNode, {'bitIndex': bitOffset})
                bitOffset +=1
                orderList.append((preNode, nexNode))
                protectPaths = list(nx.shortest_simple_paths(self.topo, preNode, nexNode))[1:]
                if protectPaths:
                    firstProPath = protectPaths[0]
                    preProNode = None
                    for nexProNode in firstProPath:
                        if preProNode:
                            if nexProNode in newTrack and preProNode in newTrack[nexProNode].keys():
                                bitIndex = newTrack[nexProNode][preProNode]['bitIndex']
                                newTrack.add_edge(preProNode, nexProNode, {'bitIndex': bitIndex})
                            else:
                                newTrack.add_edge(preProNode, nexProNode, {'bitIndex': bitOffset})
                                bitOffset +=1
                            orderList.append((preProNode, nexProNode))
                        preProNode = nexProNode
            preNode = nexNode
        newTrack.graph['bitmapLength'] = bitOffset
        newTrack.graph['orderList']    = orderList
        return newTrack

    def _cmdInstallTrack(self, newTrack):

        self.dispatch(
            signal='installTrack',
            data=newTrack
        )

    def _getRunningSlotFrame(self, frameID = '1'):

        self.dispatch(
            signal='getSchedule',
            data= frameID
        )