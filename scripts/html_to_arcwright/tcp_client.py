import socket
import json
import time


class TCPClient:
    def __init__(self, host='localhost', port=13377, timeout=30):
        self.host = host
        self.port = port
        self.timeout = timeout

    def send(self, cmd, params, retries=3):
        for attempt in range(retries):
            try:
                s = socket.socket()
                s.settimeout(self.timeout)
                s.connect((self.host, self.port))
                s.send((json.dumps({'command': cmd, 'params': params}) + '\n').encode())
                resp = b''
                while True:
                    chunk = s.recv(65536)
                    if not chunk:
                        break
                    resp += chunk
                    if b'\n' in resp:
                        break
                s.close()
                time.sleep(0.15)
                return json.loads(resp.decode().strip())
            except (ConnectionResetError, ConnectionRefusedError,
                    socket.timeout) as e:
                if attempt < retries - 1:
                    time.sleep(3)
                else:
                    raise
