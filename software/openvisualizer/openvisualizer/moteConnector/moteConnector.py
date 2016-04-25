# Copyright (c) 2010-2013, Regents of the University of California. 
# All rights reserved. 
#  
# Released under the BSD 3-Clause license as published at the link below.
# https://openwsn.atlassian.net/wiki/display/OW/License
import logging
log = logging.getLogger('moteConnector')
log.setLevel(logging.ERROR)
log.addHandler(logging.NullHandler())

import threading
import socket

from pydispatch import dispatcher

from openvisualizer.eventBus       import eventBusClient
from openvisualizer.moteState      import moteState
from openvisualizer.openController import openController

import OpenParser
import ParserException

class moteConnector(eventBusClient.eventBusClient):
    
    def __init__(self,serialport):
        
        # log
        log.info("creating instance")
        
        # store params
        self.serialport                = serialport
        
        # local variables
        self.parser                    = OpenParser.OpenParser()
        self.stateLock                 = threading.Lock()
        self.networkPrefix             = None
        self._subcribedDataForDagRoot  = False
              
        # give this thread a name
        self.name = 'moteConnector@{0}'.format(self.serialport)
       
        eventBusClient.eventBusClient.__init__(
            self,
            name             = self.name,
            registrations =  [
                {
                    'sender'   : self.WILDCARD,
                    'signal'   : 'infoDagRoot',
                    'callback' : self._infoDagRoot_handler,
                },
                {
                    'sender'   : self.WILDCARD,
                    'signal'   : 'cmdToMote',
                    'callback' : self._cmdToMote_handler,
                },
            ]
        )
        
        # subscribe to dispatcher
        dispatcher.connect(
            self._sendToParser,
            signal = 'fromMoteProbe@'+self.serialport,
        )
        
    def _sendToParser(self,data):
        
        input = data
        
        # log
        if log.isEnabledFor(logging.DEBUG):
            log.debug("received input={0}".format(input))
        
        # parse input
        try:
            (eventSubType,parsedNotif)  = self.parser.parseInput(input)
            assert isinstance(eventSubType,str)
        except ParserException.ParserException as err:
            # log
            log.error(str(err))
            pass
        else:
            # dispatch
            self.dispatch('fromMote.'+eventSubType,parsedNotif)
        
    #======================== eventBus interaction ============================
    
    def _infoDagRoot_handler(self,sender,signal,data):
        
        # I only care about "infoDagRoot" notifications about my mote
        if not data['serialPort']==self.serialport:
            return 
        
        with self.stateLock:
        
            if   data['isDAGroot']==1 and (not self._subcribedDataForDagRoot):
                # this moteConnector is connected to a DAGroot
                
                # connect to dispatcher
                self.register(
                    sender   = self.WILDCARD,
                    signal   = 'bytesToMesh',
                    callback = self._bytesToMesh_handler,
                )
                
                # remember I'm subscribed
                self._subcribedDataForDagRoot = True
                
            elif data['isDAGroot']==0 and self._subcribedDataForDagRoot:
                # this moteConnector is *not* connected to a DAGroot
                
                # disconnect from dispatcher
                self.unregister(
                    sender   = self.WILDCARD,
                    signal   = 'bytesToMesh',
                    callback = self._bytesToMesh_handler,
                )
                
                # remember I'm not subscribed
                self._subcribedDataForDagRoot = False
    
    def _cmdToMote_handler(self,sender,signal,data):
        if  data['serialPort']==self.serialport:
            if data['action']==moteState.moteState.TRIGGER_DAGROOT:
                
                # retrieve the prefix of the network
                with self.stateLock:
                    if not self.networkPrefix:
                        networkPrefix = self._dispatchAndGetResult(
                            signal       = 'getNetworkPrefix',
                            data         = [],
                        )
                        self.networkPrefix = networkPrefix
                
                # create data to send
                with self.stateLock:
                    dataToSend = [
                        OpenParser.OpenParser.SERFRAME_PC2MOTE_SETDAGROOT,
                        OpenParser.OpenParser.SERFRAME_ACTION_TOGGLE,
                    ]+self.networkPrefix
                
                # toggle the DAGroot state
                self._sendToMoteProbe(
                    dataToSend = dataToSend,
                )
            elif data['action'][0]==moteState.moteState.SET_COMMAND:
                # this is command for golden image
                with self.stateLock:
                    [success,dataToSend] = self._GDcommandToBytes(data['action'][1:])

                if success == False:
                    return

                # print dataToSend
                # send command to GD image
                self._sendToMoteProbe(
                    dataToSend = dataToSend,
                )
            elif data['action'][0]==moteState.moteState.INSTALL_SCHEDULE:
                # this is command for 6TiSCH Scheduling
                with self.stateLock:
                    [success, dataToSend] = self._ScheduleToBytes(data['action'][1:])

                if success == False:
                    return

                # send scheduling command to the mote
                self._sendToMoteProbe(
                    dataToSend=dataToSend,
                )
            else:
                raise SystemError('unexpected action={0}'.format(data['action']))

    def _ScheduleToBytes(self, data):
        outcome    = False

        #set actionId
        dataToSend = [OpenParser.OpenParser.SERFRAME_PC2MOTE_SCHEDULECMD]

        #set target slotFrameId
        if data[0] in openController.openController.SLOTFRAME_LIST:
            slotFrameId = openController.openController.SLOTFRAME_LIST.index(data[0])
            dataToSend.append(slotFrameId)
        else:
            print "============================================="
            print "Error ! Invalid slotFrame: " + data[0]
            return [outcome, dataToSend]

        #set operationId
        if data[1] in openController.openController.OPT_LIST:
            operationId = openController.openController.OPT_LIST.index(data[1])
            dataToSend.append(operationId)
        else:
            print "============================================="
            print "Error ! Invalid operation: " + data[1]
            return [outcome, dataToSend]

        #set parameters
        if operationId <= 3:
            if len(data) <3:
                print "============================================="
                print "Error ! Parameters are missing!"
                return [outcome, dataToSend]
            # set cell (slotOffset, channelOffset)
            dataToSend += list(data[2][openController.openController.PARAMS_CELL])
            if operationId == 2:
                # set remapped cell (slotOffset, channelOffset)
                dataToSend += list(data[2][openController.openController.PARAMS_REMAPTOCELL])
            if operationId <= 1:
                # set cell typeId
                typeId = openController.openController.TYPE_LIST.index(
                    data[2][openController.openController.PARAMS_TYPE])
                dataToSend.append(typeId)
                if typeId <2:
                    # set bitIndex only when Tx
                    if typeId==0:
                        bitIndex = data[2][openController.openController.PARAMS_BITINDEX]
                        dataToSend.append(bitIndex)
                    # set neighbor addr
                    neiAddr = data[2][openController.openController.PARAMS_NEIGHBOR]
                    addList = [int(c, 16) for c in neiAddr.split(' ')[0].split('-')]
                    if len(addList) == 8:
                        dataToSend += addList
                    else:
                        print "============================================="
                        print "Error ! Wrong address format: " + neiAddr
                        return [outcome, dataToSend]
                    #set shared boolean
                    if data[2][openController.openController.PARAMS_SHARED]:
                        dataToSend.append(1)
                    else:
                        dataToSend.append(0)
                    #set BFRId
                    BFRId = data[2][openController.openController.PARAMS_BFRID]
                    dataToSend.append([ord(c) for c in list(str(BFRId))])
        elif len(data) > 2:
            print "============================================="
            print "Error ! Unexpected content: " + data[2:]
            return [outcome, dataToSend]

        # the command is legal if I got here
        outcome = True
        print dataToSend
        return [outcome, dataToSend]

    def _GDcommandToBytes(self,data):
        
        outcome    = False
        dataToSend = []

        # get imageId
        if data[0] == 'gd_root':
            imageId  = 1
        elif data[0] == 'gd_sniffer':
            imageId = 2
        else:
            print "============================================="
            print "Wrong Image ({0})! (Available: gd_root OR gd_sniffer)\n".format(data[0])
            return [outcome,dataToSend]

        # get commandId
        commandIndex = 0
        for cmd in moteState.moteState.COMMAND_ALL:
            if data[1] == cmd[0]:
                commandId  = cmd[1]
                commandLen = cmd[2]
                break
            else:
                commandIndex += 1

        # check avaliability of command
        if commandIndex == len(moteState.moteState.COMMAND_ALL):
            print "============================================="
            print "Wrong Command Type! Available Command Type: {"
            for cmd in moteState.moteState.COMMAND_ALL:
                print " {0}".format(cmd[0])
            print " }"
            return [outcome,dataToSend]

        if data[1][:2] == '6p':
            try:
                dataToSend = [OpenParser.OpenParser.SERFRAME_PC2MOTE_COMMAND_GD,
                    2, # version
                    imageId,
                    commandId,
                    len(data[2][1:-1].split(','))
                ]
                if data[1] == '6pAdd' or data[1] == '6pDelete':
                    if len(data[2][1:-1].split(','))>0:
                        dataToSend += [int(i) for i in data[2][1:-1].split(',')] # celllist
            except:
                print "============================================="
                print "Wrong 6p parameter format {0}. Split the slot by".format(data[2])
                print "comma. e.g. 6,7. (up to 3)"
                return [outcome,dataToSend]
        else:
            parameter = int(data[2])
            if parameter <= 0xffff:
                parameter  = [(parameter & 0xff),((parameter >> 8) & 0xff)]
                dataToSend = [OpenParser.OpenParser.SERFRAME_PC2MOTE_COMMAND_GD,
                    2, # version
                    imageId,
                    commandId,
                    commandLen, # length 
                    parameter[0],
                    parameter[1]
                ]
            else:
                # more than two bytes parameter, error
                print "============================================="
                print "Paramter Wrong! (Available: 0x0000~0xffff)\n"
                return [outcome,dataToSend]

        # the command is legal if I got here
        outcome = True
        return [outcome,dataToSend]


    def _bytesToMesh_handler(self,sender,signal,data):
        assert type(data)==tuple
        assert len(data)==2
        
        (nextHop,lowpan) = data
        
        self._sendToMoteProbe(
            dataToSend = [OpenParser.OpenParser.SERFRAME_PC2MOTE_DATA]+nextHop+lowpan,
        )
    
    #======================== public ==========================================
    
    def quit(self):
        raise NotImplementedError()
    
    #======================== private =========================================
    
    def _sendToMoteProbe(self,dataToSend):
        try:
             dispatcher.send(
                      sender        = self.name,
                      signal        = 'fromMoteConnector@'+self.serialport,
                      data          = ''.join([chr(c) for c in dataToSend])
                      )
            
        except socket.error:
            log.error(err)
            pass