# Copyright (c) 2010-2013, Regents of the University of California.
# All rights reserved.
#
# Released under the BSD 3-Clause license as published at the link below.
# https://openwsn.atlassian.net/wiki/display/OW/License
'''
stores and manages the information about the devices, their capabilities, reachability, and so on.

'''

import networkx as nx
from collections import namedtuple
from openvisualizer.eventBus import eventBusClient
import threading
import logging
log = logging.getLogger('trackMgr')
log.setLevel(logging.ERROR)
log.addHandler(logging.NullHandler())
import openvisualizer.openvisualizer_utils as u

class trackMgr(eventBusClient.eventBusClient):

    SINGLE_PATH = 0
    PARALLEL_PATH = 1
    FULL_PATH = 2

    def __init__(self):

        # log
        log.info("create instance")

        # store params
        self.rootLock          = threading.Lock()
        self.topoLock          = threading.Lock()
        self.repType           = self.SINGLE_PATH
        self.rootEui64         = None
        self.tracks            = {}
        self.topo              = nx.Graph()

        # init super class
        eventBusClient.eventBusClient.__init__(
            self,
            name='trackMgr',
            registrations=[
                {
                    'sender': self.WILDCARD,
                    'signal': 'updateParents',
                    'callback': self._updateTopology,
                },
                {
                    'sender': self.WILDCARD,
                    'signal': 'infoDagRoot',
                    'callback': self._updateRoot,
                },
                {
                    'sender': self.WILDCARD,
                    'signal': 'getBitmap',
                    'callback': self._bitmapRequest,
                },
                {
                    'sender': self.WILDCARD,
                    'signal': 'fromMote.bitString',
                    'callback': self._bitmapFeedback,
                }
            ]
        )

    # ======================== public =======================

    def getDagRoot(self):
        '''
        returns the DAGroot's EUI64 address.

        '''
        return self.rootEui64

    def getRepType(self):
        '''
        returns replication type.

        '''
        return self.repType

    def setRepType(self, t):
        '''
        sets replication type.

        '''
        self.repType = t

    def getTopo(self):
        '''
        returns topology
        '''
        with self.topoLock:
            return self.topo

    def getTrackers(self):
        '''
        returns tracks
        '''
        return self.tracks.get(1)

    # ======================== private ======================

    def _updateTopology(self, sender, signal, data):
        '''
        updates topology
        '''
        returnVal = self._dispatchAndGetResult(
            signal='getStateElem',
            data='Neighbors'
        )
        edges = []

        # gets the schedule of every mote
        for mote64bID, neiList in returnVal.items():
            for neiInfo in neiList[:]:
                if neiInfo['addr'] != " (None)":
                    neiInfo['addr'] = tuple([int(i, 16) for i in neiInfo['addr'].split(' ')[0].split('-')])
                    edges.append((mote64bID, neiInfo['addr']))

        with self.topoLock:
            self.topo.clear()
            self.topo.add_edges_from(edges)

    def _updateRoot(self, sender, signal, data):
        '''
        Record the DAGroot's EUI64 address.

        '''
        newDagRootEui64 = tuple(data['eui64'])

        with self.rootLock:
            sameDAGroot = (self.rootEui64 == newDagRootEui64)
            # register the DAGroot
            if data['isDAGroot'] == 1 and (not sameDAGroot):
                # log
                log.info("[trackMgr] registering DAGroot {0}".format(u.formatAddr(newDagRootEui64)))
                # store DAGroot
                self.rootEui64 = newDagRootEui64
            if data['isDAGroot'] == 0 and sameDAGroot:
                # log
                log.info("[trackMgr] unregistering DAGroot {0}".format(u.formatAddr(newDagRootEui64)))
                # clear DAGroot
                self.rootEui64 = None

    def _bitmapRequest(self, sender, signal, data):
        '''
        returns bitmap for corresponded destination.

        '''
        inTrack = False
        tracker = None
        dstAddr = tuple(data)
        # returns bitmap
        for (trackId,tracker) in self.tracks.items():
            if dstAddr in tracker.track:
                inTrack = True
                break
        if not inTrack:
            # create a new track
            trackId = len(self.tracks) + 1
            rplRoute = self._dispatchAndGetResult('getSourceRoute', list(dstAddr))
            if len(rplRoute) >= 2:
                srcRoute = [tuple(hop) for hop in rplRoute]
            else:
                srcRoute = self._getShortestPath(dstAddr)
                if not srcRoute:
                    return (None,None)

            tracker = self._buildTrack(Tracker(srcRoute,trackId,self.repType))
            self.tracks[trackId] = tracker
        return tracker.getBitmap(dstAddr)

    def _bitmapFeedback(self, sender, signal, data):
        self.tracks.get(data[0]).feedBits(data[1:])

    def _buildTrack(self, tracker):

        if tracker.srcRoute[0] in tracker.track:
            self.dispatch('scheduleTrack', (tracker.trackId, tracker.arcs))
            tracker.postInit()
            return tracker

        _0hop = [node for node in tracker.srcRoute if node in tracker.track][0]
        _1hop = [node for node in tracker.srcRoute if node not in tracker.track][-1]

        ARC   = namedtuple('ARC', 'bits edges arcPath hop')

        edgeNode1 = _0hop
        altPaths = list(nx.shortest_simple_paths(self.topo, _1hop, _0hop))[1:]
        arcPath = []
        arcBits = []
        arcEdges= []

        # find a sibling path to build an ARC
        for altPath in altPaths:
            if altPath[-2] in tracker.track and altPath[-2] not in tracker.srcRoute:
                arcPath = altPath
                break
        # choose a non-sibling path if not find;
        if not arcPath:
            arcPath = altPaths[0] if altPaths else [_1hop, _0hop]

        medNodes = [node for node in arcPath if node not in tracker.track]
        edgeNode2 = arcPath[arcPath.index(medNodes[-1]) + 1]

        preHop = edgeNode1
        for nexHop in medNodes:
            arcEdges.append((nexHop, preHop, {'bit': tracker.bitOffset}))
            tracker.bitOffset += 1
            arcBits.append(tracker.bitOffset)
            preHop = nexHop

        medNodes.reverse()
        bits = arcBits[:]

        preHop = edgeNode2
        for nexHop in medNodes:
            arcEdges.append((nexHop, preHop, {'bit': bits.pop()}))
            preHop = nexHop

        tracker.bitOffset += 1
        tracker.track.add_edges_from(arcEdges)
        tracker.arcs.append(ARC(bits=arcBits,edges=arcEdges,arcPath=arcPath,hop=(_1hop,_0hop)))

        return self._buildTrack(tracker)


    def _getShortestPath(self, dst):
        '''
        returns shortest path
        '''

        with self.topoLock:
            try:
                path = nx.shortest_path(self.topo, dst, self.rootEui64)
            except nx.exception.NetworkXNoPath as nopatherr:
                log.warning('[topologyMgr]:{0}'.format(nopatherr))
                return
            except nx.exception.NetworkXError as err:
                log.warning('[topologyMgr]:{0}'.format(err))
                return
            except:
                print '[topologyMgr] error when getting shortest path with input {0}'.format(dst)
                return

        return path


