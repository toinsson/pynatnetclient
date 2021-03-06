# -*- coding: utf-8 -*-
#Copyright © 2021 toinsson
#Copyright © 2018 Naturalpoint
# Licensed under the Apache-2.0 License, see LICENSE for details.

NATNET_PING    = 0
MAX_PACKETSIZE = 100000
SOCKET_BUFSIZE = 0x100000

# Client/server message ids
NAT_PING                  = 0
NAT_PINGRESPONSE          = 1
NAT_REQUEST               = 2
NAT_RESPONSE              = 3
NAT_REQUEST_MODELDEF      = 4
NAT_MODELDEF              = 5
NAT_REQUEST_FRAMEOFDATA   = 6
NAT_FRAMEOFDATA           = 7
NAT_MESSAGESTRING         = 8
NAT_DISCONNECT            = 9
NAT_UNRECOGNIZED_REQUEST  = 100