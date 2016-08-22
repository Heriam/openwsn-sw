# Copyright (c) 2010-2013, Regents of the University of California.
# All rights reserved.
#
# Released under the BSD 3-Clause license as published at the link below.
# https://openwsn.atlassian.net/wiki/display/OW/License
'''
stores and manages the information about the devices, their capabilities, reachability, and so on.

'''

import networkx as nx
import threading
import datetime as dt
import logging
import openvisualizer.openvisualizer_utils as u
from collections import namedtuple
from openvisualizer.eventBus import eventBusClient
from BitmapError import BitmapError
log = logging.getLogger('trackMgr')
log.setLevel(logging.ERROR)
log.addHandler(logging.NullHandler())


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
                    'signal': 'getBitString',
                    'callback': self._bitStringRequest,
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
        if self.getTracker():
            self.getTracker().repType = t

    def getTopo(self):
        '''
        returns topology
        '''
        with self.topoLock:
            return self.topo

    def getTracker(self, trackId = 4):
        '''
        returns tracks
        '''
        return self.tracks.get(trackId)



    # ======================== private ======================

    def _updateTopology(self, sender, signal, data):
        '''
        updates topology
        '''
        parentList = data[1]
        source     = data[0]
        childList  = data[2]
        newEdges = [(source, tuple(p[1]),{'preference': p[0]}) for p in parentList]
        newEdges + [(source,tuple(child),{'preference': self.topo[source][tuple(child)]['preference']
                                if (source in self.topo and tuple(child) in self.topo[source]) else 0}) for child in childList]
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

    def _bitStringRequest(self, sender, signal, data):
        '''
        returns bitString for corresponded destination.

        '''
        print '~~~~~~'
        trackId = data[0]
        print data
        print self.rootEui64
        srcRoute = [tuple(hop) for hop in data[1]] + [self.rootEui64]
        print '987q057409'
        # returns bitString
        tracker = self.tracks.get(trackId)
        print '4313451451'
        if tracker and srcRoute[0] == tracker.srcRoute[0]:
            return tracker.getBitString()
        else:
            # create a new track
            try:
                tracker = self._buildTrack(Tracker(srcRoute, trackId, self.repType))
                self.tracks[trackId] = tracker
                return tracker.getBitString()
            except KeyError as err:
                raise BitmapError(BitmapError.COMPUTATION,
                                  "could not build a new track for srcroute mote {0}, {1}".format(srcRoute, err))

    def _buildTrack(self, tracker):
        '''
        returns tracker class

        '''
        print '~~~~~~~1~~~~~'
        if tracker.srcRoute[0] in tracker.track:
            if tracker.trackId == 4:
                print '~~~~~~~3~~~~~'
                self.dispatch('scheduleTrack', (tracker.trackId, tracker.arcs))
            tracker.postInit()
            return tracker
        print '~~~~~~~2~~~~~'
        _0hop = [node for node in tracker.srcRoute if node in tracker.track][0]
        _1hop = [node for node in tracker.srcRoute if node not in tracker.track][-1]

        ARC   = namedtuple('ARC', 'arcBits arcEdges arcPath hop')
        print '~~~~~~~4~~~~~'
        safeNode1 = _0hop
        altPaths = list(nx.shortest_simple_paths(self.topo, _1hop, _0hop))[1:]
        arcPath = []
        arcBits = []
        Bits = []
        print '~~~~~~~5~~~~~'
        # find a sibling path to build an ARC
        for altPath in altPaths:
            if altPath[-2] in tracker.track and altPath[-2] not in tracker.srcRoute:
                arcPath = altPath
                break
        # choose a non-sibling path if not find;
        print '~~~~~~~6~~~~~'
        if not arcPath:
            arcPath = altPaths[0] if altPaths else [_1hop, _0hop]

        medNodes  = [node for node in arcPath if node not in tracker.track]
        safeNode2 = arcPath[arcPath.index(medNodes[-1]) + 1]
        edge1     = (medNodes[0], safeNode1, {'bit': tracker.bitOffset})
        arcBits.append(tracker.bitOffset)
        tracker.bitOffset += 1
        edge2     = (medNodes[-1], safeNode2, {'bit': tracker.bitOffset})
        arcBits.append(tracker.bitOffset)
        tracker.bitOffset += 1
        arcEdges = [edge1,edge2]
        print '~~~~~~~7~~~~~'
        if tracker.interleave:
            medNodes.reverse()
            tracker.interleave = 0
        else:
            tracker.interleave = 1

        preHop = medNodes[0]
        for nexHop in medNodes[1:]:
            arcEdges.append((nexHop, preHop, {'bit': tracker.bitOffset}))
            Bits.append(tracker.bitOffset)
            arcBits.append(tracker.bitOffset)
            tracker.bitOffset += 1
            preHop = nexHop
        print '~~~~~~~8~~~~~'
        medNodes.reverse()

        preHop = medNodes[0]
        for nexHop in medNodes[1:]:
            arcEdges.append((nexHop, preHop, {'bit': Bits.pop()}))
            preHop = nexHop
        print '~~~~~~~9~~~~~'
        tracker.track.add_edges_from(arcEdges)
        tracker.arcs.append(ARC(arcBits=arcBits,arcEdges=arcEdges,arcPath=arcPath,hop=(_1hop,_0hop)))
        print '~~~~~~~10~~~~~'
        return self._buildTrack(tracker)


    def _getShortestPath(self, dst):
        '''
        returns shortest path
        '''

        with self.topoLock:
            try:
                path = nx.shortest_path(self.topo, dst, self.rootEui64)
            except nx.exception.NetworkXNoPath as nopatherr:
                log.warning('[trackMgr]:{0}'.format(nopatherr))
                return
            except nx.exception.NetworkXError as err:
                log.warning('[trackMgr]:{0}'.format(err))
                return
            except:
                print '[trackMgr] error when getting shortest path with input {0}'.format(dst)
                return

        return path