class Tracker():

    def __init__(self, srcRoute, trackId, repType):

        # store params
        self.trackId     = trackId
        self.bitOffset   = 0
        self.arcs        = []
        self.srcRoute    = srcRoute
        self.repType     = repType
        self.bitMap      = {}
        self.seq         = 0
        self.bitStrings  = {}
        self.track       = nx.DiGraph()

        # init tracker
        self.track.add_node(srcRoute[-1])


    def postInit(self):

        # build bitMap
        for (txMote,rxMote) in self.track.edges():
            bit = self.track[txMote][rxMote]['bit']
            self.bitMap[bit] = (txMote,rxMote)

        # calculate bitStrings
        for node in self.track.nodes():
            self.bitStrings[node] = self._computeBitmap(node)

    def getTrackId(self):
        return self.trackId

    def getBitOffset(self):
        return self.bitOffset

    def getArcs(self):
        return self.arcs

    def getSrcRoute(self):
        return self.srcRoute

    def getTrack(self):
        return self.track

    def feedBits(self, data):
        (moteId, asn, seq, bitBytes) = data
        print data

    def getBitmap(self, dst):
        self.seq +=1
        return self.bitStrings.get(dst), self.seq

    def _computeBitmap(self, dstAddr):
        route = nx.shortest_path(self.track, dstAddr, self.srcRoute[-1])
        txMote = None
        bitmap = ['0'] * self.bitOffset
        if self.repType == trackMgr.SINGLE_PATH:
            for rxMote in route:
                if txMote:
                    bitIndex = self.track[txMote][rxMote]['bit']
                    bitmap[bitIndex] = '1'
                txMote = rxMote

        elif self.repType == trackMgr.PARALLEL_PATH:
            mediatNodes = route[1:-1]
            if mediatNodes:
                newTrack = self.track.copy()
                newTrack.remove_nodes_from(mediatNodes)
                altPath = nx.shortest_path(newTrack, route[0], route[-1])
            else:
                altPath = list(nx.shortest_simple_paths(self.track, route[0], route[-1]))[1:2][0]
            for rxMote in route:
                if txMote:
                    bitIndex = self.track[txMote][rxMote]['bit']
                    bitmap[bitIndex] = '1'
                txMote = rxMote
            txMote = None
            for rxMote in altPath:
                if txMote:
                    bitIndex = self.track[txMote][rxMote]['bit']
                    bitmap[bitIndex] = '1'
                txMote = rxMote

        elif self.repType == trackMgr.FULL_PATH:
            bitmap = ['1'] * self.bitOffset

        return ''.join([bit for bit in bitmap])