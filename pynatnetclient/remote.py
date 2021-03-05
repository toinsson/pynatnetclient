import sys
import socket
import struct
import threading

from .protocol import MAX_PACKETSIZE, NATNET_PING
from .unpack import Decoder

class NatNetClientRemote(Decoder):
    """Inherit the Decoder from unpack module, which exposes the process_message
    method.
    """

    def __init__(self, client_address, server_address):
        super(NatNetClientRemote, self).__init__()

        # NatNet stream version, updated to the actual server version during initialization.
        self.__natNetStreamVersion = (3,0,0,0)
        self.__natNetStreamVersion2 = '.'.join([str(i) for i in (3,0,0,0)])

        # lopping variable
        self.is_looping = threading.Event()

        # logging
        self.logger = logging.getLogger(__name__)
        self.logger.addHandler(logging.NullHandler())

        # client is reading the data from the server running the optitrack
        self.client_address = client_address
        self.server_address = server_address

        # NatNet Command channel
        self.command_port = 1510


    def __createDataSocket(self):
        """Create a data socket to attach to the NatNet stream."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, 0)

        try:
            sock.bind((self.client_address, self.command_port))
        except socket.error:
            sys.exit(1)

        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, self.SOCKET_BUFSIZE)
        sock.setblocking(0)
        return sock


    def __dataThreadFunction(self):
        while self.is_looping.is_set():
            try:
                msg, address = self.dataSocket.recvfrom(MAX_PACKETSIZE + 4)
                if( len( msg ) > 0 ):
                    with self.ed.lock:
                        self.process_message( msg )
            except socket.error:   # no message
                pass

        self.dataSocket.close()


    def stop(self):
        """Stop the while loop that listen to messages."""
        self.is_looping.clear()


    def run(self):

        # Create the data socket
        self.dataSocket = self.__createDataSocket()
        msg = struct.pack("I", NATNET_PING)
        _ = self.dataSocket.sendto(msg, (self.server_address, self.command_port))

        # set the loop flag event
        self.is_looping.set()

        # Create a separate thread for receiving data packets
        self.dataThread = threading.Thread( target = self.__dataThreadFunction )
        self.dataThread.start()

        # set up a ping timer to keep the connection up
        def ping():
            if self.is_looping.is_set():
                msg = struct.pack("I", NATNET_PING)
                _ = self.dataSocket.sendto(msg, (self.server_address, self.command_port))
                threading.Timer(0.1, ping).start()
        ping()

