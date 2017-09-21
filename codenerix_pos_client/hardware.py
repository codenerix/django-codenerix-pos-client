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

import os
import re
import serial
import tempfile
import base64
from usb.core import USBError
from escpos.printer import Usb, Network, USBNotFoundError

# Smartcard libraries
from smartcard.CardMonitoring import CardMonitor
# from smartcard.CardType import AnyCardType
# from smartcard.CardRequest import CardRequest
# from smartcard.util import *

from lib.debugger import Debugger

from workers import POSWorker
from dnie import DNIeObserver


class POSWeightSerial(Debugger):

    ALLOWED_DEVICES = {
        'usb0': '/dev/ttyUSB0',
    }

    def __init__(self, config):

        # Prepare debugger
        self.set_name('POSWeightSerial')
        self.set_debug()

        # Get basic configuration
        if config is None:
            config = []
        elif isinstance(config, str):
            config = config.split(":")
        elif not isinstance(config, list):
            raise HardwareError("Unknow kind of configuration '{}', valid example: None, \"usb0\", [\"usb0\", 9600, \"8N1\"]".format(config))
        elif len(config) > 3:
            raise HardwareError("Configuration is too long '{}'".format(config))

        # Split configuration
        finalconfig = ['usb0', 9600, '8N1']
        if len(config) > 0:
            finalconfig[0] = config[0]
        if len(config) > 1:
            finalconfig[1] = config[1]
        if len(config) > 2:
            finalconfig[2] = config[2]
        if len(finalconfig[2]) != 3:
            raise HardwareError("Missing details in last parameter of configuration '{}' (lenght should be 3)".format(finalconfig[2]))

        # Prepare device, bauds, bytesize, parity and stopbits
        tdevice = finalconfig[0]
        bauds = finalconfig[1]
        bytesize = int(finalconfig[2][0])
        parity = finalconfig[2][1]
        stopbits = int(finalconfig[2][2])

        # Validate configuration
        device = self.ALLOWED_DEVICES.get(tdevice, None)
        if device is None:
            raise HardwareError("Device '{}' not in allowed devices list: {}".format(tdevice, ", ".join(self.ALLOWED_DEVICES.keys())))
        if bauds not in serial.Serial.BAUDRATES:
            raise HardwareError("Bauds '{}' not in allowed bauds list: {}".format(bauds, ", ".join([x for x in serial.Serial.BAUDRATES])))
        if bytesize not in serial.Serial.BYTESIZES:
            raise HardwareError("Bytesize '{}' not in allowed bytesize list: {}".format(bytesize, ", ".join([str(x) for x in serial.Serial.BYTESIZES])))
        if parity not in serial.Serial.PARITIES:
            raise HardwareError("Parity '{}' not in allowed parity list: {}".format(parity, ", ".join(serial.Serial.PARITIES)))
        if stopbits not in serial.Serial.STOPBITS:
            raise HardwareError("Stopbits '{}' not in allowed stopbits list: {}".format(stopbits, ", ".join([x for x in serial.Serial.STOPBITS])))

        # Save verified configuration
        self.__config = {
            'port': device,
            'baudrate': bauds,
            'bytesize': bytesize,
            'parity': parity,
            'stopbits': stopbits,
        }
        # Test config
        error = self.connect()
        if error:
            raise HardwareError("I couldn't connect to serial device: {} ({})".format(error, ", ".join(["{}={}".format(key, value) for (key, value) in self.__config.items()])))

    def connect(self):
        # Build the link
        error = None
        try:
            self.link = serial.Serial(**self.__config)
        except serial.serialutil.SerialException as e:
            error = e
            self.link = None

        if self.link:
            # Set up timeout
            self.link.timeout = 1

        return error

    def get(self):
        if not self.link:
            self.connect()

        if self.link:
            try:
                answer = self.link.read_all()
            except OSError as e:
                msg = "Couldn't read from bus: {}".format(e)
                self.error(msg)
                self.link = None
                raise HardwareError(msg)
        else:
            answer = None
        return answer


