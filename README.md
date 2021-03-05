# pynatnet

Python client for [Optitrack](https://optitrack.com/) cameras.

Adapted from the sample provided in the [NatNet client SDK](https://optitrack.com/software/natnet-sdk/). This client also includes version for Optitrack servers running on remote machine, which was developed based on the feedback from this forum [thread](https://forums.naturalpoint.com/viewtopic.php?f=59&t=13472).


# Changes

- split the code in separate classes
- create a package and add a setup.py file
- replace the tracing function with logging
- add remote server functionality
- remove callback function for data access
- implement a local datastore

The original files from the SDK are included in the [legacy](./legacy) folder.
