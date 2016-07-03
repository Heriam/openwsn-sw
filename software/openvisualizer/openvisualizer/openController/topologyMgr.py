# Copyright (c) 2010-2013, Regents of the University of California.
# All rights reserved.
#
# Released under the BSD 3-Clause license as published at the link below.
# https://openwsn.atlassian.net/wiki/display/OW/License

'''
stores and manages the information about the devices, their capabilities, reachability, and so on.

'''
from openvisualizer.eventBus import eventBusClient
from openvisualizer.RPL.topology import topology as topo
import threading
import logging
import networkx as nx

log = logging.getLogger('topologyMgr')
log.setLevel(logging.ERROR)
log.addHandler(logging.NullHandler())

class topologyMgr(eventBusClient.eventBusClient):

    SINGLE_PATH   = 0
    PARALLEL_PATH = 1
    FULL_PATH     = 2

    TRACKID_DEFAULT = 1

    def __init__(self):

        # log
        log.info("create instance")

        # store params
        self.topoLock          = threading.Lock()
        self.topo              = nx.Graph()
        self.rootEui64List     = []
        self.track             = nx.DiGraph()
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

    def getTrack(self):
        with self.topoLock:
            return self.track

    def getRepType(self):

        return self.repType

    def setRepType(self, t):

        self.repType = t

    def getTopo(self):
        with self.topoLock:
            return self.topo


    # ================================ private ==============================


    def _computeBitmap(self, srcRoute):
        txMote = None
        bitmap = ['0'] * self.track.graph['bitOffset']
        if self.repType == self.SINGLE_PATH:
            for rxMote in srcRoute:
                if txMote:
                    bitIndex = self.track[txMote][rxMote]['bitIndex']
                    bitmap[bitIndex] = '1'
                txMote = rxMote

        elif self.repType == self.PARALLEL_PATH:
            mediatNodes = srcRoute[1:-1]
            if mediatNodes:
                newTrack = self.track.copy()
                newTrack.remove_nodes_from(mediatNodes)
                altPath = nx.shortest_path(newTrack, srcRoute[0], srcRoute[-1])
            else:
                altPath = list(nx.shortest_simple_paths(self.track, srcRoute[0], srcRoute[-1]))[1:2][0]
            for rxMote in srcRoute:
                if txMote:
                    bitIndex = self.track[txMote][rxMote]['bitIndex']
                    bitmap[bitIndex] = '1'
                txMote = rxMote
            txMote = None
            for rxMote in altPath:
                if txMote:
                    bitIndex = self.track[txMote][rxMote]['bitIndex']
                    bitmap[bitIndex] = '1'
                txMote = rxMote

        elif self.repType == self.FULL_PATH:
            bitmap = ['1'] * self.track.graph['bitOffset']

        return ''.join([bit for bit in bitmap])

    def _updateTrack(self, graph, srcRoute, track = nx.DiGraph(), newArcs = []):

        if not track:
            track.graph['trackID'] = self.TRACKID_DEFAULT
            track.graph['srcArcs'] = []
            track.graph['bitOffset'] = 0
            track.add_node(srcRoute[-1])
        if srcRoute[0] in track:
            track.graph['newArcs'] = newArcs
            return track
        else:
            _0hop = [node for node in srcRoute if node in track][0]
            _1hop = [node for node in srcRoute if node not in track][-1]
            arcBits = []
            arcEdges  = []
            edgeNode1 = _0hop
            altPaths  = list(nx.shortest_simple_paths(graph, _1hop, _0hop))[1:]
            arcPath   = []

            # find a sibling path to build an ARC
            for altPath in altPaths:
                if altPath[-2] in track and altPath[-2] not in srcRoute:
                    arcPath = altPath
                    break
            # choose a non-sibling path if not find;
            if not arcPath:
                arcPath = altPaths[0] if altPaths else [_1hop, _0hop]

            medNodes = [node for node in arcPath if node not in track]
            edgeNode2 = arcPath[arcPath.index(medNodes[-1]) + 1]

            preHop = edgeNode1
            for nexHop in medNodes:
                arcEdges.append((nexHop, preHop))
                track.add_edge(nexHop, preHop, {'bitIndex': track.graph['bitOffset']})
                track.graph['bitOffset'] +=1
                arcBits.append(track.graph['bitOffset'])
                preHop = nexHop

            medNodes.reverse()

            preHop = edgeNode2
            for nexHop in medNodes:
                arcEdges.append((nexHop, preHop))
                track.add_edge(nexHop, preHop, {'bitIndex': arcBits.pop()})
                preHop = nexHop

            track.graph['bitOffset'] += 1
            track.graph['srcArcs'] = arcEdges + track.graph['srcArcs']
            newArcs += [arcEdges]

            return self._updateTrack(graph,srcRoute,track, newArcs)

    def _updateTrackSchedule(self, track):

        self.dispatch(
            signal='installTrack',
            data=track
        )

    # ============================== eventbus ===================================


    def _updateTopology(self, sender, signal, data):
        '''
        updates topology
        '''
        prefer = data[0]
        source = data[1]
        parent = tuple(data[2][0])

        try:
            with self.topoLock:
                if prefer == topo.MAX_PARENT_PREFERENCE:
                    if source in self.topo.graph and self.topo.graph[source][prefer-1] != parent:
                        self.topo.remove_edges_from(self.topo.graph[source])
                    self.topo.graph[source] = [(None,None)]*topo.MAX_PARENT_PREFERENCE
                self.topo.add_edge(source,parent,{'preference':prefer})
                self.topo.graph[source][prefer-1] = (source,parent)
        except KeyError as err:
            print "RPLTOARC Error: source{0}, parent{1}, preference {2}. {3}".format(source,parent,prefer,err)

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
        srcRoute = [tuple(hop) for hop in data] + [self.rootEui64List[0]]
        with self.topoLock:
            self._updateTrack(self.topo, srcRoute, self.track, [])

        if self.track.graph['newArcs']:
            self._updateTrackSchedule(self.track)

        bitMap = self._computeBitmap(srcRoute)

        return bitMap