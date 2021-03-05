#Copyright © 2021 toinsson
#Copyright © 2018 Naturalpoint
#
#Licensed under the Apache License, Version 2.0 (the "License");
#you may not use this file except in compliance with the License.
#You may obtain a copy of the License at
#
#http://www.apache.org/licenses/LICENSE-2.0
#
#Unless required by applicable law or agreed to in writing, software
#distributed under the License is distributed on an "AS IS" BASIS,
#WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#See the License for the specific language governing permissions and
#limitations under the License.

# OptiTrack NatNet direct depacketization library for Python 3.x
# Modified by toinsson for packaging and debugging purposes, as well as
# supporting remote servers.


__version__ = '1.0'

import logging
import threading

from .local import NatNetClientLocal
from .remote import NatNetClientRemote


def NatNetClient(multicastAddress=None, client_address=None, server_address=None):
    """Factory function that returns a local or remote version of the NatNetClient.
    If local is True, the optitrack and the client are on the same machine.
    Otherwise, the IP for the optitrack server and the client must be provided.
    """

    if (client_address==None) and (server_address==None):
        return NatNetClientLocal(multicastAddress)
    else:
        return NatNetClientRemote(client_address, server_address)
