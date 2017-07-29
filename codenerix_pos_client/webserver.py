#!/usr/bin/env python3
# encoding: utf-8
#
# django-codenerix-pos-client
#
# Copyright 2017 Juanmi Taboada - http://www.juanmitaboada.com
#
# Project URL : http://www.codenerix.com
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
import time
import threading
from socketserver import ThreadingMixIn
from http.server import HTTPServer, BaseHTTPRequestHandler

from codenerix.lib.debugger import Debugger

from workers import POSWorker
from config import UUID


class Handler(BaseHTTPRequestHandler, Debugger):

    def __init__(self, *args, **kwargs):
        # Prepare debugger
        self.set_name(threading.currentThread().getName())
        self.set_debug()

        # Let the lass finish it works
        super(Handler, self).__init__(*args, **kwargs)

    def do_GET(self):

        # # Convert answer to JSON
        # if self.path=='/getkey':
        #     answer = json.dumps({'name':self.server.posworker.name, 'msg':'hola'})
        # elif self.path=='/getdnie':
        #     self.send(self.server.C_Hardware, {'action': 'GETDNIE'})
        #     answer = self.get(True, 5)
        # else:
        #     answer = "Unknown request"
        answer = json.dumps({'uuid': UUID})

        # Prepare response
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()

        # Send response
        try:
            self.wfile.write(bytes(answer, 'utf-8'))
        except BrokenPipeError:
            pass

        return


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
        """Handle requests in a separate thread."""


class WebServer(POSWorker):

    def __init__(self, uid, name, ip='127.0.0.1', port=8080):

        # Save configuration
        self.__ip = ip
        self.__port = port

        # Let the constructor to finish the job
        super(WebServer, self).__init__(uid, {'name': name})

    def run(self):

        # Set up
        self.debug("Starting WebServer at {}:{}".format(self.__ip, self.__port), color='blue')
        server = ThreadedHTTPServer((self.__ip, self.__port), Handler)
        server.posworker = self
        thread = threading.Thread(target=server.serve_forever)
        thread.start()

        # Keep running until master say to stop
        self.debug("WebServer is up", color='green')
        while not self.stoprequest.isSet():
            time.sleep(1)

        self.debug("Shutting down...", color='blue')
        server.shutdown()
        self.debug("Server is down", color='green')
