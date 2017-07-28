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

from smartcard.CardMonitoring import CardObserver

####################################################################################
# [1] 00 A4 00 00 02 50 15   Seleccionamos el fichero raiz de la estructura.       #
#                            Responde SW1:0x61 indica que podemos leer con 0xC0    #
#                            GET_RESPONSE y Sw2: indica la longitud de lectura     #
#                                                                                  #
# [2] 00 A4 00 00 02 60 04   Seleccionamos el EF que contiene el CDF.              #
#                            Responde SW1:0x61 indica que podemos leer con 0xC0    #
#                            GET_RESPONSE y Sw2: indica la longitud de lectura     #
#                                                                                  #
# [3] 00 C0 00 00 LE   Comando get response para obtener el tamano del CDF.        #
#                      LE sera 1C casi seguro, aunque debe aparecer el resultado   #
#                      de SW2 del paso 2                                           #
#                      Responde LE bytes + SW1 y SW2 que deberian ser 0x9000 (OK)  #
#                      En esta respuesta buscar 6004 y los 2 siguientes bytes      #
#                      indican hasta donde podemos leer con la INS 0xB0            #
#                      Ejemplo xx xx xx xx xx 60 04 05 10 xx xx xx .... 90 00      #
#                      Nos quedamos con (0x05 y 0x10) para este ejemplo, la        #
#                      La longitud real que vamos a leer seria:                    #
#                                   (0x04 * 0xFF) + 0x10                           #
#                      para este caso.                                             #
#                                                                                  #
# [4] 00 B0 00 00 FF   Ejecutamos la INS 0xB0 hasta la longitud que era 0x0510     #
# [5] 00 B0 01 00 FF                                                               #
# [6] 00 B0 02 00 FF                                                               #
# [7] 00 B0 03 00 FF                                                               #
# [8] 00 B0 04 00 FF                                                               #
# ...                                                                              #
# [C] 00 B0 05 00 10                                                               #
#                                                                                  #
# Si responde alguna instruccion con 6D00 significa que la instruccion es invalida #
# o no esta soportada                                                              #
#                                                                                  #
#                                                                                  #
# [4] 00 B0 00 00 FF /* Recuperamos los primeros 0xFF bytes.                       #
# [5] 00 B0 01 00 FF /* Recuperamos los siguientes 0xFF bytes.                     #
# [6] 00 B0 02 00 FF /* ...                                                        #
# ... /* ...                                                                       #
# [C] 00 B0 NN 00 FF /* NN es el resultado de dividir la longitud de contenido     #
# del CDF entre 255. Dicha longitud se encuentra en la respuesta del comando       #
# [3], tras el identificador del fichero accedido, 6004.                           #
##################################################################################3#

class DNIeObserver( CardObserver ):

    def __init__( self , send_signature ):
        # List of cards connected
        self.__cards={}
        # Function to send the signature
        self.__send_signature=send_signature

    #def update( self, observable, (addedcards, removedcards) ):
    def update( self, observable, cards):
        ( addedcards, removedcards ) = cards
        # Struct
        outstruct={}
        outstruct['kind']='CID'
        # Inserted cards
        for card in addedcards:
            idcard=id(card)
            if idcard not in self.__cards.keys():
                # Define commands
                SELECT_ROOT=[0x00, 0xA4, 0x00, 0x00, 0x02, 0x50, 0x15]  # Seleccionamos el fichero raiz de la estructura
                SELECT_EF=[0x00, 0xA4, 0x00, 0x00, 0x02, 0x60, 0x04]    # Seleccionamos el EF que contiene el CDF
                GET_RESPONSE=[0x00, 0xC0, 0x00, 0x00, None]             # Comando get response para obtener el tamano del CDF (sw2 del comando anterior)
                GET_DATA=[0x00, 0xB0, None, 0x00, None]                 # Comando para recuperar los primeros 0xFF bytes (offset y cantidad bytes a leer)

                # Connect the card
                card.connection = card.createConnection()
                card.connection.connect()
                # Select root struct
                (response,sw1,sw2)=self.send(card.connection,SELECT_ROOT)
                # Select EF that contains CDF
                (response,sw1,sw2)=self.send(card.connection,SELECT_EF)
                # Get the size of CDF
                GET_RESPONSE[-1]=sw2
                (response,sw1,sw2)=self.send(card.connection,GET_RESPONSE)
                if response:
                    position=0
                    for r in response:
                        if position!=2 and r==0x60:
                            # Located first byte of 0x6004 secuence
                            position=1
                        elif position==1 and r==0x04:
                            # Located first and second byte of 0x6004 secuence
                            position=2
                        elif position==2:
                            # Recording block limit
                            block_limit=r
                            position=3
                        elif position==3:
                            # Recording line limit
                            line_limit=r
                            break
                    # Get data
                    result=''
                    if block_limit is not None:
                        for i in range(0x00,block_limit):
                            if i==block_limit:
                                GET_DATA[4]=line_limit
                            else:
                                GET_DATA[4]=0xFF
                            GET_DATA[2]=i
                            (response,sw1,sw2)=self.send(card.connection,GET_DATA)
                            for r in response:
                                result+=chr(r)
                    # Get data
                    cid=self.get_field(result,'55040513')
                    fullname=self.get_field(result,'5504030C')
                    print(fullname)
                    print(bytes(fullname,encoding='utf-8'))
                    # Build the internal structure
                    struct={}
                    struct['cid']=cid
                    struct['fullname']=fullname
                    # Save it in the class
                    self.__cards[idcard]=struct
                    # Build outstruct
                    outstruct['action']='I'
                    outstruct['id']=struct['cid']
                    # Send CID
                    self.__send_signature(outstruct)
                    # Show information
                    print("+ Card inserted: %s" % (struct))

        # Removed cards
        for card in removedcards:
            idcard=id(card)
            if idcard in self.__cards.keys():
                # Get the CID
                cid=self.__cards[idcard]['cid']
                # Forget the card
                self.__cards.pop( idcard )
                # Build outstruct
                outstruct['action']='O'
                outstruct['id']=cid
                # Send CID
                self.__send_signature(outstruct)
                # Show information
                print("- Card removed: %s" % (cid))

    def send(self,link,command):
        # Send command
        response, sw1, sw2 = link.transmit( command )
        if sw1 == 0x62 and sw2 == 0x83:
            raise IOError("WARN: Selected file invalidated")
        elif sw1 == 0x62 and sw2 == 0x84:
            raise IOError("WARN: FCI not formatted acording to section 5.1.5")
        elif sw1 == 0x6A and sw2 == 0x81:
            raise IOError("ERROR: Function not supported")
#        elif sw1 == 0x6A and sw2 == 0x82:
#            raise IOError("ERROR: File not found")
        elif sw1 == 0x6A and sw2 == 0x86:
            raise IOError("ERROR: incorrect parameter P1-P2")
        elif sw1 == 0x6A and sw2 == 0x87:
            raise IOError("ERROR: Lc inconsistent with P1-P2")
        else:
            return (response,sw1,sw2)

    def get_field(self,string,to_find):
        str_to_find=bytes.fromhex(to_find).decode('utf-8')
        index=string.find(str_to_find)
        index+=len(str_to_find)
        size=ord(string[index])
        return string[index+1:index+1+size]


