# pynatnetclient

Python client for [Optitrack](https://optitrack.com/) cameras.

Adapted from the sample provided in the [NatNet client SDK](https://optitrack.com/software/natnet-sdk/), this client also includes an option for Optitrack servers running on remote machines, which was developed based on the feedback from this forum [thread](https://forums.naturalpoint.com/viewtopic.php?f=59&t=13472).

# usage

When the Optitrack server is running on the same machine as the data consumer:

```
from pynatnetclient import NatNetClient

nnc = NatNetClient()  # connect to a local server by default
nnc.run()             # start the listening thread

with nnc.ed.lock:     # access thread-safe data
    print(nnc.ed.frameNumber)

nnc.close()           # close the listening thread
```

When the Optitrack server is streaming over the network, the server and client address are required:

```
client_address = 192.168.0.10
server_address = 192.168.0.11

nnc = NatNetClient(client_address, server_address)  # connect to a remote server
```

OBS: The data that is currently exposed through the class [ExposedData](./pynatnetclient/unpack.py#L14) only relates to labeled markers:

```
class ExposedData(object):

    frameNumber
    labeledMarkerCount
    labeledMarker
    timestamp
    stampCameraExposure
    stampDataReceived
    stampTransmit
```

# changes

- split the code in separate classes
- create a package and add a setup.py file
- replace the tracing function with logging
- add remote server functionality
- remove callback function for data access
- implement a local datastore

The original files from the SDK are included in the [legacy](./legacy) folder.
