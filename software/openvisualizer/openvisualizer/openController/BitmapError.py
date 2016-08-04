# Copyright (c) 2010-2013, Regents of the University of California.
# All rights reserved.
#
# Released under the BSD 3-Clause license as published at the link below.
# https://openwsn.atlassian.net/wiki/display/OW/License

class BitmapError(Exception):

    GENERIC          = 1
    TOO_SHORT        = 2
    WRONG_LENGTH     = 3
    UNKNOWN_DST      = 4
    NO_BITMAP        = 5
    SERIALIZE        = 6
    COMPUTATION      = 7

    descriptions = {
        GENERIC:        'generic bitmap error',
        TOO_SHORT:      'bitmap too short',
        WRONG_LENGTH:   'bitmap of the wrong length',
        UNKNOWN_DST:    'unknown destination',
        NO_BITMAP:      'bit/bitmap not found',
        SERIALIZE:      'serialization error',
        COMPUTATION:    'error in bitmap computation'
    }

    def __init__(self,errorCode,details=None):
        self.errorCode  = errorCode
        self.details    = details

    def __str__(self):
        try:
            output = self.descriptions[self.errorCode]
            if self.details:
                output += ': ' + str(self.details)
            return output
        except KeyError:
            return "Unknown error: #" + str(self.errorCode)