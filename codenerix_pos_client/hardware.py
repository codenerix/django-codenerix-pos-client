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
import datetime
import queue
import threading
from escpos.printer import Usb, Network

# Smartcard libraries
from smartcard.CardMonitoring import CardMonitor
from smartcard.CardType import AnyCardType
from smartcard.CardRequest import CardRequest
from smartcard.util import *

from codenerix.lib.debugger import Debugger
from worker import POSWorker
from dnie import DNIeObserver

class Hardware(POSWorker):

    def __init__(self, name, printer=None):
        '''
        config: can be
            - an ip address or hostname in a string to user Network hardware
            - a tuple with 2 elements to use Usb hardware
        '''
        
        # Let the constructor to finish the job
        super(Hardware, self).__init__(name)
        
        # Control we got a valid config
        if printer:
            if type(printer) == tuple:
                if len(printer) == 2:
                    (m1, m2) = config
                    self.warning("CHECK HERE FOR M1 and M2 connectino to Usb() now we use predefined values")
                    #self.__printer = Usb(0x1fc9, 0x2016)
                    self.__printer = None
                else:
                    raise IOError("Wrong configuration: 'tuple' == Usb hardware. You must provide 2 parameters to get it configure")
            elif type(config) == str:
                #self.__printer = Network('192.168.1.11')
                self.__printer = None
            else:
                raise IOError("Wrong configuration: not string or tuple detected, instead '{}'".format(type(printer)))
    
    @property
    def DNIeHandler(self):
        def got_internal_cid(posworker, struct):
            print("POSWORKER {} GOT CID: {}".format(posworker.name, struct))
        return lambda struct: got_internal_cid(self, struct)
    
    def run(self):
        self.debug("Starting Hardware system", color='blue')
        
        # Monitor for new cards
        cardtype = AnyCardType()
        try:
            cardrequest = CardRequest( timeout=1.5, cardType=cardtype )
            cardmonitor = CardMonitor()
            cardobserver = DNIeObserver( self.DNIeHandler )
            self.debug("Connecting observer", color='yellow')
            cardmonitor.addObserver( cardobserver )
        except Exception as e:
            self.error("No smartcard reader detected... (ERROR: {})".format(e))
            cardobserver=None
            cardmonitor=None
        
        while not self.stoprequest.isSet():
            request = self.get()
            
            if request:
                (uuid, msg) = request
                self.debug("IN msg: {}".format(request), color='cyan')
                if request == 'DNIE':
                    self.send(uuid, "Notify DNIE {}".format(datetime.datetime.now()))
                else:
                    self.send(uuid, "{}: {}?".format(datetime.datetime.now(), request))
                # Print this text
                #self.__hw.text("Hello World\n")
                # Print this image
                #self.__hw.image("logo.gif")
                # Print this barcode
                #self.__hw.barcode('1324354657687', 'EAN13', 64, 2, '', '')
                # Cut the paper
                #self.__hw.cut()
                # Open cash machine
                #self.__hw.cashdraw(2)
            
            # Sleep a second
            time.sleep(1)
        
        # Finish
        self.debug("Shutting down Hardware system", color='blue')
        
        # Remove the observer, or the monitor will poll forever
        if cardmonitor and cardobserver:
            cardmonitor.deleteObserver(cardobserver)
        
        # We are done
        self.debug("Hardware system is down", color='blue')

