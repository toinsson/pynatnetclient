
client_address = '192.168.0.11'
server_address = '192.168.0.10'

from NatNetClient import NatNetClient


# This is a callback function that gets connected to the NatNet client and called once per mocap frame.
def receiveNewFrame( frameNumber, markerSetCount, unlabeledMarkersCount, rigidBodyCount, skeletonCount,
                    labeledMarkerCount, timecode, timecodeSub, timestamp, isRecording, trackedModelsChanged ):
    # print( "Received frame", frameNumber )
    pass

# This is a callback function that gets connected to the NatNet client. It is called once per rigid body per frame
def receiveRigidBodyFrame( id, position, rotation ):
    # print( "Received frame for rigid body", id )
    pass

# This will create a new NatNet client
streamingClient = NatNetClient(client_address, server_address, tracing=False)

# Configure the streaming client to call our rigid body handler on the emulator to send data out.
streamingClient.newFrameListener = receiveNewFrame
streamingClient.rigidBodyListener = receiveRigidBodyFrame


streamingClient.run()

print('passed the init')

import time

flag = True
while flag:
    try:
        time.sleep(0.1)
        print(streamingClient.ed.frameNumber)
    except KeyboardInterrupt:
        print('receive stop')
        streamingClient.stop()
        flag = False