class POSWeight(POSWorker):
    module_name = "Weight System"

    def __init__(self, *args, **kwargs):
        # Normal initialization
        super(POSWeight, self).__init__(*args, **kwargs)

        # Remember last value
        self.__last_value = None

        # Check configuration
        protocol = self.config('protocol')
        config = self.config('config')
        if protocol == 'serial':
            # Configure connection
            self.__controller = POSWeightSerial(config)
        else:
            raise HardwareError("Device {} is requesting to use protocol '{}' but I only know 'serial'".format(self.uuid, protocol))

    def loop(self):
        # Check if we have messages waiting
        try:
            data = self.__controller.get()
        except HardwareError as e:
            self.send({'error': str(e)}, None)
            data = None

        # Check if there is something to work on
        if data:
            # Extract information
            try:
                value = data.decode('utf-8').split("\r")[-2].replace("\n", "").split(":")[1].strip()
                if value[0] == '-':
                    sign = -1
                else:
                    sign = 1
                unit = value[-1]
                number = sign * float(value[1:-1].strip())

                # Send weight change detected
                self.debug("Weight detected {}{}".format(number, unit), color='cyan')
                answer = {'weight': number, 'unit': unit}
                self.__last_value = answer
                self.send(answer, None)
            except Exception as e:
                try:
                    self.error("I got a wrong data from the bus: {}".format(e))
                except Exception:
                    self.error("I got a wrong data from the bus: NO PRINTABLE")

    def recv(self, msg, ref, uid=None):
        self.debug('Weight request from {}'.format(self.get_uuid(uid)), color='white')
        self.send(self.__last_value, ref, uid)


class POSTicketPrinter(POSWorker):
    module_name = "Ticket Printer"

    __EURO = '€'
    __CODE_EURO = "\x1b\x74\x13"  # chr(19)
    __CODE_EURO_CP = 'cp858'
    __CODE_NORMAL = "\x1b\x74\x12"  # chr(18)
    __CODE_NORMAL_CP = 'cp852'

    def __init__(self, *args, **kwargs):
        # Normal initialization
        super(POSTicketPrinter, self).__init__(*args, **kwargs)

        # Set basic configuration
        self.__image_format = "bitImageRaster"

        # Check configuration
        port = self.config('port')
        config = self.config('config')
        if port == 'usb':
            if isinstance(config, list) and len(config) >= 2 and len(config) <= 6 and isinstance(config[0], str) and isinstance(config[1], str):
                cfgkwargs = {}
                if len(config) == 6:
                    self.__image_format = config[5]
                if len(config) == 5:
                    if config[4] is not None:
                        cfgkwargs['out_ep'] = int(config[4], 16)
                if len(config) >= 4:
                    if config[3] is not None:
                        cfgkwargs['in_ep'] = int(config[3], 16)
                if len(config) >= 3:
                    if config[2] is not None:
                        cfgkwargs['timeout'] = config[2]
                self.__internal_config = ((int(config[0], 16), int(config[1], 16)), cfgkwargs)
            else:
                raise HardwareError("USB configuration must be a list with 2-5 elements (idVendor, idProduct, timeout, in_ep, out_ep)")
        elif port == 'ethernet':
            if isinstance(config, str):
                self.__internal_config = ((config, ), {})
            else:
                raise HardwareError("Ethernet configuration must be a string with an IP address")
        else:
            raise HardwareError("Port is not 'usb' or 'ethernet'")

    def get_printer(self):
        if self.config('port') == 'usb':
            dev = Usb
        else:
            dev = Network

        # Load configuration
        try:
            printer = dev(*self.__internal_config[0], **self.__internal_config[1])
        except USBError as e:
            printer = str(e)
        except USBNotFoundError as e:
            printer = str(e)

        return printer

    def render(self, template, ctx):

        # Initialize
        r = []

        # Split the document in pages
        pages = template.split("<({cut})>")
        first = True
        for page in pages:
            if not first:
                r.append(('cut', None))
            else:
                first = False

            elements = re.split(r"(<\(\{[a-z]+\}\)>?)", page)

            for element in elements:
                if len(element) > 6 and element[0:3] == '<({' and element[-3:] == '})>':
                    key = element[3:-3].strip()
                    config = ctx.get(key, None)
                    if isinstance(config, list):
                        (kind, value) = config
                        if kind in ['image', 'barcode']:
                            r.append((kind, value))
                        else:
                            self.warning("Found key '{}' wich kind I don't recognize, valid kinds are: image and barcode".format(key))
                    else:
                        self.warning("Found key '{}' in template with no matching in context".format(key))
                else:
                    r.append(('text', element))

        # Return final render
        return r

    def actions(self, data, printer):
        self.debug("Printing: {}".format(data), color='white')
        template = data.get('template', '')
        ctx = data.get('ctx', {})
        render = self.render(template, ctx)

        self.debug("Printing: {}".format(render), color='cyan')
        for (kind, data) in render:

            if kind == 'text':
                self.debug(data, color='cyan')

                # Support for euro character and several encoded characters
                datasp = data.split(self.__EURO)  # Euro symbol
                first = True
                for token in datasp:

                    # Show Euro symbol
                    if not first:
                        self.debug('    > EURO ({}, {})'.format(self.__CODE_EURO_CP, [self.__CODE_EURO]), color='simplecyan')
                        printer._raw(self.__CODE_EURO)
                        printer._raw(self.__EURO.encode(self.__CODE_EURO_CP, 'ignore'))
                    else:
                        first = False

                    # Print normal code
                    if token and token[-1] == "\n":
                        tokenclean = token[:-1]
                    else:
                        tokenclean = token
                    self.debug('    > NORMAL: {} ({}, {})'.format(tokenclean, self.__CODE_NORMAL_CP, [self.__CODE_NORMAL]), color='simplecyan')
                    printer._raw(self.__CODE_NORMAL)
                    printer._raw(token.encode(self.__CODE_NORMAL_CP, 'ignore'))

            elif kind == 'image':
                (tmpfile, tmpfilename) = tempfile.mkstemp(prefix='cdnx_pos_', suffix='.png')
                tmpfile = open(tmpfilename, 'wb')
                tmpfile.write(base64.b64decode(data))
                tmpfile.close()
                printer.image(tmpfilename, impl=self.__image_format)
                os.unlink(tmpfilename)

            elif kind == 'barcode':
                if 'code' in data:
                    code = data.get('code')
                    bc = data.get('bc', 'EAN13')
                    barkwargs = {}
                    for key in ['height', 'width', 'pos', 'font', 'align_ct', 'function_type']:
                        value = data.get(key, None)
                        if value is not None:
                            barkwargs[key] = value

                    # Print barcode
                    printer.barcode(code, bc, **barkwargs)
                else:
                    raise HardwareError("Missing CODE in barcode printing")

            elif kind == 'cut':
                self.debug('    > CUT', color='purple')
                printer.cut()

            else:
                self.error("Unknown action in printer. KIND={} - DATA:{}".format(kind, data))

    def recv(self, msg, ref, uid=None):
        data = msg.get('data', None)
        if data:
            printer = self.get_printer()
            if not isinstance(printer, str):
                self.actions(data, printer)
                answer = {'ack': True}
            else:
                answer = {'error': printer}
        else:
            answer = {'error': 'Nothing to print'}

        # Let's be polite and answer to the remote when the action is done
        self.send(answer, ref, uid)


