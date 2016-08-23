
import networkx as nx
import threading
import datetime as dt
import logging
from openvisualizer.eventBus import eventBusClient
log = logging.getLogger('trackMgr')
log.setLevel(logging.ERROR)
log.addHandler(logging.NullHandler())

class trackMgr(eventBusClient.eventBusClient):

    ED9 = (0, 18, 75, 0, 6, 13, 158, 217)
    F4A = (0, 18, 75, 0, 6, 13, 159, 74)
    F02 = (0, 18, 75, 0, 6, 13, 159, 2)
    ED8 = (0, 18, 75, 0, 6, 13, 158, 216)
    EC3 = (0, 18, 75, 0, 6, 13, 158, 195)
    EEC = (0, 18, 75, 0, 6, 13, 158, 236)
    EF6 = (0, 18, 75, 0, 6, 13, 158, 246)
    EC7 = (0, 18, 75, 0, 6, 13, 158, 199)

    BITMAPLEN = 11

    def __init__(self):
        # log
        log.info("create instance")

        self.topoLock    = threading.Lock()
        self.countLock   = threading.Lock()
        self.bitmapLock1 = threading.Lock()
        self.bitmapLock4 = threading.Lock()
        self.track = nx.DiGraph()
        self.topo  = nx.Graph()
        self.bitString4 = '11111111111'
        self.bitString1 = '11111111111'
        self.lastRxBmp1 = dt.datetime.now()
        self.lastRxBmp4 = dt.datetime.now()
        self.roundTime  = dt.datetime.now()
        self.pdrInterval= dt.timedelta(minutes=5)
        self.timeOutDlta= dt.timedelta(seconds=5)
        self.failTimes  = [0]*self.BITMAPLEN
        self.sentTimes  = 0
        self.track.add_edges_from(
            [
                (self.ED9,self.F4A,{'bit': 0,'pdr':1.000}),  # 9ed9 -> 9f4a
                (self.ED9,self.F02,{'bit': 1,'pdr':1.000}),  # 9ed9 -> 9f02
                (self.F4A,self.F02,{'bit': 2,'pdr':1.000}),  # 9f4a -> 9f02
                (self.F02,self.F4A,{'bit': 2,'pdr':1.000}),  # 9f02 -> 9f4a
                (self.F4A,self.ED8,{'bit': 3,'pdr':1.000}),  # 9f4a -> 9ed8
                (self.F02,self.EC7,{'bit': 4,'pdr':1.000}),  # 9f02 -> 9ec7
                (self.ED8,self.EC7,{'bit': 5,'pdr':1.000}),  # 9ed8 -> 9ec7
                (self.EC7,self.ED8,{'bit': 5,'pdr':1.000}),  # 9ec7 -> 9ed8
                (self.ED8,self.EF6,{'bit': 6,'pdr':1.000}),  # 9ed8 -> 9ef6
                (self.EC7,self.EEC,{'bit': 7,'pdr':1.000}),  # 9ec7 -> 9eec
                (self.EF6,self.EEC,{'bit': 8,'pdr':1.000}),  # 9ef6 -> 9eec
                (self.EEC,self.EF6,{'bit': 8,'pdr':1.000}),  # 9eec -> 9ef6
                (self.EF6,self.EC3,{'bit': 9,'pdr':1.000}),  # 9ef6 -> 9ec3
                (self.EEC,self.EC3,{'bit': 10,'pdr':1.000})  # 9eec -> 9ec3
             ]
        )

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
                    'signal': 'getBitString',
                    'callback': self._bitStringRequest,
                },
                {
                    'sender': self.WILDCARD,
                    'signal': 'fromMote.bitString',
                    'callback': self._bitStringFeedback,
                }
            ]
        )
    # ========================== public ============================

    def getTopo(self):
        '''
        returns topology
        '''
        with self.topoLock:
            return self.topo

    def getTrack(self):
        '''
        returns tracks
        '''
        return self.track

    # ========================== private ===========================

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

    def _bitStringRequest(self,sender,signal,data):
        if data == 4:
            if dt.datetime.now() - self.lastRxBmp4 > self.timeOutDlta:
                with self.bitmapLock4:
                    self.bitString4 = '11111111111'
            return self.bitString4
        elif data == 1:
            if dt.datetime.now() - self.lastRxBmp1 > self.timeOutDlta:
                with self.bitmapLock1:
                    self.bitString1 = '11111111111'
                with self.countLock:
                    self.sentTimes += 1
            return self.bitString1

    def _bitStringFeedback(self,sender,signal,data):
        bitString = ''
        (trackId, moteId, asn, bitBytes) = data
        for i in bitBytes:
            bitVal = bin(i)[2:]
            bitString = bitString + ''.join([bit for bit in ['0'] * (8 - len(bitVal))]) + bitVal
        failedBits = [i for i, x in enumerate(bitString) if x == '1']
        failedHops = [(i,x) for i, x in self.track.edges() if self.track[i][x]['bit'] in failedBits]

        if trackId == 4:
            self.lastRxBmp4 = dt.datetime.now()
            if self.bitString4 == '11111111111':
                track = self.track.copy()
                track.remove_edges_from(failedHops)
                altPath = nx.shortest_path(track, self.ED9, self.EC3)
                newBitmap = ['0'] * self.BITMAPLEN
                preHop = altPath[0]
                for nexHop in altPath[1:]:
                    newBitmap[self.track[preHop][nexHop]['bit']] = '1'
                with self.bitmapLock4:
                    self.bitString4 = ''.join([bit for bit in newBitmap])

        elif trackId == 1:
            self.lastRxBmp1 = dt.datetime.now()
            with self.countLock:
                for bitIndex in failedBits:
                    self.failTimes[bitIndex] +=1
            if self.lastRxBmp1 - self.roundTime > self.pdrInterval:
                self._updatePdr()

    def _updatePdr(self):

        pdr = [ i * (1.000/self.sentTimes) for i in self.failTimes]

        for (t,r) in self.track.edges():
            self.track[t][r]['pdr'] = pdr[self.track[t][r]['bit']]
            print pdr

        with self.countLock:
            self.failTimes = [0] * self.BITMAPLEN
            self.sentTimes = 0






