# DO NOT EDIT DIRECTLY!
# This file was generated automatically by GenStackDefines.py
# on Thu, 18 Jun 2015 23:18:40
#

components = {
   0: "NULL",
   1: "OPENWSN",
   2: "IDMANAGER",
   3: "OPENQUEUE",
   4: "OPENSERIAL",
   5: "PACKETFUNCTIONS",
   6: "RANDOM",
   7: "RADIO",
   8: "IEEE802154",
   9: "IEEE802154E",
  10: "SIXTOP_TO_IEEE802154E",
  11: "BIER_TO_IEEE802154E",
  12: "IEEE802154E_TO_SIXTOP",
  13: "IEEE802154E_TO_BIER",
  14: "SIXTOP",
  15: "NEIGHBORS",
  16: "SCHEDULE",
  17: "SIXTOP_RES",
  18: "BIER",
  19: "OPENBRIDGE",
  20: "IPHC",
  21: "FORWARDING",
  22: "ICMPv6",
  23: "ICMPv6ECHO",
  24: "ICMPv6ROUTER",
  25: "ICMPv6RPL",
  26: "OPENTCP",
  27: "OPENUDP",
  28: "OPENCOAP",
  29: "C6T",
  30: "CEXAMPLE",
  31: "CINFO",
  32: "CLEDS",
  33: "CSENSORS",
  34: "CSTORM",
  35: "CWELLKNOWN",
  36: "TECHO",
  37: "TOHLONE",
  38: "UECHO",
  39: "UINJECT",
  40: "RRT",
  41: "SECURITY",
}

errorDescriptions = {
   1: "received an echo request",
   2: "received an echo reply",
   3: "getData asks for too few bytes, maxNumBytes={0}, fill level={1}",
   4: "the input buffer has overflown",
   5: "the command is not allowed, command = {0}",
   6: "unknown transport protocol {0} (code location {1})",
   7: "wrong TCP state {0} (code location {1})",
   8: "TCP reset while in state {0} (code location {1})",
   9: "unsupported port number {0} (code location {1})",
  10: "unexpected DAO (code location {0})",
  11: "unsupported ICMPv6 type {0} (code location {1})",
  12: "unsupported 6LoWPAN parameter {1} at location {0}",
  13: "no next hop",
  14: "invalid parameter",
  15: "invalid forward mode",
  16: "large DAGrank {0}, set to {1}",
  17: "packet discarded hop limit reached",
  18: "loop detected due to previous rank {0} lower than current node rank {1}",
  19: "upstream packet set to be downstream, possible loop.",
  20: "neighbors table is full (max number of neighbor is {0})",
  21: "there is no sent packet in queue",
  22: "there is no received packet in queue",
  23: "schedule overflown",
  24: "BIER message forwarded to upper layer. First 16 bits of the bitmap : {0:08b}{1:08b}",
  25: "Attempt to forward a BIER message. BIERMAP sent : {0:08b}{1:08b}",
  26: "Trying to make an elimination on messages which are different.",
  27: "wrong celltype {0} at slotOffset {1}",
  28: "unsupported IEEE802.15.4 parameter {1} at location {0}",
  29: "got desynchronized at slotOffset {0}",
  30: "synchronized at slotOffset {0}",
  31: "large timeCorr.: {0} ticks (code loc. {1})",
  32: "wrong state {0} in end of frame+sync",
  33: "wrong state {0} in startSlot, at slotOffset {1}",
  34: "wrong state {0} in timer fires, at slotOffset {1}",
  35: "wrong state {0} in start of frame, at slotOffset {1}",
  36: "wrong state {0} in end of frame, at slotOffset {1}",
  37: "maxTxDataPrepare overflows while at state {0} in slotOffset {1}",
  38: "maxRxAckPrepapare overflows while at state {0} in slotOffset {1}",
  39: "maxRxDataPrepapre overflows while at state {0} in slotOffset {1}",
  40: "maxTxAckPrepapre overflows while at state {0} in slotOffset {1}",
  41: "wdDataDuration overflows while at state {0} in slotOffset {1}",
  42: "wdRadio overflows while at state {0} in slotOffset {1}",
  43: "wdRadioTx overflows while at state {0} in slotOffset {1}",
  44: "wdAckDuration overflows while at state {0} in slotOffset {1}",
  45: "busy sending",
  46: "sendDone for packet I didn't send",
  47: "no free packet buffer (code location {0})",
  48: "freeing unused memory",
  49: "freeing memory unsupported memory",
  50: "unsupported command {0}",
  51: "unknown message type {0}",
  52: "wrong address type {0} (code location {1})",
  53: "bridge mismatch (code location {0})",
  54: "header too long, length {1} (code location {0})",
  55: "input length problem, length={0}",
  56: "booted",
  57: "invalid serial frame",
  58: "invalid packet frome radio, length {1} (code location {0})",
  59: "busy receiving when stop of serial activity, buffer input length {1} (code location {0})",
  60: "wrong CRC in input Buffer (input length {0})",
  61: "frame received at asn {0} with timeCorrection of {1}",
  62: "security error on frameType {0}, code location {1}",
  63: "sixtop return code {0} at sixtop state {1} ",
  64: "there are {0} cells to request mote",
  65: "the cells reserved to request mote contains slot {0} and slot {1}",
  66: "| requested cell SlotOffset {0} is not available",
  67: "| requested cell SlotOffset {0} is unscheduled",
  68: "| requested operationID {0} is not supported",
  69: "| slotframe Length is set to {0}, maxActiveSlots {1}",

  80: "# active cells for Tx: {0}, Rx: {1}",
  81: "Anormal delay betwwen two BIER packets. Nb of slots : {0}",
  82: "Non-BIER test msg received on track 2. SlotOffset : {0}",
  83: "Non-BIER test msg received on track 3. SlotOffset : {0}",
  84: "TX stats of slot {0} reset. Num TX : 255. Successful : {1}.",
  85: "RX stats of slot {0} reset. Num RX : {1}"
}
