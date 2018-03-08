import socket as socket
import struct as struct

NATNET_PING = 0

MAX_PACKETSIZE = 100000
SOCKET_BUFSIZE = 0x100000

client_address = '192.168.0.11'
server_address = '192.168.0.10'
command_port = 1510

def ConnectCommandSocket():
    "Create a command socket."
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, 0)
    sock.bind((client_address, command_port))
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, SOCKET_BUFSIZE)
    sock.setblocking(0)
    return sock

commandSocket = ConnectCommandSocket()

from NatNetClient import NatNetClient


# This is a callback function that gets connected to the NatNet client and called once per mocap frame.
def receiveNewFrame( frameNumber, markerSetCount, unlabeledMarkersCount, rigidBodyCount, skeletonCount,
                    labeledMarkerCount, timecode, timecodeSub, timestamp, isRecording, trackedModelsChanged ):
    print( "Received frame", frameNumber )

# This is a callback function that gets connected to the NatNet client. It is called once per rigid body per frame
def receiveRigidBodyFrame( id, position, rotation ):
    print( "Received frame for rigid body", id )

# This will create a new NatNet client
streamingClient = NatNetClient()

# Configure the streaming client to call our rigid body handler on the emulator to send data out.
streamingClient.newFrameListener = receiveNewFrame
streamingClient.rigidBodyListener = receiveRigidBodyFrame



## Send a ping command so that Tracker will begin streaming data
msg = struct.pack("I", NATNET_PING)
result = commandSocket.sendto(msg, (server_address, command_port))

while True:
    try:
        msg, address = commandSocket.recvfrom(MAX_PACKETSIZE + 4)

        data = msg
        if( len( data ) > 0 ):
            streamingClient._NatNetClient__processMessage( data )

    except socket.error:
        pass
    # else:
    #     print(msg, "\n")



