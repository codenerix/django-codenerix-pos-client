#!/usr/bin/env python3
# encoding: utf-8

import json
import base64
import pyotp
import hashlib
# import websocket
# import _thread
# import time
import asyncio
import websockets


# from manager import Manager
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
        hash32 = base64.b32encode(bytes(hashkey, 'utf-8'))
        totp = pyotp.TOTP(hash32).now()

        token = hashlib.sha1(bytes("{}{}".format(hashkey, totp), 'utf-8')).hexdigest()
        msg = {
            'action': 'authenticate',
            'id': ID,
            'token': token,
            }
        ws.send(json.dumps(msg))
        ws.send(json.dumps(msg))
    elif action == 'authenticated':
        authenticated = request.get('result')
        print("Authenticated:{}".format(authenticated))
        # ws.send(json.dumps("HOLA"))
        ws.send(json.dumps({"action": "HOLA", 'id': 1}))
        ws.send(json.dumps({"action": "HOLA", 'id': 2}))
        ws.send(json.dumps({"action": "HOLA", 'id': 3}))
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


async def hello():
    async with websockets.connect("ws://{}/codenerix_pos/?session_key=asdf".format(SERVER)) as websocket:

        await websocket.send(json.dumps({'action': 'hola'}))
        await websocket.send(json.dumps({'action': 'hola'}))
        await websocket.send(json.dumps({'action': 'hola'}))

        greeting = await websocket.recv()
        print("< {}".format(greeting))

#    finally:
#        yield from websocket.close()

if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(hello())


ws = websockets.connect("ws://{}/codenerix_pos/?session_key=asdf".format(SERVER))
