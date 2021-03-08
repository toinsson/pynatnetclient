# -*- coding: utf-8 -*-
#Copyright © 2021 toinsson
#Copyright © 2018 Naturalpoint
# Licensed under the Apache-2.0 License, see LICENSE for details.

import sys
import socket
import threading

from .protocol import MAX_PACKETSIZE
from .unpack import Decoder

class NatNetClientLocal(Decoder):
    """Inherit the Decoder from unpack module, which exposes the process_message
    method.
    """

    def __init__(self, multicastAddress):
        # NatNet stream version, updated to the actual server version during initialization.
        self.natNetStreamVersion = (3,0,0,0)
        self.natNetStreamVersion2 = '.'.join([str(i) for i in (3,0,0,0)])

        super(NatNetClientLocal, self).__init__(self.natNetStreamVersion, self.natNetStreamVersion2)


        # lopping variable
        self.is_looping = threading.Event()

        # should match the multicast address listed in Motive's streaming settings.
        self.localIPAddress = "127.0.0.1"

        if multicastAddress == None:
            self.multicastAddress = "239.255.42.99"
        else:
            self.multicastAddress = multicastAddress

        self.dataPort = 1511


    def __createDataSocket(self, port):
        """Create a data socket to attach to the NatNet stream."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, socket.inet_aton(self.multicastAddress) + socket.inet_aton(self.localIPAddress))

        try:
            sock.bind((self.localIPAddress, port))
        except socket.error:
            sys.exit(1)

        return sock


    # def __createCommandSocket(self):
    #     """Create a command socket to attach to the NatNet stream."""
    #     sock = socket.socket( socket.AF_INET, socket.SOCK_DGRAM )
    #     sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    #     try:
    #         sock.bind(('', 0))
    #     except socket.error:
    #         sys.exit(1)

    #     sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    #     sock.setblocking(0)
    #     # sock.settimeout(5)
    #     return sock


    def __dataThreadFunction(self, socket):
        while self.is_looping.is_set():
            try:
                msg, address = self.dataSocket.recvfrom(MAX_PACKETSIZE + 4)
                if (len(msg) > 0):
                    with self.ed.lock:
                        self.process_message(msg)
            except socket.error:
                pass

        socket.close()


    def stop(self):
        """Stop the while loop that listen to messages."""
        self.is_looping.clear()


    def run(self):
        self.is_looping.set()

        self.dataSocket = self.__createDataSocket(self.dataPort)
        dataThread = threading.Thread( target = self.__dataThreadFunction, args = (self.dataSocket, ))
        dataThread.start()


        # COMMAND - not implemented

        # self.commandSocket = self.__createCommandSocket()
        # commandThread = Thread( target = self.__dataThreadFunction, args = (self.commandSocket, ))
        # commandThread.start()

        # def sendCommand( self, command, commandStr, socket, address ):
        #     # Compose the message in our known message format
        #     if( command == self.NAT_REQUEST_MODELDEF or command == self.NAT_REQUEST_FRAMEOFDATA ):
        #         packetSize = 0
        #         commandStr = ""
        #     elif( command == self.NAT_REQUEST ):
        #         packetSize = len( commandStr ) + 1
        #     elif( command == self.NAT_PING ):
        #         commandStr = "Ping"
        #         packetSize = len( commandStr ) + 1

        #     data = command.to_bytes( 2, byteorder='little' )
        #     data += packetSize.to_bytes( 2, byteorder='little' )

        #     data += commandStr.encode( 'utf-8' )
        #     data += b'\0'
        #     socket.sendto( data, address )

