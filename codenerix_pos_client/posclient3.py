#!/usr/bin/env python3
# encoding: utf-8

import json
import base64
import pyotp
import hashlib
import socket
import websocket
#import _thread
#import time

from manager import Manager
from config import ID, KEY, SERVER


from websocket import create_connection, WebSocket

#def on_message(ws, message):
#def on_error(ws, error):
#    if type(error) == KeyboardInterrupt:
#        print("Closed by user request")
#    else:
#        print("### error ###")
#        print(error)

#def on_close(ws):
#    print("### closed ###")

from ws4py.client.tornadoclient import TornadoWebSocketClient
from tornado import ioloop

class POSClient(TornadoWebSocketClient):
    def opened(self):
        print("Open")

    def closed(self, code, reason=None):
        print("Closed down", code, reason)
        ioloop.IOLoop.instance().stop()


    def received_message(self, message):
        print(self.__dict__)
        print(message.__dict__)
        print()
        request = json.loads(message.data.decode('utf-8'))
        action = request.get('action', None)
        if action == 'authenticate':
            challenge = request.get('challenge', '')
            
            hashkey = "{}{}".format(challenge, KEY)
            hash32 = base64.b32encode(bytes(hashkey,'utf-8'))
            totp = pyotp.TOTP(hash32).now()
            
            token = hashlib.sha1(bytes("{}{}".format(hashkey,totp),'utf-8')).hexdigest()
            
            msg={
                'action':'authenticate',
                'id':ID,
                'token':token,
                }
            ws.send(json.dumps(msg))
        elif action == 'authenticated':
            authenticated=request.get('result')
            print("Authenticated:{}".format(authenticated))
            #ws.send(json.dumps("HOLA"))
            print("1")
            ws.send(json.dumps({"action":"HOLA",'id':1}))
            print("2")
            ws.send(json.dumps({"action":"HOLA",'id':2}))
            print("3")
            ws.send(json.dumps({"action":"HOLA",'id':3}))
            print("4")
    #        if authenticated:
            
        else:
            print("Unknown action '{}'".format(action))
            # self.close(reason='Bye bye')


ws = POSClient("ws://{}/codenerix_pos/".format(SERVER), protocols=['http-only', 'chat'])
ws.connect()

ioloop.IOLoop.instance().start()
