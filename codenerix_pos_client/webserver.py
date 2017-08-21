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

from tornado.httpserver import HTTPServer
from tornado.websocket import WebSocketHandler
from tornado.ioloop import IOLoop
from tornado.web import Application


from codenerix.lib.debugger import Debugger

from workers import POSWorker
from config import UUID, PORT, ALLOWED_IPS, KEY


class WSHandler(WebSocketHandler, Debugger):

    def __init__(self, *args, **kwargs):
        # Prepare debugger
        self.set_name('Tornado Websocket Server')
        self.set_debug()

        # Let the lass finish it works
        super(WSHandler, self).__init__(*args, **kwargs)

    def open(self):
        self.debug('New connection from {}'.format(self.request.remote_ip), color='cyan')
        self.write_message(json.dumps({'uuid': UUID, 'key': KEY}))

    def on_message(self, message):
        self.debug('Message from {}: {}'.format(self.request.remote_ip, message), color='green')
        self.write_message(json.dumps({'uuid': UUID}))

    def on_close(self):
        self.debug('Connection closed for {}'.format(self.request.remote_ip), color='cyan')

    def check_origin(self, origin):
        remote_ip = self.request.remote_ip
        allowed = ['127.0.0.1'] + ALLOWED_IPS
        allow = remote_ip in allowed
        if allow:
            self.debug('Check ORIGIN - Remote IP: {}'.format(remote_ip), color='blue')
        else:
            self.debug('Check ORIGIN - Remote IP: {} - ACCESS DENIED - ALLOWED: {}'.format(remote_ip, allowed), color='red')
        return allow


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
        """Handle requests in a separate thread."""


class WebServer(POSWorker):

    def __init__(self, uid, name):

        # Save configuration
        self.__allowed_ips = ALLOWED_IPS

        # Let the constructor to finish the job
        super(WebServer, self).__init__(uid, {'name': name})

    def run(self):

        application = Application([
                (r'/codenerix_pos_client/', WSHandler),
        ])

        # Set up
        self.debug("Starting Tornado WebSocketServer at port {}".format(PORT), color='blue')
        server = ThreadedHTTPServer(application)
        server.posworker = self
        server.listen(PORT)
        thread = threading.Thread(target=IOLoop.instance().start)
        thread.start()

        # Keep running until master say to stop
        self.debug("WebServer is up", color='green')
        while not self.stoprequest.isSet():
            time.sleep(1)

        self.debug("Shutting down...", color='blue')
        server.stop()
        self.debug("Server is down", color='green')
