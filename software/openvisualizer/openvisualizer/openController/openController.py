# Copyright (c) 2010-2013, Regents of the University of California.
# All rights reserved.
#
# Released under the BSD 3-Clause license as published at the link below.
# https://openwsn.atlassian.net/wiki/display/OW/License

'''


'''
import threading
import scheduleMgr
import logging
log = logging.getLogger('openController')
log.setLevel(logging.ERROR)
log.addHandler(logging.NullHandler())

class topologyMgr():

    def __init__(self):

        # log
        log.info("create instance")

        # store params
        self.stateLock         = threading.Lock()
        self.scheduleMgr       = scheduleMgr.scheduleMgr()