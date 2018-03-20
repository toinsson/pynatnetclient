
import logging
logging.basicConfig(level=logging.WARNING)


from NatNetClient import NatNetClient

client_address = '192.168.0.11'
server_address = '192.168.0.10'
nnc = NatNetClient(client_address, server_address, tracing=False)
nnc.run()

import time

flag = True
while flag:
    try:
        time.sleep(0.1)
        with nnc.ed.lock:
            print(nnc.ed.frameNumber)
            print(nnc.ed.labeledMarker)
            print(nnc.ed.timestamp, nnc.ed.stampDataReceived, nnc.ed.stampTransmit)
    except KeyboardInterrupt:
        print('receive stop')
        nnc.stop()
        flag = False