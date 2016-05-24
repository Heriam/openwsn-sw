# Copyright (c) 2010-2013, Regents of the University of California. 
# All rights reserved. 
#  
# Released under the BSD 3-Clause license as published at the link below.
# https://openwsn.atlassian.net/wiki/display/OW/License

'''
Contains the remoteConnector class for --rover mode to enable
connection with remote rovers.
'''

import logging
log = logging.getLogger('remoteConnectorServer')
log.setLevel(logging.ERROR)
log.addHandler(logging.NullHandler())

import threading
import zmq
import copy

from pydispatch import dispatcher


class remoteConnectorServer():

    def __init__(self, zmqport=50000):

        # log
        log.info("creating instance")

        # local variables
        self.zmqport                   = zmqport
        self.roverdict                 = {}
        self.stateLock                 = threading.Lock()
        self.networkPrefix             = None
        self._subcribedDataForDagRoot  = False

        # give this thread a name
        self.name = 'remoteConnectorServer'

        # initiate ZeroMQ connection
        context = zmq.Context()
        self.publisher = context.socket(zmq.PUB)
        self.publisher.setsockopt(zmq.IPV6,1)
        self.publisher.setsockopt(zmq.IPV4ONLY, 0)
        self.publisher.bind("tcp://*:%d" % self.zmqport)
        self.subscriber = context.socket(zmq.SUB)
        self.subscriber.setsockopt(zmq.IPV6,1)
        self.subscriber.setsockopt(zmq.IPV4ONLY, 0)
        self.subscriber.setsockopt(zmq.SUBSCRIBE, "")
        log.info('Publisher started')

        self.threads = []
        t = threading.Thread(target=self._recvdFromRemote)
        t.setDaemon(True)
        t.start()
        self.threads.append(t)

        
    #======================== eventBus interaction ============================
    
    def _sendToRemote_handler(self,sender, signal, data):

        self.publisher.send_json({'sender' : sender, 'signal' : signal, 'data': data.encode('hex')})
        log.info('Message sent: sender: ' + sender, 'signal: ' + signal, 'data: '+ data.encode('hex'))


    def _recvdFromRemote(self):
        while True:
            event = self.subscriber.recv_json()
            dispatcher.send(
                sender  =  event['sender'].encode("utf8"),
                signal  =  event['signal'].encode("utf8"),
                data    =  event['data']
            )

    
    #======================== public ==========================================
    
    def quit(self):
        raise NotImplementedError()

    def initRoverConn(self, newroverdict):
        # clear history
        dispatcher.disconnect(self._sendToRemote_handler)
        while len(self.roverdict)>0:
            for oldIP in self.roverdict.keys():
                self.subscriber.disconnect("tcp://%s:%s" % (oldIP, self.zmqport))
                self.roverdict.pop(oldIP)

        # add new configuration
        self.roverdict = copy.deepcopy(newroverdict)
        log.info('Rover connection:', str(self.roverdict))
        for roverIP in self.roverdict.keys():
            self.subscriber.connect("tcp://%s:%s" % (roverIP, self.zmqport))
            for serial in self.roverdict[roverIP]:
                if "@" in serial:
                    signal = 'fromMoteConnector@'+serial
                    dispatcher.connect(
                        self._sendToRemote_handler,
                        signal = signal.encode('utf8')
                    )

    def closeRoverConn(self, ipAddr):
        if ipAddr in self.roverdict.keys():
            self.subscriber.disconnect("tcp://%s:%s" % (ipAddr, self.zmqport))
            self.roverdict.pop(ipAddr)