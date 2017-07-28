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

from codenerix.lib.debugger import Debugger

from workers import POSWorker


class Manager(Debugger):

    __running = False

    def __init__(self):
        self.set_name("Manager")
        self.set_debug()
        self.__workers = []

    @property
    def isrunning(self):
        return self.__running

    def attach(self, worker):
        self.debug("Attaching worker '{}' with UUID '{}'".format(worker.name, worker.uuid), color='cyan')
        self.__workers.append(worker)

    def run(self):
        # Manager is running
        self.__running = True

        # Start all workers
        self.debug("waiting for workers to get ready", color='blue')
        for worker in self.__workers:
            self.debug("    > Starting {}...".format(worker.name), color='cyan')
            worker.start()
        time.sleep(1)

    def shutdown(self):
        # Ask threads to die and wait for them to do it
        self.debug("waiting for workers to finish", color='blue')
        for worker in self.__workers:
            self.debug("    > Stopping {}...".format(worker.name), color='cyan')
            worker.join()
        self.debug("finished", color='cyan')
        self.__running = False


if __name__ == '__main__':
    m = Manager()
    m.attach(POSWorker(uuid.uuid4(), {}))
    m.attach(POSWorker(uuid.uuid4(), {}))
    m.attach(POSWorker(uuid.uuid4(), {}))
    m.run()

    try:
        while True:
            time.sleep(100)
    except KeyboardInterrupt:
        m.shutdown()
