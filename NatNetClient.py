﻿import socket as socket
import struct

import threading
# from threading import Thread

from distutils.version import LooseVersion, StrictVersion

# import ipdb

# Create structs for reading various object types to speed up parsing.
Vector3 = struct.Struct( '<fff' )
Quaternion = struct.Struct( '<ffff' )
FloatValue = struct.Struct( '<f' )
DoubleValue = struct.Struct( '<d' )


class ExposedData(object):
    """docstring for ExposedData"""
    frameNumber = 0





class NatNetClient:
    def __init__( self , client_address, server_address, tracing=False):

        self.client_address = client_address
        self.server_address = server_address

        # TODO: replace with logging
        if tracing:
            self.trace = (lambda *args: print("".join(map(str,args))))
        else:
            self.trace = (lambda *args: None)

        # NatNet Command channel
        self.command_port = 1510

        # NatNet stream version, updated to the actual server version during initialization.
        self.__natNetStreamVersion = (3,0,0,0)
        self.__natNetStreamVersion2 = '.'.join([str(i) for i in (3,0,0,0)])

        # lopping variable
        self.is_looping = threading.Event()

        # store for received data
        self.ed = ExposedData()


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

    # Create a data socket to attach to the NatNet stream
    def __createDataSocket( self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, 0)
        sock.bind((self.client_address, self.command_port))
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, self.SOCKET_BUFSIZE)
        sock.setblocking(0)
        return sock

    # Unpack a rigid body object from a data packet
    def __unpackRigidBody( self, data ):
        offset = 0

        # ID (4 bytes)
        id = int.from_bytes( data[offset:offset+4], byteorder='little' )
        offset += 4
        self.trace( "ID:", id )

        # Position and orientation
        pos = Vector3.unpack( data[offset:offset+12] )
        offset += 12
        self.trace( "\tPosition:", pos[0],",", pos[1],",", pos[2] )
        rot = Quaternion.unpack( data[offset:offset+16] )
        offset += 16
        self.trace( "\tOrientation:", rot[0],",", rot[1],",", rot[2],",", rot[3] )

        # Send information to any listener.
        if self.rigidBodyListener is not None:
            self.rigidBodyListener( id, pos, rot )

        # RB Marker Data ( Before version 3.0.  After Version 3.0 Marker data is in description )
        if( self.__natNetStreamVersion[0] < 3 ) :
            # Marker count (4 bytes)
            markerCount = int.from_bytes( data[offset:offset+4], byteorder='little' )
            offset += 4
            markerCountRange = range( 0, markerCount )
            self.trace( "\tMarker Count:", markerCount )

            # Marker positions
            for i in markerCountRange:
                pos = Vector3.unpack( data[offset:offset+12] )
                offset += 12
                self.trace( "\tMarker", i, ":", pos[0],",", pos[1],",", pos[2] )

            if( self.__natNetStreamVersion[0] >= 2 ):
                # Marker ID's
                for i in markerCountRange:
                    id = int.from_bytes( data[offset:offset+4], byteorder='little' )
                    offset += 4
                    self.trace( "\tMarker ID", i, ":", id )

                # Marker sizes
                for i in markerCountRange:
                    size = FloatValue.unpack( data[offset:offset+4] )
                    offset += 4
                    self.trace( "\tMarker Size", i, ":", size[0] )

        # Skip padding inserted by the server
        offset += 4

        if( self.__natNetStreamVersion[0] >= 2 ):
            markerError, = FloatValue.unpack( data[offset:offset+4] )
            offset += 4
            self.trace( "\tMarker Error:", markerError )

        # Version 2.6 and later
        if( ( ( self.__natNetStreamVersion[0] == 2 ) and ( self.__natNetStreamVersion[1] >= 6 ) ) or self.__natNetStreamVersion[0] > 2 or self.__natNetStreamVersion[0] == 0 ):
            param, = struct.unpack( 'h', data[offset:offset+2] )
            trackingValid = ( param & 0x01 ) != 0
            offset += 2
            self.trace( "\tTracking Valid:", 'True' if trackingValid else 'False' )

        return offset

    # Unpack a skeleton object from a data packet
    def __unpackSkeleton( self, data ):
        offset = 0

        id = int.from_bytes( data[offset:offset+4], byteorder='little' )
        offset += 4
        self.trace( "ID:", id )

        rigidBodyCount = int.from_bytes( data[offset:offset+4], byteorder='little' )
        offset += 4
        self.trace( "Rigid Body Count:", rigidBodyCount )
        for j in range( 0, rigidBodyCount ):
            offset += self.__unpackRigidBody( data[offset:] )

        return offset

    # Unpack data from a motion capture frame message
    def __unpackMocapData( self, data ):
        self.trace( "Begin MoCap Frame\n-----------------\n" )

        data = memoryview( data )
        offset = 0

        # Frame number (4 bytes)
        self.ed.frameNumber = int.from_bytes( data[offset:offset+4], byteorder='little' )
        offset += 4
        # self.trace( "Frame #:" , self.ed.frameNumber )

        # Marker set count (4 bytes)
        markerSetCount = int.from_bytes( data[offset:offset+4], byteorder='little' )
        offset += 4
        # self.trace( "Marker Set Count:", markerSetCount )

        for i in range( 0, markerSetCount ):
            # Model name
            modelName, separator, remainder = bytes(data[offset:]).partition( b'\0' )
            offset += len( modelName ) + 1
            # self.trace( "Model Name:", modelName.decode( 'utf-8' ) )

            # Marker count (4 bytes)
            markerCount = int.from_bytes( data[offset:offset+4], byteorder='little' )
            offset += 4
            self.trace( "Marker Count:", markerCount )

            for j in range( 0, markerCount ):
                pos = Vector3.unpack( data[offset:offset+12] )
                offset += 12
                #self.trace( "\tMarker", j, ":", pos[0],",", pos[1],",", pos[2] )

        # Unlabeled markers count (4 bytes)
        unlabeledMarkersCount = int.from_bytes( data[offset:offset+4], byteorder='little' )
        offset += 4
        self.trace( "Unlabeled Markers Count:", unlabeledMarkersCount )

        for i in range( 0, unlabeledMarkersCount ):
            pos = Vector3.unpack( data[offset:offset+12] )
            offset += 12
            self.trace( "\tMarker", i, ":", pos[0],",", pos[1],",", pos[2] )

        # Rigid body count (4 bytes)
        rigidBodyCount = int.from_bytes( data[offset:offset+4], byteorder='little' )
        offset += 4
        self.trace( "Rigid Body Count:", rigidBodyCount )

        for i in range( 0, rigidBodyCount ):
            offset += self.__unpackRigidBody( data[offset:] )

        # Version 2.1 and later
        skeletonCount = 0
        if( ( self.__natNetStreamVersion[0] == 2 and self.__natNetStreamVersion[1] > 0 ) or self.__natNetStreamVersion[0] > 2 ):
            skeletonCount = int.from_bytes( data[offset:offset+4], byteorder='little' )
            offset += 4
            self.trace( "Skeleton Count:", skeletonCount )
            for i in range( 0, skeletonCount ):
                offset += self.__unpackSkeleton( data[offset:] )

        # Labeled markers (Version 2.3 and later)
        self.ed.labeledMarkerCount = 0
        if self.__natNetStreamVersion2 > LooseVersion("2.3"):
        # if( ( self.__natNetStreamVersion[0] == 2 and self.__natNetStreamVersion[1] > 3 ) or self.__natNetStreamVersion[0] > 2 ):
            labeledMarkerCount = int.from_bytes( data[offset:offset+4], byteorder='little' )
            offset += 4
            self.trace( "Labeled Marker Count:", labeledMarkerCount )
            for i in range( 0, labeledMarkerCount ):
                id = int.from_bytes( data[offset:offset+4], byteorder='little' )
                offset += 4
                pos = Vector3.unpack( data[offset:offset+12] )
                offset += 12
                size = FloatValue.unpack( data[offset:offset+4] )
                offset += 4

                self.trace( "Pos:", pos )
                self.trace( "Size:", size )

                # Version 2.6 and later
                if( ( self.__natNetStreamVersion[0] == 2 and self.__natNetStreamVersion[1] >= 6 ) or self.__natNetStreamVersion[0] > 2 or major == 0 ):
                    param, = struct.unpack( 'h', data[offset:offset+2] )
                    offset += 2
                    occluded = ( param & 0x01 ) != 0
                    pointCloudSolved = ( param & 0x02 ) != 0
                    modelSolved = ( param & 0x04 ) != 0

                # Version 3.0 and later
                if( ( self.__natNetStreamVersion[0] >= 3 ) or  major == 0 ):
                    residual, = FloatValue.unpack( data[offset:offset+4] )
                    offset += 4
                    self.trace( "Residual:", residual )

        # Force Plate data (version 2.9 and later)
        if( ( self.__natNetStreamVersion[0] == 2 and self.__natNetStreamVersion[1] >= 9 ) or self.__natNetStreamVersion[0] > 2 ):
            forcePlateCount = int.from_bytes( data[offset:offset+4], byteorder='little' )
            offset += 4
            self.trace( "Force Plate Count:", forcePlateCount )
            for i in range( 0, forcePlateCount ):
                # ID
                forcePlateID = int.from_bytes( data[offset:offset+4], byteorder='little' )
                offset += 4
                self.trace( "Force Plate", i, ":", forcePlateID )

                # Channel Count
                forcePlateChannelCount = int.from_bytes( data[offset:offset+4], byteorder='little' )
                offset += 4

                # Channel Data
                for j in range( 0, forcePlateChannelCount ):
                    self.trace( "\tChannel", j, ":", forcePlateID )
                    forcePlateChannelFrameCount = int.from_bytes( data[offset:offset+4], byteorder='little' )
                    offset += 4
                    for k in range( 0, forcePlateChannelFrameCount ):
                        forcePlateChannelVal = int.from_bytes( data[offset:offset+4], byteorder='little' )
                        offset += 4
                        self.trace( "\t\t", forcePlateChannelVal )

        # Device data (version 2.11 and later)
        if( ( self.__natNetStreamVersion[0] == 2 and self.__natNetStreamVersion[1] >= 11 ) or self.__natNetStreamVersion[0] > 2 ):
            deviceCount = int.from_bytes( data[offset:offset+4], byteorder='little' )
            offset += 4
            self.trace( "Device Count:", deviceCount )
            for i in range( 0, deviceCount ):
                # ID
                deviceID = int.from_bytes( data[offset:offset+4], byteorder='little' )
                offset += 4
                self.trace( "Device", i, ":", deviceID )

                # Channel Count
                deviceChannelCount = int.from_bytes( data[offset:offset+4], byteorder='little' )
                offset += 4

                # Channel Data
                for j in range( 0, deviceChannelCount ):
                    self.trace( "\tChannel", j, ":", deviceID )
                    deviceChannelFrameCount = int.from_bytes( data[offset:offset+4], byteorder='little' )
                    offset += 4
                    for k in range( 0, deviceChannelFrameCount ):
                        deviceChannelVal = int.from_bytes( data[offset:offset+4], byteorder='little' )
                        offset += 4
                        self.trace( "\t\t", deviceChannelVal )

        # Timecode
        timecode = int.from_bytes( data[offset:offset+4], byteorder='little' )
        offset += 4
        timecodeSub = int.from_bytes( data[offset:offset+4], byteorder='little' )
        offset += 4

        # Timestamp (increased to double precision in 2.7 and later)
        if( ( self.__natNetStreamVersion[0] == 2 and self.__natNetStreamVersion[1] >= 7 ) or self.__natNetStreamVersion[0] > 2 ):
            timestamp, = DoubleValue.unpack( data[offset:offset+8] )
            offset += 8
        else:
            timestamp, = FloatValue.unpack( data[offset:offset+4] )
            offset += 4

        # Hires Timestamp (Version 3.0 and later)
        if( ( self.__natNetStreamVersion[0] >= 3 ) or  major == 0 ):
            stampCameraExposure = int.from_bytes( data[offset:offset+8], byteorder='little' )
            offset += 8
            stampDataReceived = int.from_bytes( data[offset:offset+8], byteorder='little' )
            offset += 8
            stampTransmit = int.from_bytes( data[offset:offset+8], byteorder='little' )
            offset += 8

        # Frame parameters
        param, = struct.unpack( 'h', data[offset:offset+2] )
        isRecording = ( param & 0x01 ) != 0
        trackedModelsChanged = ( param & 0x02 ) != 0
        offset += 2

    # Unpack a marker set description packet
    def __unpackMarkerSetDescription( self, data ):
        offset = 0

        name, separator, remainder = bytes(data[offset:]).partition( b'\0' )
        offset += len( name ) + 1
        self.trace( "Markerset Name:", name.decode( 'utf-8' ) )

        markerCount = int.from_bytes( data[offset:offset+4], byteorder='little' )
        offset += 4

        for i in range( 0, markerCount ):
            name, separator, remainder = bytes(data[offset:]).partition( b'\0' )
            offset += len( name ) + 1
            self.trace( "\tMarker Name:", name.decode( 'utf-8' ) )

        return offset

    # Unpack a rigid body description packet
    def __unpackRigidBodyDescription( self, data ):
        offset = 0

        # Version 2.0 or higher
        if( self.__natNetStreamVersion[0] >= 2 ):
            name, separator, remainder = bytes(data[offset:]).partition( b'\0' )
            offset += len( name ) + 1
            self.trace( "\tMarker Name:", name.decode( 'utf-8' ) )

        id = int.from_bytes( data[offset:offset+4], byteorder='little' )
        offset += 4

        parentID = int.from_bytes( data[offset:offset+4], byteorder='little' )
        offset += 4

        timestamp = Vector3.unpack( data[offset:offset+12] )
        offset += 12

        return offset

    # Unpack a skeleton description packet
    def __unpackSkeletonDescription( self, data ):
        offset = 0

        name, separator, remainder = bytes(data[offset:]).partition( b'\0' )
        offset += len( name ) + 1
        self.trace( "\tMarker Name:", name.decode( 'utf-8' ) )

        id = int.from_bytes( data[offset:offset+4], byteorder='little' )
        offset += 4

        rigidBodyCount = int.from_bytes( data[offset:offset+4], byteorder='little' )
        offset += 4

        for i in range( 0, rigidBodyCount ):
            offset += self.__unpackRigidBodyDescription( data[offset:] )

        return offset

    # Unpack a data description packet
    def __unpackDataDescriptions( self, data ):
        offset = 0
        datasetCount = int.from_bytes( data[offset:offset+4], byteorder='little' )
        offset += 4

        for i in range( 0, datasetCount ):
            type = int.from_bytes( data[offset:offset+4], byteorder='little' )
            offset += 4
            if( type == 0 ):
                offset += self.__unpackMarkerSetDescription( data[offset:] )
            elif( type == 1 ):
                offset += self.__unpackRigidBodyDescription( data[offset:] )
            elif( type == 2 ):
                offset += self.__unpackSkeletonDescription( data[offset:] )

    def __dataThreadFunction( self):
        while self.is_looping.is_set():  # replace with a flag
            try:
                msg, address = self.dataSocket.recvfrom(self.MAX_PACKETSIZE + 4)
                if( len( msg ) > 0 ):
                    self.__processMessage( msg )

            except socket.error:
                pass

        print('stop the loop in thread')


    def __processMessage( self, data ):
        self.trace( "Begin Packet\n------------\n" )

        messageID = int.from_bytes( data[0:2], byteorder='little' )
        self.trace( "Message ID:", messageID )

        packetSize = int.from_bytes( data[2:4], byteorder='little' )
        self.trace( "Packet Size:", packetSize )

        offset = 4
        if( messageID == self.NAT_FRAMEOFDATA ):
            self.__unpackMocapData( data[offset:] )
        elif( messageID == self.NAT_MODELDEF ):
            self.__unpackDataDescriptions( data[offset:] )
        elif( messageID == self.NAT_PINGRESPONSE ):
            offset += 256   # Skip the sending app's Name field
            offset += 4     # Skip the sending app's Version info
            self.__natNetStreamVersion = struct.unpack( 'BBBB', data[offset:offset+4] )
            self.__natNetStreamVersion2 = '.'.join([str(i) for i in self.__natNetStreamVersion])
            offset += 4
        elif( messageID == self.NAT_RESPONSE ):
            if( packetSize == 4 ):
                commandResponse = int.from_bytes( data[offset:offset+4], byteorder='little' )
                offset += 4
            else:
                message, separator, remainder = bytes(data[offset:]).partition( b'\0' )
                offset += len( message ) + 1
                self.trace( "Command response:", message.decode( 'utf-8' ) )
        elif( messageID == self.NAT_UNRECOGNIZED_REQUEST ):
            self.trace( "Received 'Unrecognized request' from server" )
        elif( messageID == self.NAT_MESSAGESTRING ):
            message, separator, remainder = bytes(data[offset:]).partition( b'\0' )
            offset += len( message ) + 1
            self.trace( "Received message from server:", message.decode( 'utf-8' ) )
        else:
            self.trace( "ERROR: Unrecognized packet type" )

        self.trace( "End Packet\n----------\n" )


    def stop(self):
        """Stop the while loop that listen to messages."""
        self.is_looping.clear()


    def run( self ):
        # Create the data socket
        self.dataSocket = self.__createDataSocket()
        if( self.dataSocket is None ):
            print( "Could not open data channel" )
            exit

        msg = struct.pack("I", self.NATNET_PING)
        _ = self.dataSocket.sendto(msg, (self.server_address, self.command_port))

        # set the loop flag event
        self.is_looping.set()

        # Create a separate thread for receiving data packets
        self.dataThread = threading.Thread( target = self.__dataThreadFunction )
        self.dataThread.start()