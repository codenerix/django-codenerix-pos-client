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
import datetime

from workers import POSWorker


class Watchdog(POSWorker):

    hearbeat_rate = 6   # Beats per minute
    hurted_after = 25   # Hurted after 25 seconds
    dead_after = 60     # Shutdown after 60 seconds
    last_beat = None    # No last beat
    suicides = 0        # Times we have tried to suicide

    def __init__(self, uid, name, posclient):

        # POSClient object
        self.__posclient = posclient

        # Let the constructor to finish the job
        super(Watchdog, self).__init__(uid, {'name': name})

    def run(self):

        # Set up
        self.debug("Starting Watchdog", color='blue')

        # We start with no beats
        beats = 0

        # Last beat is now
        self.last_beat = datetime.datetime.now()

        # While we should keep working
        while not self.stoprequest.isSet():
            if beats:
                # One beat less
                beats -= 1
            else:
                # Say the system we are doing a heartbeat
                # self.debug("Heartbeat cycle", color='white')
                if self.suicides:
                    self.warning("I have tried to suicide {} times, can you imagine how difficult is to live like this? O_O".format(self.suicides))

                # Get timestamp
                now = datetime.datetime.now()

                # Reset beats
                beats = 60 / self.hearbeat_rate

                # Get the last message from the buffer
                package = None
                tmppackage = self.get()
                while tmppackage:
                    package = tmppackage
                    tmppackage = self.get()

                # If we got some package
                if package:
                    (source, msg, ref) = package
                    #self.debug("Watchdog MSG: {} (REF:{})".format(msg, ref), color='purple')

                    # Check last beat
                    try:
                        refdate = datetime.datetime.strptime(ref, '%Y-%m-%d %H:%M:%S.%f')
                    except Exception:
                        refdate = 0
                    self.last_beat = max(self.last_beat, refdate)

                # Check distance from reality
                distance = datetime.datetime.now() - self.last_beat
                if distance.seconds > self.dead_after:
                    # It has passed too much time since last confirmed beat, we are dead! :-(
                    self.warning("Good bye world! :-(")
                    self.suicides += 1
                    self.send("shutdown", str(datetime.datetime.now()))
                    # Wait 10 seconds for the system to die
                    tries = 10
                    while tries and (not self.stoprequest.isSet()):
                        tries -= 1
                        time.sleep(1)
                    continue
                elif distance.seconds > self.hurted_after:
                    self.warning("Getting a ticket to /dev/null, trash or wherever processes are gone when we die! :-(")
                else:
                    # Nothing to do, send another pingdog
                    # self.debug("Heartbeat - {}".format(now), color='white')
                    self.__posclient.send({'action': 'pingdog'}, str(now))

            # Sleep for a second (1 beat a second)
            time.sleep(1)

        # Get back the thread
        self.debug("Watchdog is down...", color='green')
