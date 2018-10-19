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

from lib.debugger import Debugger


class POSWorker(threading.Thread, Debugger):
    queues = {}
    channels = {}
    module_name = None
    slow_loop = True

    def __init__(self, uid, config):
        # Get hex uuid
        uidhex = uid.hex
        # Prepare debugger
        self.set_name(uidhex)
        self.set_debug()

        # Prepare threading system
        super(POSWorker, self).__init__()
        self.stoprequest = threading.Event()

        # Setup ourselves
        self.__config = config
        self.__uuid = uid
        self.__uuidhex = uidhex
        self.__queue = queue.Queue()
        self.__parent = None

        # Attach our queue to the Queue system
        self.queues[uidhex] = self.__queue

    def __del__(self):
        if self.__uuidhex in self.queues:
            self.queues.pop(self.__uuidhex)

    @property
    def uuid(self):
        return self.__uuid

    @property
    def uuidhex(self):
        return self.__uuidhex

    def add_channel(self, name):
        if name not in self.channels:
            self.channels[name] = queue.Queue()
        else:
            self.warning("I have tried to add an already existing channel named '{}'".format(name))

    def remove_channel(self, name):
        if name in self.channels:
            self.channels.pop(name)
        else:
            self.warning("I have tried to remove a non-existing channel named '{}'".format(name))

    def sendto_channel(self, name, msg):

        # Locate the channel
        channel = self.channels.get(name, None)

        if channel:

            # Convert message to JSON
            tmsg = json.dumps((self.__uuidhex, msg))

            # Send the message
            channel.put(tmsg)

        else:
            self.warning("I have tried to send to a non-existing channel named '{}'".format(name))

        # Return answer
        return (channel is not None)

    def getfrom_channel(self, name, block=False, timeout=None):

        # Locate the channel
        channel = self.channels.get(name, None)

        if channel:

            # Get message
            try:
                tmsg = channel.get(block, timeout)
            except queue.Empty:
                tmsg = None

            if tmsg:

                # Decode message
                (uid, msg) = json.loads(tmsg)

                # Look for the target queue
                if uid in self.queues:
                    # Give back the queue object already selected
                    answer = (self.queues[uid], msg)
                else:
                    # Unknown sender detected (or Queue not registered properly)
                    self.warning("We got a message from an unknown Queue with UUID '{}' (maybe it didn't register properly)".format(uid))
                    answer = (uid, msg)

            else:
                answer = None

        else:
            self.warning("Tried to get from a non-existing channel named '{}'".format(name))
            answer = None

        # Return answer
        return answer

    def parent(self, uidhex, queue):
        self.__parent = uidhex
        if uidhex not in self.queues:
            self.queues[uidhex] = queue

    def config(self, key):
        if type(self.__config) is dict:
            return self.__config.get(key, None)
        else:
            return None

    def get_queue(self, uid):
        if isinstance(uid, uuid.UUID):
            uid = uid.hex
        return self.queues.get(uid, None)

    def get_uuid(self, obj):
        # Check if we got a Queue
        uid = None
        if isinstance(obj, queue.Queue):

            # Get got a Queue, find its UUID
            result = None
            for tuuid, tqueue in self.queues.items():
                if tqueue == obj:
                    result = tuuid

            # If we got the UUID
            if result:
                uid = result
            else:
                # Notify if no UUID was found for that Queue
                self.warning("POSWorker with the given Queue is not registered")

        # Return the UUID
        return uid

    def get(self, block=False, timeout=None):

        # Get message
        try:
            tmsg = self.__queue.get(block, timeout)
        except queue.Empty:
            tmsg = None

        # If got a message
        if tmsg:
            # Decode message
            (uid, msg, ref) = json.loads(tmsg)

            # Look for the target queue
            if uid in self.queues:
                # Give back the queue object already selected
                answer = (self.queues[uid], msg, ref)
            else:
                # Unknown sender detected (or Queue not registered properly)
                self.warning("We got a message from an unknown Queue with UUID '{}' (maybe it didn't register properly)".format(uid))
                answer = (uid, msg, ref)

        else:
            answer = None

        return answer

    def send(self, msg, ref, target=None):

        # Autoselect parent
        if target is None:
            target = self.get_queue(self.__parent)

        # Check if we got a Queue
        if not isinstance(target, queue.Queue):

            # Look for the target queue
            if target in self.queues:
                target = self.queues[target]
            else:
                # Notify if no queue found
                raise POSWorkerNotFound("POSWorker with UUID '{}' didn't register properly (Queue messages not found)".format(target))

        # Convert message to JSON
        msg = json.dumps((self.__uuidhex, msg, ref))

        # Send the message to the queue
        target.put(msg)

    def loop(self):
        pass

    def run(self, show_title=True):
        if self.module_name:
            self.debug("Starting {}".format(self.module_name), color='blue')

        # Keep running until master say to stop
        while not self.stoprequest.isSet():

            # Check if we have messages waiting
            package = self.get()
            if package:
                (source, msg, ref) = package
                try:
                    self.recv(msg, ref, source)
                except Exception as e:
                    try:
                        self.send({'uuid': self.uuidhex, 'from': self.get_uuid(source), 'msg': msg, 'error': e}, ref)
                    except Exception as e:
                        self.send({'uuid': self.uuidhex, 'from': self.get_uuid(source), 'msg': msg, 'error': "ERROR can not be sent: {}".format(e)}, ref)
            else:
                if getattr(self, 'demo', None):
                    # Demo mode is on
                    if random.randint(0, 100) > 90:
                        # Choose a random queue
                        qs = list(self.queues.keys())
                        qs.pop(qs.index(self.uuidhex))
                        targetuuid = random.choice(qs)
                        # Send message
                        msgs = ["HEY MAN", "WHATS UP", "HELLO WORLD", "GOODBYE COCODRILE", "SEE YOU LATER ALIGATOR"]
                        msg = {'message': random.choice(msgs)}
                        self.debug("{} -> {} :: {}  !!! RANDOM".format(self.uuid, targetuuid, msg), color='white')
                        time.sleep(random.randint(0, 1))
                        self.send(msg, None, targetuuid)
                    else:
                        time.sleep(0.1)
                else:
                    # Do a loop and wait sec
                    self.loop()
                    if self.slow_loop:
                        time.sleep(1)

    def recv(self, msg, ref, uid=None):
        # Autoselect parent
        if uid is None:
            uid = self.__parent

        if 'error' in msg:
            self.debug("{} GOT ANSWER FROM {} -> ERROR - [{}] (ref:{})".format(self.uuid, self.get_uuid(uid), msg.get('error', 'No error'), ref), color='green')
        elif 'ack' in msg:
            self.debug("{} GOT ANSWER FROM {} -> ACK - [{}] (ref:{})".format(self.uuid, self.get_uuid(uid), msg.get('ack', False), ref), color='green')
        elif 'message' in msg:
            self.debug("{} GOT MSG FROM {} -> {} (ref:{})".format(self.uuid, self.get_uuid(uid), msg, ref), color='blue')
            time.sleep(random.randint(0, 1))
            answer = {"ack": True, 'message': msg.get('message', '???')}
            self.debug("{} ANSWER TO {} -> OK - [{}] (ref:{})".format(self.uuid, self.get_uuid(uid), answer, ref), color='cyan')
            self.send(answer, ref, uid)
        else:
            msg = "Unknown msg kind"
            self.debug(msg)
            self.send({'error': msg}, ref, uid)

    def join(self, timeout=None):
        self.stoprequest.set()
        super(POSWorker, self).join(timeout)


class POSWorkerNotFound(Exception):

    def __init__(self, string):
        self.string = string

    def __str__(self):
        return self.string
