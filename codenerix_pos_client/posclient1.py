#!/usr/bin/env python3
# encoding: utf-8

import json
import base64
import pyotp
import hashlib
import websocket
#import _thread
#import time

from manager import Manager
from config import ID, KEY, SERVER

def on_message(ws, message):
    print("#{}#".format(ws.cookie))
    print(ws.__dict__)
    print(message)
    print()
    request = json.loads(message)
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
        ws.send(json.dumps(msg))
    elif action == 'authenticated':
        authenticated=request.get('result')
        print("Authenticated:{}".format(authenticated))
        #ws.send(json.dumps("HOLA"))
        ws.send(json.dumps({"action":"HOLA",'id':1}))
        ws.send(json.dumps({"action":"HOLA",'id':2}))
        ws.send(json.dumps({"action":"HOLA",'id':3}))
#        if authenticated:
        
    else:
        print("Unknown action '{}'".format(action))

def on_error(ws, error):
    if type(error) == KeyboardInterrupt:
        print("Closed by user request")
    else:
        print("### error ###")
        print(error)

def on_close(ws):
    print("### closed ###")

#def on_open(ws):
#    print("OPEN")
#    ws.send(json.dumps({"text":"hola caracola"}))
#    def run(*args):
#        for i in range(3):
#            time.sleep(1)
#            ws.send("Hello %d" % i)
#        time.sleep(1)
#        ws.close()
#        print("thread terminating...")
#    thread.start_new_thread(run, ())
#
#
#        ws.send(json.dumps({"text":"hola caracola"}))
#        def run(*args):
#            print(args)
#            for i in range(10):
#                ws.send(json.dumps({'msg':"{} - Hello {}".format(args[0], i)}))
#            time.sleep(1)
#            ws.close()
#            print("thread terminating...")
#        _thread.start_new_thread(run, (1, ))
#        _thread.start_new_thread(run, (2, ))
#        _thread.start_new_thread(run, (3, ))




if __name__ == "__main__":
    websocket.enableTrace(False)
    ws = websocket.WebSocketApp("ws://{}/codenerix_pos/?session_key=asdf".format(SERVER),
                              # on_open = on_open,
                              on_message = on_message,
                              on_error = on_error,
                              on_close = on_close,
                              )
    # Attach manager to WS
    ws.manager = Manager()
    # Launch
    ws.run_forever()