class POSCashDrawer(POSTicketPrinter):
    module_name = "Cash Drawer"

    def actions(self, data, printer):
        self.debug('Open Cash Drawer', color='white')
        printer.cashdraw(2)


class POSDNIe(POSWorker):

    def __init__(self, *args, **kwargs):
        super(POSDNIe, self).__init__(*args, **kwargs)

    @property
    def DNIeHandler(self):
        def got_internal_cid(posworker, struct):

            # Get details
            cid = struct.get('id', None)
            # kind = struct.get('kind', None)
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

            # Build package
            if action == 'I':
                package = {'firstname': firstname.lower().title(), 'lastname': lastname.lower().title(), 'cid': cid, 'kind': 'DNIE'}
            else:
                package = {}

            # Send final package
            posworker.send(package, None)

        # End of wrapper
        return lambda struct: got_internal_cid(self, struct)

    def run(self, loop=True):
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

        # Sleep as usually
        if loop:
            super(POSDNIe, self).run()

        # Finish
        self.debug("Shutting down DNIe System", color='blue')

        # Remove the observer, or the monitor will poll forever
        if cardmonitor and cardobserver:
            cardmonitor.deleteObserver(cardobserver)

        # We are done
        self.debug("DNIe System is down", color='blue')

    def recv(self, msg, ref, uid=None):
        self.debug('DNIe request from {} (ref:{})'.format(self.get_uuid(uid), ref), color='white')
        self.run(loop=False)


class HardwareError(Exception):

    def __init__(self, string):
        self.string = string

    def __str__(self):
        return self.string
