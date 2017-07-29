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
from usb.core import USBError
from escpos.printer import Usb, Network, USBNotFoundError

# Smartcard libraries
from smartcard.CardMonitoring import CardMonitor
# from smartcard.CardType import AnyCardType
# from smartcard.CardRequest import CardRequest
# from smartcard.util import *

from workers import POSWorker
from dnie import DNIeObserver


class POSWeight(POSWorker):
    demo = True


class POSTicketPrinter(POSWorker):
    def __init__(self, *args, **kwargs):
        # Normal initialization
        super(POSTicketPrinter, self).__init__(*args, **kwargs)

        # Check configuration
        port = self.config('port')
        config = self.config('config')
        if port == 'usb':
            if isinstance(config, list) and len(config) == 2 and isinstance(config[0], str) and isinstance(config[1], str):
                self.__internal_config = (int(config[0], 16), int(config[1], 16))
            else:
                raise HardwareConfigError("USB configuration must be a list with 2 elements (idVendor, idProduct)")
        elif port == 'ethernet':
            if isinstance(config, str):
                self.__internal_config = (config, )
            else:
                raise HardwareConfigError("Ethernet configuration must be a string with an IP address")
        else:
            raise HardwareConfigError("Port is not 'usb' or 'ethernet'")

    def get_printer(self):
        if self.config('port') == 'usb':
            dev = Usb
        else:
            dev = Network

        # Load configuration
        try:
            printer = dev(*self.__internal_config)
        except USBError as e:
            printer = str(e)
        except USBNotFoundError as e:
            printer = str(e)

        return printer

    def actions(self, msg, printer):
        msg = msg.get('message', "???")
        printer.text("{}\n".format(msg))
        # self.__hw.barcode('1324354657687', 'EAN13', 64, 2, '', '')
        printer.cut()

    def recv(self, msg, uid=None):
        printer = self.get_printer()
        if not isinstance(printer, str):
            self.actions(msg, printer)
            answer = {'ack': True}
        else:
            answer = {'error': printer}

        # Let's be polite and answer to the remote when the action is done
        self.send(answer, uid)


class POSCashDrawer(POSTicketPrinter):

    def actions(self, msg, printer):
        printer.cashdraw(2)


class POSDNIe(POSWorker):

    @property
    def DNIeHandler(self):
        def got_internal_cid(posworker, struct):

            # Get details
            cid = struct.get('id', None)
            kind = struct.get('kind', None)
            action = struct.get('action', None)

            # Analize fullname
            fullnamedirty = struct.get('fullname', '')
            fullnamesp = fullnamedirty.split("(")[0].strip().split(",")
            if len(fullnamesp) == 2:
                firstname = fullnamesp[1].strip()
                lastname = fullnamesp[0].strip()
            elif len(fullnamesp) == 1:
                firstname = fullnamesp[0].strip()
                lastname = None
            else:
                firstname = None
                lastname = None

            # Answer
            if action == 'I':
                actiontxt = 'inserted'
            elif action == 'O':
                actiontxt = 'ejected'
            else:
                actiontxt = '???'
            self.debug("DNIe number {} was {}".format(cid, actiontxt), color='purple')
            posworker.send({'firstname': firstname, 'lastname': lastname, 'cid': cid, 'kind': kind, 'action': action})

        # End of wrapper
        return lambda struct: got_internal_cid(self, struct)

    def run(self):
        self.debug("Starting DNIe System", color='blue')

        # Monitor for new cards
        # cardtype = AnyCardType()
        try:
            # cardrequest = CardRequest( timeout=1.5, cardType=cardtype )
            cardmonitor = CardMonitor()
            cardobserver = DNIeObserver(self.DNIeHandler)
            self.debug("DNIe connecting observer", color='yellow')
            cardmonitor.addObserver(cardobserver)
        except Exception as e:
            self.error("No smartcard reader detected... (ERROR: {})".format(e))
            cardobserver = None
            cardmonitor = None

        while not self.stoprequest.isSet():
            # Sleep a second
            time.sleep(1)

        # Finish
        self.debug("Shutting down DNIe System", color='blue')

        # Remove the observer, or the monitor will poll forever
        if cardmonitor and cardobserver:
            cardmonitor.deleteObserver(cardobserver)

        # We are done
        self.debug("DNIe System is down", color='blue')

    def recv(self, msg, uid=None):
        printer = self.get_printer()
        if not isinstance(printer, str):
            self.actions(msg, printer)
            answer = {'ack': True}
        else:
            answer = {'error': printer}

        # Let's be polite and answer to the remote when the action is done
        self.send(answer, uid)


class HardwareConfigError(Exception):

    def __init__(self, string):
        self.string = string

    def __str__(self):
        return self.string
