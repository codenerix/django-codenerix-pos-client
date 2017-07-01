#!/usr/bin/env python3
# encoding: utf-8

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
from dnie import DNIeObserver

class POSNotify(threading.Thread, Debugger):

    def __init__(self, config, inmsg, outmsg):
        '''
        config: can be
            - an ip address or hostname in a string to user Network hardware
            - a tuple with 2 elements to use Usb hardware
        inmsg: a Queue object (to get messages from another service)
        outmsg: a Queue object (to put messages for another service)
        '''
        
        # Prepare debugger
        self.set_name('POSNotify')
        self.set_debug()
        
        # Control we got a valid config
        if type(config) == tuple:
            if len(config) == 2:
                (m1, m2) = config
                self.warning("CHECK HERE FOR M1 and M2 connectino to Usb() now we use predefined values")
                #self.__hw = Usb(0x1fc9, 0x2016)
                self.__hw = None
            else:
                raise IOError("Wrong configuration: 'tuple' == Usb hardware. You must provide 2 parameters to get it configure")
        elif type(config) == str:
            #self.__hw = Network('192.168.1.11')
            self.__hw = None
        else:
            raise IOError("Wrong configuration: not string or tuple detected, instead '{}'".format(type(config)))
        
        # Prepare threading system
        super(POSNotify, self).__init__()
        self.stoprequest = threading.Event()
        
        # Prepare messaging system
        self.__inmsg = inmsg
        self.__outmsg = outmsg
    
    @staticmethod
    def got_cid(struct):
        # print("GOT CID: {}".format(struct))
        pass
    
    def run(self):
        self.debug("Starting", color='blue')
        try:
            
            # Monitor for new cards
            cardtype = AnyCardType()
            try:
                cardrequest = CardRequest( timeout=1.5, cardType=cardtype )
                cardmonitor = CardMonitor()
                cardobserver = DNIeObserver( self.got_cid )
                self.debug("Connecting observer", color='yellow')
                cardmonitor.addObserver( cardobserver )
            except Exception as e:
                self.error("No smartcard reader detected... (ERROR: {})".format(e))
                cardobserver=None
                cardmonitor=None
            
            while not self.stoprequest.isSet():
                try:
                    request = self.__inmsg.get(True, 0.05)
                except queue.Empty:
                    request = None
                
                if request is not None:
                    self.debug("IN msg: {}".format(request), color='cyan')
                    if request == 'DNIE':
                        self.__outmsg.put("Notify DNIE {}".format(datetime.datetime.now()))
                    else:
                        self.__outmsg.put("{}: {}?".format(datetime.datetime.now(), request))
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
            self.debug("Finishing")
            
            # Remove the observer, or the monitor will poll forever
            self.debug("Disconnecting observer", color='yellow')
            if cardmonitor and cardobserver:
                cardmonitor.deleteObserver(cardobserver)
        except KeyboardInterrupt:
            self.warning("Closed by user request")
        except Exception as e:
            self.error("ERROR: {}".format(e))


    def join(self, timeout=None):
        self.stoprequest.set()
        super(POSNotify, self).join(timeout)

