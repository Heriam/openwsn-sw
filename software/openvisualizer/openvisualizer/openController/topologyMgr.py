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
log = logging.getLogger('topologyMgr')
log.setLevel(logging.ERROR)
log.addHandler(logging.NullHandler())

class topologyMgr(eventBusClient.eventBusClient):

    def __init__(self):

        # log
        log.info("create instance")

        # store params
        self.stateLock         = threading.Lock()

        eventBusClient.eventBusClient.__init__(
            self,
            name=self.name,
            registrations=[
                # {
                #     'sender': self.WILDCARD,
                #     'signal': 'infoDagRoot',
                #     'callback': self._infoDagRoot_handler,
                # },
                # {
                #     'sender': self.WILDCARD,
                #     'signal': 'cmdToMote',
                #     'callback': self._cmdToMote_handler,
                # }
            ]
        )