class Tracker(eventBusClient.eventBusClient):

    def __init__(self, srcRoute, trackId, repType):

        # store params
        self.interleave  = 0
        self.bitLock     = threading.Lock()
        self.trackId     = trackId
        self.arcs        = []
        self.bitOffset   = 0
        self.srcRoute    = srcRoute
        self.srcHops     = []
        self.enabledHops = []
        self.repType     = repType
        self.bitString   = ''
        self.track       = nx.DiGraph()
        self.lastTxBmp   = None
        self.lastRxBmp   = None
        self.lastRxAsn   = None
        self.bitsArcMap  = {}
        self.bitMap = {
            ((0, 18, 75, 0, 6, 13, 158, 217),(0, 18, 75, 0, 6, 13, 159, 74))  : 0, # 9ed9 -> 9f4a
            ((0, 18, 75, 0, 6, 13, 158, 217),(0, 18, 75, 0, 6, 13, 159, 2))   : 1, # 9ed9 -> 9f02
            ((0, 18, 75, 0, 6, 13, 159, 74), (0, 18, 75, 0, 6, 13, 159, 2))   : 2, # 9f4a -> 9f02
            ((0, 18, 75, 0, 6, 13, 159, 2), (0, 18, 75, 0, 6, 13, 159, 74))   : 2, # 9f02 -> 9f4a
            ((0, 18, 75, 0, 6, 13, 159, 74), (0, 18, 75, 0, 6, 13, 158, 216)) : 3, # 9f4a -> 9ed8
            ((0, 18, 75, 0, 6, 13, 159, 2), (0, 18, 75, 0, 6, 13, 158, 199))  : 4, # 9f02 -> 9ec7
            ((0, 18, 75, 0, 6, 13, 158, 216), (0, 18, 75, 0, 6, 13, 158, 199)): 5, # 9ed8 -> 9ec7
            ((0, 18, 75, 0, 6, 13, 158, 199), (0, 18, 75, 0, 6, 13, 158, 216)): 5, # 9ec7 -> 9ed8
            ((0, 18, 75, 0, 6, 13, 158, 216), (0, 18, 75, 0, 6, 13, 158, 246)): 6, # 9ed8 -> 9ef6
            ((0, 18, 75, 0, 6, 13, 158, 199), (0, 18, 75, 0, 6, 13, 158, 236)): 7, # 9ec7 -> 9eec
            ((0, 18, 75, 0, 6, 13, 158, 246), (0, 18, 75, 0, 6, 13, 158, 236)): 8, # 9ef6 -> 9eec
            ((0, 18, 75, 0, 6, 13, 158, 236), (0, 18, 75, 0, 6, 13, 158, 246)): 8, # 9eec -> 9ef6
            ((0, 18, 75, 0, 6, 13, 158, 246), (0, 18, 75, 0, 6, 13, 158, 195)): 9, # 9ef6 -> 9ec3
            ((0, 18, 75, 0, 6, 13, 158, 236), (0, 18, 75, 0, 6, 13, 158, 195)): 10,# 9eec -> 9ec3
        }

        # init tracker
        self.track.add_node(srcRoute[-1])

        eventBusClient.eventBusClient.__init__(
            self,
            "Tracker@{0}".format(trackId),
            registrations=[
                {
                    'sender': self.WILDCARD,
                    'signal': 'fromMote.bitString@{0}'.format(self.trackId),
                    'callback': self._bitStringFeedback,
                }
            ]
        )

    # ======================= public ===========================

    def postInit(self):

        # build bitsArcMap:
        for arc in self.arcs:
            for bit in arc.arcBits:
                self.bitsArcMap[bit] = arc

        # calculate bitStrings
        if self.trackId == 1:
            self.updateEnabledHops(self.bitMap.keys())
        elif self.trackId == 4:
            srcRoute = self.srcRoute[:]
            srcRoute.reverse()
            self.srcHops = self._pathToHops(srcRoute)
            self.updateEnabledHops(self.srcHops)

    def getTrackId(self):
        return self.trackId

    def getBitOffset(self):
        return self.bitOffset

    def getArcs(self):
        return self.arcs

    def getEnabledHops(self):
        return self.enabledHops

    def getSrcRoute(self):
        return self.srcRoute

    def getTrack(self):
        return self.track

    def getBitmap(self):
        return self.bitMap

    def getBitString(self):
        gap =  (dt.datetime.now() - self.lastRxBmp) if self.lastRxBmp else 0
        print "~~~~~~~~~~~~~~~~"
        if gap > dt.timedelta(seconds= 10) and self.trackId == 4:
            self.updateEnabledHops(self.bitMap.keys())
        return self.bitString

    def updateEnabledHops(self, enabledHops):
        newBitString = ['0'] * self.bitOffset
        with self.bitLock:
            for edge in enabledHops:
                newBitString[self.bitMap.get(edge)] = '1'
            self.bitString = ''.join([bit for bit in newBitString])
            self.enabledHops   = enabledHops

    # ======================== private ===============================

    def _bitStringFeedback(self, sender, signal, data):
        bitString  = ''
        (trackId, moteId, asn, bitBytes) = data

        for i in bitBytes:
            bitVal = bin(i)[2:]
            bitString = bitString + ''.join([bit for bit in ['0'] * (8 - len(bitVal))]) + bitVal

        if len(self.enabledHops) == 14 and self.trackId == 4:
            failedBits = [i for i, x in enumerate(bitString) if x == '1']
            failedHops = [i for i, x in self.bitMap.items() if x in failedBits]
            track = self.track.copy()
            track.remove_edges_from(failedHops)
            altPath = nx.shortest_path(track, self.srcRoute[0], self.srcRoute[-1])
            altPath.reverse()
            newHops = self._pathToHops(altPath)
            self.updateEnabledHops(newHops)
            self.lastRxBmp = dt.datetime.now()

        # thisRxAsn = asn[0] + (asn[1] << 16) + (asn[2] << 32)

    def _pathToHops(self, path):

        hops = []
        preHop = path[0]
        for nexHop in path[1:]:
            hops.append((preHop,nexHop))
            preHop = nexHop

        return hops




