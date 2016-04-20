# Copyright (c) 2010-2013, Regents of the University of California.
# All rights reserved.
#
# Released under the BSD 3-Clause license as published at the link below.
# https://openwsn.atlassian.net/wiki/display/OW/License

'''
Contains
'''

import logging
log = logging.getLogger('openController')
log.setLevel(logging.ERROR)
log.addHandler(logging.NullHandler())
import threading


from openvisualizer.eventBus      import eventBusClient

class openController():

    def __init__(self):
        # log
        log.info("create instance")

        # store params
        self.stateLock = threading.Lock()
        self.motelist       = []
        self.schedule       = {}


