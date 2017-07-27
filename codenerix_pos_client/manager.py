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

import time

from codenerix.lib.debugger import Debugger

from webserver import WebServer
from hardware import Hardware
#from wsclient import WSClient

from workers import POSWorker

from __init__ import __version_name__

class Manager(Debugger):

    def __init__(self):
        self.set_name("Manager")
        self.set_debug()
        self.debug("Starting {}".format(__version_name__), color='blue')
        self.__workers = []

    def attach(self, worker):
        self.debug("Attaching worker '{}' with UUID '{}'".format(worker.name, worker.uuid), color='cyan')
        self.__workers.append(worker)

    def run(self):

        # Start all workers
        self.debug("POSClient: waiting for workers to get ready", color='blue')
        for worker in self.__workers:
            self.debug("    > Starting {}...".format(worker.name), color='cyan')
            worker.start()

        time.sleep(1)

        # Stay in main loop
        self.debug("POSClient: sleeping on main Thread (use CTRL+C to exit)", color='yellow')
        try:
            while True:
                time.sleep(10)
        except:
            print()

        # Ask threads to die and wait for them to do it
        self.debug("POSClient: waiting for workers to finish", color='blue')
        for worker in self.__workers:
            self.debug("    > Stopping {}...".format(worker.name), color='cyan')
            worker.join()
        self.debug("POSClient: finished", color='cyan')

if __name__ == '__main__':
    m = Manager()
    m.C_WebServer='WebServer'
    m.C_Hardware='WebServer'
    m.attach(POSWorker('paco'))
    m.attach(POSWorker('luis'))
    m.attach(POSWorker('pedro'))
    #m.attach(WebServer(m.C_WebServer))
    #m.attach(Hardware(m.C_Hardware))
#    m.attach(WSClient("127.0.0.1:8000"))
    m.run()
