#!/usr/bin/env python3
"""Read-only guest-ping over the private QEMU Guest Agent Unix socket."""
import json
import socket
import sys
import time

deadline = time.monotonic() + 20
last_error = 'no reply'
while time.monotonic() < deadline:
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.settimeout(2)
            client.connect(sys.argv[1])
            client.sendall(b'{"execute":"guest-ping"}\n')
            with client.makefile('rb') as stream:
                raw = stream.readline(4097)
            if len(raw) > 4096:
                raise ValueError('Oversized agent reply')
            reply = json.loads(raw.lstrip(b'\xff'))
            if reply != {'return': {}}:
                raise ValueError('Unexpected guest-ping reply: ' + str(reply))
            print('QEMU Guest Agent: guest-ping passed')
            sys.exit(0)
    except (OSError, ValueError) as error:
        last_error = str(error)
        time.sleep(0.2)
sys.exit('QEMU Guest Agent did not answer guest-ping: ' + last_error)
