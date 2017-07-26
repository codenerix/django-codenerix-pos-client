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


async def hello(myloop):

    # Internal status
    authenticated = False

    async with websockets.connect("ws://{}/codenerix_pos/?session_key=asdf".format(SERVER)) as websocket:

        while True:

            # Wait for a message
            message = await websocket.recv()
            print("New MSG: {}".format(message))
            print()

            # Decode it
            request = json.loads(message)

            # Check action
            action = request.get('action', None)
            if action == 'authenticate':

                # Server request authentication
                print("AUTHENTICATE")
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
                print(1)
                await websocket.send(json.dumps({"action": "HOLA", "id": 3}))
                print(2)
                message = await websocket.recv()
                print("3:{}".format(message))
                await websocket.send(json.dumps(msg))
                print(4)

            elif action == 'authenticated':

                # Server answered to our authentication
                print("AUTHENTICATED")
                authenticated = request.get('result')
                print("Authenticated:{}".format(authenticated))

                # Check if we got authenticated
                if authenticated:

                    # Start main bucle
                    # while True:
                    #    await asyncio.sleep(1)
                    await websocket.send(json.dumps({"action": "HOLA", "id": 3}))
                    await websocket.send(json.dumps({"action": "HOLA", "id": 3}))
                    await websocket.send(json.dumps({"action": "HOLA", "id": 3}))

        else:
            print("Unknown action '{}'".format(action))


async def test():
    loop.stop()

if __name__ == "__main__":
    print("========================")
    loop = asyncio.get_event_loop()
#    asyncio.ensure_future(test())
    try:
        loop.run_until_complete(hello(loop))
        loop.run_forever()
    except Exception as error:
        if type(error) == KeyboardInterrupt:
            print("Closed by user request")
        else:
            print("### error ###")
            print(error)
    finally:
        print("Pending tasks at exit: %s" % asyncio.Task.all_tasks(loop))
        loop.close()
