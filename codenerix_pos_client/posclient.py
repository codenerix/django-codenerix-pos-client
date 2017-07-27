#!/usr/bin/env python3
# encoding: utf-8

import json
import uuid

from ws4py.client.threadedclient import WebSocketClient

from codenerix.lib.debugger import Debugger
from codenerix_extensions.lib.cryptography import AESCipher

# from manager import Manager
from config import ID, KEY, SERVER


class POSClient(WebSocketClient, Debugger):

    def recv(self, message):
        action = message.get('action', None)
        if action == 'config':
            self.debug("Setting configuration", color='blue')
            for hardware in message.get('hardware', []):
                # Get details
                uuidtxt = hardware.get('uuid', None)
                kind = hardware.get('kind', '')
                # config = hardware.get('config', {})

                if uuidtxt is not None:
                    uid = uuid.UUID(uuidtxt)
                    self.debug("    > Configuring ", color='yellow', tail=False)
                    self.debug(str(uid), color='purple', head=False, tail=False)
                    self.debug(" as ", color='yellow', head=False, tail=False)
                    if kind in ['WEIGHT', 'TICKET', 'CASH', 'DNIE']:
                        self.debug(kind, color='white', head=False)
                        # We have here
                        # uid  => UUID
                        # kind => WEIGHT, TICKET, CASH, DNIE
                        # config => { configuration }
                    else:
                        self.debug("{}??? - Not setting it up!".format(kind), color='red', head=False)
                else:
                    self.error("    > I found a hardware configuration without UUID, I will not set it up!")
        else:
            print("Unknown action '{}'".format(action))
            # self.close(reason='Bye bye')

    # === MANAGEMENT CODE === ===============================================

    def __init__(self, *args, **kwargs):
        self.crypto = AESCipher()
        self.set_debug()
        self.set_name('POSClient')
        self.challenge = None
        super(POSClient, self).__init__(*args, **kwargs)

    def opened(self):
        self.debug("Opening Websocket", color="blue")
        self.send({'action': 'get_config'})

    def closed(self, code, reason=None):
        self.debug("Websocket closed", color="blue")

    def send_error(self, msg):
        self.error(msg)
        super(POSClient, self).send(json.dumps({'error': True, 'errortxt': msg}))

    def send(self, request):
        # Encode request
        msg = json.dumps(request)

        # Build query
        query = {
            'id': ID,
            'message': self.crypto.encrypt(msg, KEY).decode('utf-8'),
        }

        # Encode to JSON
        data = json.dumps(query)

        # Send to remote
        super(POSClient, self).send(data)

    def received_message(self, package):
        self.debug("New message arrived", color='yellow')

        try:
            request = json.loads(package.data.decode('utf-8'))
        except Exception:
            request = None

        # Check if we got msg
        if request is not None and isinstance(request, dict):
            message = request.get('message', None)
            if message is not None:

                # Decrypt message
                msg = self.crypto.decrypt(message, KEY)
                try:
                    query = json.loads(msg)
                except Exception:
                    query = None
                if query is not None and isinstance(query, dict):
                    self.debug("Receive: {}".format(query), color='cyan')
                    self.recv(query)
                else:
                    if query is None:
                        self.send_error("Message is not JSON or is None")
                    else:
                        self.send_error("Message is not a Dictionary")
            else:
                self.send_error("Missing 'message' or is None")
        else:
            if request is None:
                self.send_error("Request is not JSON or is None")
            else:
                self.send_error("Request is not a Dictionary")


if __name__ == '__main__':
    try:
        ws = POSClient("ws://{}/codenerix_pos/?session_key={}".format(SERVER, uuid.uuid4().hex), protocols=['http-only', 'chat'])
        ws.connect()
        ws.run_forever()
    except KeyboardInterrupt:
        ws.close()
