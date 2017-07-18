#!/usr/bin/env python3
# encoding: utf-8

import json
import websocket
#import _thread
import time
from config import SERVER

def on_message(ws, message):
    print(message)

def on_error(ws, error):
    print("### error ###")
    print(error)

def on_close(ws):
    print("### closed ###")

def on_open(ws):
    print("OPEN")
    ws.send(json.dumps({"text":"hola caracola"}))
#    def run(*args):
#        for i in range(3):
#            time.sleep(1)
#            ws.send("Hello %d" % i)
#        time.sleep(1)
#        ws.close()
#        print("thread terminating...")
#    thread.start_new_thread(run, ())


if __name__ == "__main__":
    websocket.enableTrace(False)
    ws = websocket.WebSocketApp("ws://{}/".format(SERVER),
                              on_open = on_open,
                              on_message = on_message,
                              on_error = on_error,
                              on_close = on_close,
                              )
    # ws.on_open = on_open
    for i in range(1,10):
        time.sleep(1)
    ws.run_forever()
