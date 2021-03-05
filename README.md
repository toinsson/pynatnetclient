# pynatnet

Python client for [Optitrack](https://optitrack.com/) cameras.

Adapted from the sample provided in the [NatNet client SDK](https://optitrack.com/software/natnet-sdk/). This client also includes version for Optitrack servers running on remote machine. This was developed based on the forum [thread](https://forums.naturalpoint.com/viewtopic.php?f=59&t=13472).


# Changes

- split the code in separate classes
- replace the tracing function with logging
- add remote server functionality
- remove callback function for data access
- implement a local datastore

The original files from the SDK are included in the legacy folder.
