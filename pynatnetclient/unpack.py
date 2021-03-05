import struct
import logging
import threading
from distutils.version import LooseVersion


from .protocol import *

class ExposedData(object):
    """docstring for ExposedData"""
    def __init__(self):

        self.lock = threading.Lock()

        self.frameNumber = 0
        self.labeledMarkerCount = 0
        self.labeledMarker = []
        self.timestamp = 0
        self.stampCameraExposure = 0
        self.stampDataReceived = 0
        self.stampTransmit = 0

    def __copy__(self):
        ed = ExposedData()
        ed.__dict__.update(self.__dict__)
        ed.lock = None
        return ed


# Create structs for reading various object types to speed up parsing.
Vector3 = struct.Struct( '<fff' )
Quaternion = struct.Struct( '<ffff' )
FloatValue = struct.Struct( '<f' )
DoubleValue = struct.Struct( '<d' )

# logging
logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class Decoder(object):
    """docstring for Unpacker"""
    def __init__(self, natNetStreamVersion, natNetStreamVersion2):

        self.natNetStreamVersion = natNetStreamVersion
        self.natNetStreamVersion2 = natNetStreamVersion2

        # store for received data
        self.ed = ExposedData()


    def process_message( self, data ):
        logger.debug( "Begin Packet\n------------\n" )

        messageID = int.from_bytes( data[0:2], byteorder='little' )
        logger.debug( "Message ID: {}".format(messageID))

        packetSize = int.from_bytes( data[2:4], byteorder='little' )
        logger.debug( "Packet Size: {}".format(packetSize))

        offset = 4
        if( messageID == NAT_FRAMEOFDATA ):
            self.__unpackMocapData( data[offset:] )
        elif( messageID == NAT_MODELDEF ):
            self.__unpackDataDescriptions( data[offset:] )
        elif( messageID == NAT_PINGRESPONSE ):
            offset += 256   # Skip the sending app's Name field
            offset += 4     # Skip the sending app's Version info
            self.natNetStreamVersion = struct.unpack( 'BBBB', data[offset:offset+4] )
            offset += 4
        elif( messageID == NAT_RESPONSE ):
            if( packetSize == 4 ):
                commandResponse = int.from_bytes( data[offset:offset+4], byteorder='little' )
                offset += 4
            else:
                message, separator, remainder = bytes(data[offset:]).partition( b'\0' )
                offset += len( message ) + 1
                logger.debug( "Command response:", message.decode( 'utf-8' ) )
        elif( messageID == NAT_UNRECOGNIZED_REQUEST ):
            logger.debug( "Received 'Unrecognized request' from server" )
        elif( messageID == NAT_MESSAGESTRING ):
            message, separator, remainder = bytes(data[offset:]).partition( b'\0' )
            offset += len( message ) + 1
            logger.debug( "Received message from server:", message.decode( 'utf-8' ) )
        else:
            logger.debug( "ERROR: Unrecognized packet type" )

        logger.debug( "End Packet\n----------\n" )


    # Unpack a rigid body object from a data packet
    def __unpackRigidBody( self, data ):
        offset = 0

        # ID (4 bytes)
        id = int.from_bytes( data[offset:offset+4], byteorder='little' )
        offset += 4
        logger.debug( "ID:", id )

        # Position and orientation
        pos = Vector3.unpack( data[offset:offset+12] )
        offset += 12
        logger.debug( "\tPosition:", pos[0],",", pos[1],",", pos[2] )
        rot = Quaternion.unpack( data[offset:offset+16] )
        offset += 16
        logger.debug( "\tOrientation:", rot[0],",", rot[1],",", rot[2],",", rot[3] )

        # Send information to any listener.
        if self.rigidBodyListener is not None:
            self.rigidBodyListener( id, pos, rot )

        # RB Marker Data ( Before version 3.0.  After Version 3.0 Marker data is in description )
        if( self.natNetStreamVersion[0] < 3 ) :
            # Marker count (4 bytes)
            markerCount = int.from_bytes( data[offset:offset+4], byteorder='little' )
            offset += 4
            markerCountRange = range( 0, markerCount )
            logger.debug( "\tMarker Count:", markerCount )

            # Marker positions
            for i in markerCountRange:
                pos = Vector3.unpack( data[offset:offset+12] )
                offset += 12
                logger.debug( "\tMarker", i, ":", pos[0],",", pos[1],",", pos[2] )

            if( self.natNetStreamVersion[0] >= 2 ):
                # Marker ID's
                for i in markerCountRange:
                    id = int.from_bytes( data[offset:offset+4], byteorder='little' )
                    offset += 4
                    logger.debug( "\tMarker ID", i, ":", id )

                # Marker sizes
                for i in markerCountRange:
                    size = FloatValue.unpack( data[offset:offset+4] )
                    offset += 4
                    logger.debug( "\tMarker Size", i, ":", size[0] )

        # Skip padding inserted by the server
        offset += 4

        if( self.natNetStreamVersion[0] >= 2 ):
            markerError, = FloatValue.unpack( data[offset:offset+4] )
            offset += 4
            logger.debug( "\tMarker Error:", markerError )

        # Version 2.6 and later
        if( ( ( self.natNetStreamVersion[0] == 2 ) and ( self.natNetStreamVersion[1] >= 6 ) ) or self.natNetStreamVersion[0] > 2 or self.natNetStreamVersion[0] == 0 ):
            param, = struct.unpack( 'h', data[offset:offset+2] )
            trackingValid = ( param & 0x01 ) != 0
            offset += 2
            logger.debug( "\tTracking Valid:", 'True' if trackingValid else 'False' )

        return offset

    # Unpack a skeleton object from a data packet
    def __unpackSkeleton( self, data ):
        offset = 0

        id = int.from_bytes( data[offset:offset+4], byteorder='little' )
        offset += 4
        logger.debug( "ID:", id )

        rigidBodyCount = int.from_bytes( data[offset:offset+4], byteorder='little' )
        offset += 4
        logger.debug( "Rigid Body Count:", rigidBodyCount )
        for j in range( 0, rigidBodyCount ):
            offset += self.__unpackRigidBody( data[offset:] )

        return offset

    # Unpack data from a motion capture frame message
    def __unpackMocapData( self, data ):
        logger.debug( "Begin MoCap Frame\n-----------------\n" )

        # clear data
        self.ed = ExposedData()

        data = memoryview( data )
        offset = 0

        # Frame number (4 bytes)
        self.ed.frameNumber = int.from_bytes( data[offset:offset+4], byteorder='little' )
        offset += 4
        logger.debug("Frame #: {}".format(self.ed.frameNumber))

        # Marker set count (4 bytes)
        markerSetCount = int.from_bytes( data[offset:offset+4], byteorder='little' )
        offset += 4
        # logger.debug( "Marker Set Count:", markerSetCount )

        for i in range( 0, markerSetCount ):
            # Model name
            modelName, separator, remainder = bytes(data[offset:]).partition( b'\0' )
            offset += len( modelName ) + 1
            # logger.debug( "Model Name:", modelName.decode( 'utf-8' ) )

            # Marker count (4 bytes)
            markerCount = int.from_bytes( data[offset:offset+4], byteorder='little' )
            offset += 4
            logger.debug("Marker Count: {}".format(markerCount))

            for j in range( 0, markerCount ):
                pos = Vector3.unpack( data[offset:offset+12] )
                offset += 12
                #logger.debug( "\tMarker", j, ":", pos[0],",", pos[1],",", pos[2] )

        # Unlabeled markers count (4 bytes)
        unlabeledMarkersCount = int.from_bytes( data[offset:offset+4], byteorder='little' )
        offset += 4
        logger.debug("Unlabeled Markers Count: {}".format(unlabeledMarkersCount))

        for i in range( 0, unlabeledMarkersCount ):
            pos = Vector3.unpack( data[offset:offset+12] )
            offset += 12
            logger.debug("\tMarker {}: {},{},{}".format(i, pos[0], pos[1], pos[2]))

        # Rigid body count (4 bytes)
        rigidBodyCount = int.from_bytes( data[offset:offset+4], byteorder='little' )
        offset += 4
        logger.debug("Rigid Body Count: {}".format(rigidBodyCount))

        for i in range( 0, rigidBodyCount ):
            offset += self.__unpackRigidBody( data[offset:] )

        # Version 2.1 and later
        skeletonCount = 0
        if self.natNetStreamVersion2 > LooseVersion("2.1"):
            skeletonCount = int.from_bytes( data[offset:offset+4], byteorder='little' )
            offset += 4
            logger.debug("Skeleton Count: {}".format(skeletonCount))
            for i in range( 0, skeletonCount ):
                offset += self.__unpackSkeleton( data[offset:] )

        # Labeled markers (Version 2.3 and later)
        if self.natNetStreamVersion2 > LooseVersion("2.3"):
            self.ed.labeledMarkerCount = int.from_bytes( data[offset:offset+4], byteorder='little' )
            offset += 4
            logger.debug("Labeled Marker Count: {}".format(self.ed.labeledMarkerCount))
            for i in range( 0, self.ed.labeledMarkerCount ):
                ed_dict = {}
                ed_dict['id'] = int.from_bytes( data[offset:offset+4], byteorder='little' )
                offset += 4
                ed_dict['pos'] = Vector3.unpack( data[offset:offset+12] )
                offset += 12
                ed_dict['size'] = FloatValue.unpack( data[offset:offset+4] )
                offset += 4

                logger.debug( "Pos: {}".format(ed_dict['pos']))
                logger.debug( "Size: {}".format(ed_dict['size']))

                # Version 2.6 and later
                if self.natNetStreamVersion2 >= LooseVersion("2.6"):
                    param, = struct.unpack( 'h', data[offset:offset+2] )
                    offset += 2
                    ed_dict['occluded'] = ( param & 0x01 ) != 0
                    ed_dict['pointCloudSolved'] = ( param & 0x02 ) != 0
                    ed_dict['modelSolved'] = ( param & 0x04 ) != 0

                # Version 3.0 and later
                if self.natNetStreamVersion2 >= LooseVersion("3.0"):
                    ed_dict['residual'], = FloatValue.unpack( data[offset:offset+4] )  # take [0]
                    offset += 4
                    logger.debug("Residual: {}".format(ed_dict['residual']))

                self.ed.labeledMarker.append(ed_dict)


        # Force Plate data (version 2.9 and later)
        if( ( self.natNetStreamVersion[0] == 2 and self.natNetStreamVersion[1] >= 9 ) or self.natNetStreamVersion[0] > 2 ):
            forcePlateCount = int.from_bytes( data[offset:offset+4], byteorder='little' )
            offset += 4
            logger.debug("Force Plate Count: {}".format(forcePlateCount))
            for i in range( 0, forcePlateCount ):
                # ID
                forcePlateID = int.from_bytes( data[offset:offset+4], byteorder='little' )
                offset += 4
                logger.debug("Force Plate {}: {}".format(i, forcePlateID))

                # Channel Count
                forcePlateChannelCount = int.from_bytes( data[offset:offset+4], byteorder='little' )
                offset += 4

                # Channel Data
                for j in range( 0, forcePlateChannelCount ):
                    logger.debug( "\tChannel {}: {}".format(j, forcePlateID))
                    forcePlateChannelFrameCount = int.from_bytes( data[offset:offset+4], byteorder='little' )
                    offset += 4
                    for k in range( 0, forcePlateChannelFrameCount ):
                        forcePlateChannelVal = int.from_bytes( data[offset:offset+4], byteorder='little' )
                        offset += 4
                        logger.debug( "\t\t{}".format(forcePlateChannelVal))

        # Device data (version 2.11 and later)
        if( ( self.natNetStreamVersion[0] == 2 and self.natNetStreamVersion[1] >= 11 ) or self.natNetStreamVersion[0] > 2 ):
            deviceCount = int.from_bytes( data[offset:offset+4], byteorder='little' )
            offset += 4
            logger.debug("Device Count: {}".format(deviceCount))
            for i in range( 0, deviceCount ):
                # ID
                deviceID = int.from_bytes( data[offset:offset+4], byteorder='little' )
                offset += 4
                logger.debug("Device {}: {}".format(i, deviceID))

                # Channel Count
                deviceChannelCount = int.from_bytes( data[offset:offset+4], byteorder='little' )
                offset += 4

                # Channel Data
                for j in range( 0, deviceChannelCount ):
                    logger.debug( "\tChannel {}: {}".format(j, deviceID))
                    deviceChannelFrameCount = int.from_bytes( data[offset:offset+4], byteorder='little' )
                    offset += 4
                    for k in range( 0, deviceChannelFrameCount ):
                        deviceChannelVal = int.from_bytes( data[offset:offset+4], byteorder='little' )
                        offset += 4
                        logger.debug( "\t\t{}".format(deviceChannelVal))

        # Timecode
        timecode = int.from_bytes( data[offset:offset+4], byteorder='little' )
        offset += 4
        timecodeSub = int.from_bytes( data[offset:offset+4], byteorder='little' )
        offset += 4

        # Timestamp (increased to double precision in 2.7 and later)
        if self.natNetStreamVersion2 > LooseVersion("2.7"):
            self.ed.timestamp, = DoubleValue.unpack( data[offset:offset+8] )
            offset += 8
        else:
            self.ed.timestamp, = FloatValue.unpack( data[offset:offset+4] )
            offset += 4

        # Hires Timestamp (Version 3.0 and later)
        if self.natNetStreamVersion2 > LooseVersion("3.0"):
            self.ed.stampCameraExposure = int.from_bytes( data[offset:offset+8], byteorder='little' )
            offset += 8
            self.ed.stampDataReceived = int.from_bytes( data[offset:offset+8], byteorder='little' )
            offset += 8
            self.ed.stampTransmit = int.from_bytes( data[offset:offset+8], byteorder='little' )
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
        logger.debug( "Markerset Name: {}".format(name.decode('utf-8')))

        markerCount = int.from_bytes( data[offset:offset+4], byteorder='little' )
        offset += 4

        for i in range( 0, markerCount ):
            name, separator, remainder = bytes(data[offset:]).partition( b'\0' )
            offset += len( name ) + 1
            logger.debug( "\tMarker Name: {}".format(name.decode('utf-8')))

        return offset

    # Unpack a rigid body description packet
    def __unpackRigidBodyDescription( self, data ):
        offset = 0

        # Version 2.0 or higher
        if( self.natNetStreamVersion[0] >= 2 ):
            name, separator, remainder = bytes(data[offset:]).partition( b'\0' )
            offset += len( name ) + 1
            logger.debug("\tMarker Name: {}".format(name.decode('utf-8')))

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
        logger.debug("\tMarker Name: {}".format(name.decode('utf-8')))

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
