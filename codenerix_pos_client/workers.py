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

import time
import random
import uuid
import json
import queue
import threading

from codenerix.lib.debugger import Debugger

class POSWorker(threading.Thread, Debugger):
    queues = {}
    queues_name = {}
    queues_uuid = {}
    
    def __init__(self, name):
        # Prepare debugger
        self.set_name(name)
        self.set_debug()
        
        # Prepare threading system
        super(POSWorker, self).__init__()
        self.stoprequest = threading.Event()
        
        # Setup ourselves
        self.name = name
        self.__uuid = str(uuid.uuid4())
        self.__queue = queue.Queue()
        
        # Attach our queue to the Queue system
        self.queues[self.__uuid]=self.__queue
        self.queues_name[self.__uuid]=name
        self.queues_uuid[name]=self.__uuid
    
    @property
    def uuid(self):
        return self.__uuid
    
    def get_queue(self, name):
        return self.queues.get(self.queues_uuid.get(name, None), None)
    
    def get_name(self, uuid):
        # Check if we got a Queue
        if isinstance(uuid, queue.Queue):
            
            # Get got a Queue, find its UUID
            result=None
            for tuuid, tqueue in self.queues.items():
                if tqueue==uuid:
                    result=tuuid
            
            # If we got the UUID
            if result:
                uuid=result
            else:
                # Notify if no UUID was found for that Queue
                self.warning("POSWorker with the given Queue is not registered")
                uuid = None
        
        # Return the name
        return self.queues_name.get(uuid, None)
    
    def get_uuid(self, name):
        # Check if we got a Queue
        uuid = None
        if isinstance(name, queue.Queue):
            
            # Get got a Queue, find its UUID
            result=None
            for tuuid, tqueue in self.queues.items():
                if tqueue==name:
                    result=tuuid
            
            # If we got the UUID
            if result:
                uuid=result
            else:
                # Notify if no UUID was found for that Queue
                self.warning("POSWorker with the given Queue is not registered")
        
        # If no UUID found yet, try with by name
        if not uuid:
            uuid = self.queues_uuid.get(name, None)
        
        # Return the UUID
        return uuid
    
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
            if uuid in self.queues:
                # Give back the queue object already selected
                answer = (self.queues[uuid], msg)
            else:
                # Unknown sender detected (or Queue not registered properly)
                self.warning("We got a message from an unknown Queue with UUID '{}' (maybe it didn't register properly)".format(uuid))
                answer = (uuid, msg)
            
        else:
            answer = None
        
        return answer
    
    def send(self, target, msg):
        
        # Check if we got a Queue
        if not isinstance(target, queue.Queue):
            
            # Look for the target queue
            if target in self.queues:
                target = self.queues[target]
            else:
                # Notify if no queue found
                raise POSWorkerNotFound("POSWorker with UUID '{}' didn't register properly (Queue messages not found)".format(uuid))
        
        # Convert message to JSON
        msg = json.dumps((self.__uuid, msg))
        
        # Send the message to the queue
        target.put(msg)
    
    def run(self):
        
        # Keep running until master say to stop
        while not self.stoprequest.isSet():
            
            # Check if we have messages waiting
            package = self.get()
            if package:
                (uuid, msg) = package
                if 'OK' in msg:
                    print("{} GOT ANSWER FROM {} -> OK - [{}]".format(self.name, self.get_name(uuid),msg))
                else:
                    print("{} GOT MSG FROM {} -> {}".format(self.name, self.get_name(uuid), msg))
                    time.sleep(random.randint(2,5))
                    answer="#{}=OK#".format(msg)
                    print("{} ANSWER TO {} -> OK - [{}]".format(self.name, self.get_name(uuid), answer))
                    self.send(uuid, answer)
            else:
                if random.randint(0,100)>90:
                    # Choose a random queue
                    qs=list(self.queues.keys())
                    qs.pop(qs.index(self.__uuid))
                    targetuuid=random.choice(qs)
                    # Send message
                    msgs=["HEY MAN", "WHATS UP", "HELLO WORLD", "GOODBYE COCODRILE", "SEE YOU LATER ALIGATOR"]
                    msg=random.choice(msgs)
                    print("*{} -> {} :: {}  !!! RANDOM".format(self.name, self.get_name(targetuuid), msg))
                    time.sleep(random.randint(0,2))
                    self.send(targetuuid, msg)
                else:
                    time.sleep(1)
    
    def join(self, timeout=None):
        self.stoprequest.set()
        super(POSWorker, self).join(timeout)

class POSWorkerNotFound(Exception):

    def __init__(self,string):
        self.string = string

    def __str__(self):
        return self.string


