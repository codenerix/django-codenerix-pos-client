# -*- coding: utf-8 -*-
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

import uuid
import json
import queue
import threading

from codenerix.lib.debugger import Debugger

class POSWorker(threading.Thread, Debugger):
    queues = {}
    
    def __init__(self, name):
        # Prepare debugger
        self.set_name('POSWorker')
        self.set_debug()
        
        # Prepare threading system
        super(POSWorker, self).__init__()
        self.stoprequest = threading.Event()
        
        # Setup ourselves
        self.name = name
        self.__uuid = uuid.uuid4()
        self.__queue = queue.Queue()
        
        # Attach our queue to the Queue system
        self.queues[self.__uuid]=self.__queue
    
    def uuid(self):
        return self.__uuid
    
    def get(self):
        
        # Get message
        try:
            msg = self.__queue.get(True, 0.05)
        except queue.Empty:
            msg = None
        
        # If got a message
        if msg:
            # Decode message
            (uuid, msg) = json.loads(msg)
            
            # Look for the target queue
            selqueue=None
            for key in self.queues:
                if key==uuid:
                    selqueue=self.queues[key]
            
            # If we found it
            if selqueue:
                # Give back the queue object already selected
                answer = (selqueue, msg)
            else:
                # Unknown sender detected (or Queue not registered properly)
                self.warning("We got a message from an unknown Queue with UUID '{}' (maybe it didn't register properly)".format(uuid))
                answer = (uuid, msg)
            
        else:
            answer = None
        
        return answer
    
    def send(self, target, msg):
        # Look for the target queue
        if not isinstance(target, queue.Queue):
            selqueue=None
            for key in self.queues:
                if key==uuid:
                    selqueue=self.queues[key]
        
        # Send the message if we got the queue
        if selqueue:
            
            # Convert message to JSON
            msg = json.dumps((self.__uuid, msg))
            
            # Send
            selqueue.put(msg)
            
        else:
            # Notify if no queue found
            raise POSWorkerNotFound("POSWorker with UUID '{}' didn't register properly (Queue messages not found)".format(uuid))
    
    def run(self):
        while not self.stoprequest.isSet():
            print("{}::{} -> {}".format(self.name, self.__uuid, self.get()))
            import time
            time.sleep(5)
    
    def join(self, timeout=None):
        self.stoprequest.set()
        super(POSWorker, self).join(timeout)

class POSWorkerNotFound(Exception):

    def __init__(self,string):
        self.string = string

    def __str__(self):
        return self.string


