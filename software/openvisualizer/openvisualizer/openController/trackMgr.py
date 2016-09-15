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
import datetime as dt
import logging
log = logging.getLogger('trackMgr')
log.setLevel(logging.ERROR)
log.addHandler(logging.NullHandler())
import openvisualizer.openvisualizer_utils as u

class trackMgr(eventBusClient.eventBusClient):

    SINGLE_PATH = 0
    FULL_PATH = 1

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
        if self.getTrackers():
            self.getTrackers().repType = t

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
        parentList = data[1]
        source = data[0]
        newEdges = [(source, tuple(p[1]), {'preference': p[0]}) for p in parentList]

        with self.topoLock:
            if source in self.topo.graph:
                self.topo.remove_edges_from(self.topo.graph[source])
            self.topo.add_edges_from(newEdges)
            self.topo.graph[source] = newEdges

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
            srcRoute = [tuple(hop) for hop in rplRoute]
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
        medNodes.reverse()

        preHop = edgeNode2
        for nexHop in medNodes:
            arcEdges.append((nexHop, preHop, {'bit': tracker.bitOffset}))
            tracker.bitOffset += 1
            arcBits.append(tracker.bitOffset)
            preHop = nexHop

        medNodes.reverse()
        bits = arcBits[:]

        preHop = edgeNode1
        if _1hop != tracker.srcRoute[0]:
            for nexHop in medNodes:
                arcEdges.append((nexHop, preHop, {'bit': bits.pop()}))
                preHop = nexHop
        else:
            arcEdges.append((medNodes[0], preHop, {'bit': bits.pop()}))

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
        self.bitStrings  = {}
        self.track       = nx.DiGraph()
        self.lastTxBmp   = dt.datetime.now()
        self.lastRxBmp   = dt.datetime.now()
        self.lastRxAsn   = dt.datetime.now()

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
        bitString = ''
        (moteId, asn, bitBytes) = data

        thisRxAsn = asn[0]+(asn[1]<<16)+(asn[2]<<32)
        self.lastRxBmp = dt.datetime.now()

        for i in bitBytes:
            bitMap     = bin(i)[2:]
            bitMap     = ''.join([bit for bit in ['0']*(8-len(bitMap))]) + bitMap
            bitString  = bitString + bitMap

        AsnDelta    = thisRxAsn - self.lastRxAsn if self.lastRxAsn else 0


    def getBitmap(self, dst):
        thisTxBmp   = dt.datetime.now()
        txBmpDelta  = thisTxBmp - self.lastTxBmp
        txRxbmpGap  = thisTxBmp - self.lastRxBmp
        return self.bitStrings.get(dst).get(self.repType)

    def _computeBitmap(self, dstAddr):
        entry = {}
        route = nx.shortest_path(self.track, dstAddr, self.srcRoute[-1])
        txMote = None
        bitmap = ['0'] * self.bitOffset
        # self.repType == trackMgr.SINGLE_PATH:
        for rxMote in route:
            if txMote:
                bitIndex = self.track[txMote][rxMote]['bit']
                bitmap[bitIndex] = '1'
            txMote = rxMote
        entry[trackMgr.SINGLE_PATH] = ''.join([bit for bit in bitmap])
        # self.repType == trackMgr.FULL_PATH:
        bitmap = ['1'] * self.bitOffset
        entry[trackMgr.FULL_PATH] = ''.join([bit for bit in bitmap])
        return entry