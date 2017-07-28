#!/usr/bin/env python3
# encoding: utf-8

import json
import uuid

from ws4py.client.threadedclient import WebSocketClient

from codenerix.lib.debugger import Debugger
from codenerix_extensions.lib.cryptography import AESCipher

from __init__ import __version_name__

from manager import Manager
from webserver import WebServer
from config import UUID, KEY, SERVER

from hardware import POSWeight, POSTicketPrinter, POSCashDrawer, POSDNIe


class POSClient(WebSocketClient, Debugger):

    AVAILABLE_HARDWARE = {
        'WEIGHT': POSWeight,
        'TICKET': POSTicketPrinter,
        'CASH': POSCashDrawer,
        'DNIE': POSDNIe,
    }

    manager = Manager()

    def __init__(self, *args, **kwargs):
        # Set debugger
        self.set_debug()
        self.set_name('POSClient')
        self.debug("Starting {}".format(__version_name__), color='blue')

        # Initialize environment
        self.challenge = None
        self.hardware = {}
        self.crypto = AESCipher()
        self.uuid = uuid.UUID(UUID)
        self.uuidhex = self.uuid.hex

        # Keep going with warm up
        super(POSClient, self).__init__(*args, **kwargs)

    def shutdown(self):
        if self.manager.isrunning:
            self.manager.shutdown()

    def opened(self):
        self.debug("Requesting config", color="blue")
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
            'uuid': self.uuidhex,
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

    def recv(self, message):
        action = message.get('action', None)
        if action == 'config':
            if not self.manager.isrunning:
                # Initialize manager
                self.debug("Preparing manager", color='blue')
                self.manager.attach(WebServer(uuid.uuid4(), 'Local Webserver'))

                # Configure hardware
                self.debug("Setting configuration", color='blue')
                for hw in message.get('hardware', []):
                    # Get details
                    uuidtxt = hw.get('uuid', None)
                    kind = hw.get('kind', '')
                    config = hw.get('config', {})

                    if uuidtxt is not None:
                        uid = uuid.UUID(uuidtxt)
                        self.debug("    > Configuring ", color='yellow', tail=False)
                        self.debug(str(uid), color='purple', head=False, tail=False)
                        self.debug(" as ", color='yellow', head=False, tail=False)
                        if kind in self.AVAILABLE_HARDWARE:
                            self.debug(kind, color='white', head=False, tail=False)
                            self.manager.attach(self.AVAILABLE_HARDWARE.get(kind)(uid, config))
                            self.debug("", color='white', head=False)
                        else:
                            self.debug("{}??? - Not setting it up!".format(kind), color='red', head=False)
                    else:
                        self.error("    > I found a hardware configuration without UUID, I will not set it up!")

                # Start Manager
                self.manager.run()

            else:
                self.error("Configuration request not accepted, we are already configured!")
        else:
            print("Unknown action '{}'".format(action))
            # self.close(reason='Bye bye')


if __name__ == '__main__':
    ws = POSClient("ws://{}/codenerix_pos/?session_key={}".format(SERVER, uuid.uuid4().hex), protocols=['http-only', 'chat'])
    ws.connect()
    try:
        ws.run_forever()
    except KeyboardInterrupt:
        ws.debug("")
        ws.debug("User requested to exit", color='yellow')
        ws.debug("")
    finally:
        ws.shutdown()
        ws.close()
