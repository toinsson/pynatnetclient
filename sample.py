import time
import logging
from pynatnetclient import NatNetClient

logging.basicConfig(level=logging.DEBUG)

if True:
    nnc = NatNetClient()
else:
    client_address = '192.168.0.11'
    server_address = '192.168.0.10'
    nnc = NatNetClient(client_address, server_address)

nnc.run()

flag = True
while flag:
    try:
        time.sleep(0.1)
        with nnc.ed.lock:
            print(nnc.ed.frameNumber)
    except KeyboardInterrupt:
        nnc.stop()
        flag = False
