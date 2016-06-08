# Copyright (c) 2010-2013, Regents of the University of California.
# All rights reserved.
#
# Released under the BSD 3-Clause license as published at the link below.
# https://openwsn.atlassian.net/wiki/display/OW/License

'''


'''
import threading
import logging
import json
log = logging.getLogger('moteDriver')
log.setLevel(logging.ERROR)
log.addHandler(logging.NullHandler())

class moteDriver():

    def __init__(self, moteStates):

        # log
        log.info("create instance")

        # store params
        self.stateLock         = threading.Lock()
        self.moteStates        = moteStates




    # ========================== public ================================

    def cmdMote(self, moteid, cmd):
        '''
        Sends command to the mote

        :param: moteid: 16-bit ID of mote
                cmd: command to send
        '''

        log.info('Sending command to mote {0}'.format(moteid))
        ms = self.getMoteState(moteid)
        if ms:
            log.debug('Found mote {0} in moteStates'.format(moteid))
            ms.triggerAction(cmd)
        else:
            log.debug('Mote {0} not found in moteStates'.format(moteid))

    def cmdAllMotes(self, cmd):
        '''
        Sends command to all the motes

        :param: cmd: command to send
        '''

        log.info('Sending command to all the motes')
        for ms in self.moteStates:
            ms.triggerAction(cmd)

    def getMoteState(self, moteid):
        '''
        Returns the moteState object for the provided connected mote.

        :param moteid: 16-bit ID of mote
        :rtype:        moteState or None if not found
        '''
        for ms in self.moteStates:
            idManager = ms.getStateElem(ms.ST_IDMANAGER)
            if idManager and idManager.get16bAddr():
                addr = ''.join(['%02x'%b for b in idManager.get16bAddr()])
                if addr == moteid:
                    return ms
        else:
            return None

    def getMoteID(self, ms):
        '''
        Returns the moteID for the provided moteState.

        :param ms: moteState object of a mote
        :rtype:        moteID or None if not found
        '''
        addr = ms.getStateElem(ms.ST_IDMANAGER).get16bAddr()
        if addr:
            return ''.join(['%02x' % b for b in addr])
        else:
            return None

    def getRootList(self):
        '''
        Returns the moteID for the provided moteState.

        :rtype:        a list of DAGroot
        '''
        rootList = []
        for ms in self.moteStates:
            if json.loads(ms.getStateElem(ms.ST_IDMANAGER).toJson('data'))[0]['isDAGroot']:
                rootList.append(self.getMoteID(ms))

        return rootList