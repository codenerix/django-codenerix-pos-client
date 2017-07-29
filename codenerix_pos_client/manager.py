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
import uuid
import queue

from codenerix.lib.debugger import Debugger


class Manager(Debugger):

    __running = False

    def __init__(self):
        self.set_name("Manager")
        self.set_debug()
        self.__workers = []
        self.__uuid = uuid.uuid4()
        self.__uuidhex = self.__uuid.hex

        # Attach to POSWorker class
        self.queue = queue.Queue()

    @property
    def isrunning(self):
        return self.__running

    @property
    def uuid(self):
        return self.__uuid

    @property
    def uuidhex(self):
        return self.__uuidhex

    def exists_worker(self, uid):
        for worker in self.__workers:
            if worker.uuid == uid:
                return True
        return False

    def attach(self, worker):
        # Add parent to the list
        worker.parent(self.uuidhex, self.queue)

        # Append worker to workers
        self.__workers.append(worker)

    def run(self):
        # Manager is running
        self.__running = True

        # Start all workers
        self.debug("waiting for workers to get ready", color='blue')
        for worker in self.__workers:
            if not worker.isAlive():
                worker.start()
        self.debug("ready", color='yellow')

    def shutdown(self):
        # Ask threads to die and wait for them to do it
        self.debug("waiting for workers to finish", color='blue')
        while len(self.__workers):
            # Pop first worker from the list (we will pop them the same we we appended them)
            worker = self.__workers.pop(0)
            # self.debug("    > Waiting for {} to stop...".format(worker.uuid), color='cyan')
            worker.join()
        self.__running = False
        self.debug("finished", color='green')


if __name__ == '__main__':
    from workers import POSWorker
    m = Manager()
    for i in range(0, 3):
        p = POSWorker(uuid.uuid4(), {})
        p.demo = True
        m.attach(p)
    m.run()

    try:
        while True:
            time.sleep(100)
    except KeyboardInterrupt:
        m.shutdown()
