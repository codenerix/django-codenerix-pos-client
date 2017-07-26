#!/usr/bin/env python3
# encoding: utf-8

""" POSClient 2 """

import json
import base64
import pyotp
import hashlib
#import _thread
#import time

from ws4py.client.threadedclient import WebSocketClient

#from manager import Manager
from config import ID, KEY, SERVER




#def on_message(ws, message):
#def on_error(ws, error):
#    if type(error) == KeyboardInterrupt:
#        print("Closed by user request")
#    else:
#        print("### error ###")
#        print(error)

#def on_close(ws):
#    print("### closed ###")


class POSClient(WebSocketClient):
    def opened(self):
        print("Open")

    def closed(self, code, reason=None):
        print("Closed down", code, reason)

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

if __name__ == '__main__':
    try:
        ws = POSClient("ws://{}/codenerix_pos/".format(SERVER), protocols=['http-only', 'chat'])
        ws.connect()
        ws.run_forever()
    except KeyboardInterrupt:
        ws.close()



