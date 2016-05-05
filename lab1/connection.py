#!/usr/bin/env python
# encoding: utf-8
# Copyright 2014 Carlos Bederián
# $Id: connection.py 455 2011-05-01 00:32:09Z carlos $

import socket
from constants import *
from commands import *


class Connection(object):
    """
    Conexión punto a punto entre el servidor y un cliente.

    Se encarga de satisfacer los pedidos del cliente hasta
    que termina la conexión.
    """

    def __init__(self, socket, directory):
        self.socket = socket
        self.directory = directory
        self.buffer_in = ""
        self.buffer_out = ""
        self.connected = True
        self.iterable = None

    def handle(self):
        """
        Atiende eventos de la conexión hasta que termina.

        Separa los mensajes recibidos en requests y manda a procesar de a uno.

        Una vez procesado cada request la respuesta es enviada al cliente.
        """
        while self.connected:

            if EOL in self.buffer_in:
                request, self.buffer_in = self.buffer_in.split(EOL, 1)
                self.process_request(request)
                while True:
                    if len(self.buffer_out):  # Consume todo el buffer_out
                        sended_size = self.socket.send(self.buffer_out)
                        self.buffer_out = self.buffer_out[sended_size:]
                    # Si la respuesta viene de get_slice es necesario iterar
                    # y llenar el buffer_out en cada iteración.
                    elif self.iterable:
                        try:
                            self.buffer_out = self.iterable.next()
                        except StopIteration:  # Ultima iteración
                            self.iterable = None
                    else:  # Buffer vacío y no hay iterable -> Corta el send
                        break
            else:
                self.buffer_in = self.buffer_in + self.socket.recv(RECV_SIZE)
        self.socket.close()
        print 'Connection is closed.'

    def process_request(self, request):
        """
        Procesa cada request por separado analizando su validez.

        Si se trata de un comando válido, lo ejecuta.

        Caso contrario maneja el error acorde al protocolo.
        """
        assert not len(self.buffer_out)

        if CR in request:  # Busca \n suelto en un request.
            self.buffer_out = message_from_code(BAD_EOL)
            self.connected = False
        else:
            # Separa el request en argumentos dividiendo por los espacios.
            # El primer argumento de la lista será el comando.
            # El resto, si existen, serán los argumentos
            argv = request.split(SP)
            argc = len(argv)  # Cantidad de argumentos incluido el comando.
            command = argv[0]  # Renombre por comodidad.
            if argc == 1 and command == 'quit':
                # El comando es quit y no hay argumentos extras.
                self.buffer_out = quit()
                self.connected = False
            elif argc == 1 and command == 'get_file_listing':
                # El comando es get_file_listing y no hay argumentos extras.
                self.buffer_out = get_file_listing(self.directory)
            elif argc == 2 and command == 'get_metadata':
                # Comando get_metadata con un argumento como corresponde.
                # Luego la función chequea la forma del argumento.
                self.buffer_out = get_metadata(self.directory, argv[1])
            elif argc == 4 and command == 'get_slice':
                # El comando es get_slice y número de argumentos es correcto.
                # La función se encarga de las formas de dichos argumentos.
                self.iterable = get_slice(self.directory,
                                          argv[1], argv[2], argv[3])
            else:
                # El comando no existe, o el núm de argumentos para un comando
                # válido no es correcto.
                self.check_command_error(command)

    def check_command_error(self, command):
        """
        Cheque el tipo de error al procesar un comando.

        El error corresponde a un comando inválido o al uso incorrecto de los
        argumentos.
        """
        if command in COMMAND_LIST:
            self.buffer_out = message_from_code(INVALID_ARGUMENTS)
        else:
            self.buffer_out = message_from_code(INVALID_COMMAND)
