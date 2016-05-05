#!/usr/bin/env python
# encoding: utf-8
# Copyright 2014 Carlos Bederián
# $Id: connection.py 455 2011-05-01 00:32:09Z carlos $

import socket
from constants import *
from commands import *
from select import POLLIN, POLLOUT
from itertools import chain


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
        self.remove = False
        # Ahora tenemos una lista de iterables
        # La idea es que dos llamadas simultaneas a get_slice
        # no se pisen.
        self.iterables = []

    def events(self):
        """
        Evalua el estado de una conexion en cuanto a sus pedidos
        satisfechos o no.

        Si hay datos en el buffer de salida, es necesario enviarlos
        antes de recibir otro pedido (o cerrar la conexion).
        """
        # Hay datos en el buffer o falta iterar sobre la respuesta
        # a uno o mas get_slice's
        if self.buffer_out or self.iterables:
            return POLLOUT
        # Caso contrario, el cliente puede enviar nuevos pedidos
        else:
            return POLLIN

    def handle_output(self):
        """
        Se encarga de enviar las respuestas al cliente.

        Recorre el iterable si proviene de un get_slice.
        """
        if len(self.buffer_out):  # Consume todo el buffer_out
            sended_size = self.socket.send(self.buffer_out)
            self.buffer_out = self.buffer_out[sended_size:]
        # Si la respuesta viene de (uno o mas)get_slice es necesario
        # iterar y llenar el buffer_out en cada iteración.
        elif self.iterables:
            try:
                self.buffer_out = self.iterables.next()
            except StopIteration:  # Ultima iteración
                self.iterables = []

    def handle_input(self):
        """
        Se encarga de atender los pedidos del cliente y mandarlos
        a procesar.

        Divide en requests y los procesa secuencialmente.
        """
        # Recv que corresponde al 'salto' del evento POLLIN
        self.buffer_in = self.buffer_in + self.socket.recv(RECV_SIZE)
        # Separa y procesa
        while EOL in self.buffer_in:
            request, self.buffer_in = self.buffer_in.split(EOL, 1)
            self.process_request(request)

    def process_request(self, request):
        """
        Procesa cada request por separado analizando su validez.

        Si se trata de un comando válido, lo ejecuta.

        Caso contrario maneja el error acorde al protocolo.
        """

        if CR in request:  # Busca \n suelto en un request.
            self.buffer_out = message_from_code(BAD_EOL)
            self.remove = True
        else:
            # Separa el request en argumentos dividiendo por los espacios.
            # El primer argumento de la lista será el comando.
            # El resto, si existen, serán los argumentos
            argv = request.split(SP)
            argc = len(argv)  # Cantidad de argumentos incluido el comando.
            command = argv[0]  # Renombre por comodidad.
            if argc == 1 and command == 'quit':
                # El comando es quit y no hay argumentos extras.
                self.buffer_out += quit()
                self.remove = True
            elif argc == 1 and command == 'get_file_listing':
                # El comando es get_file_listing y no hay argumentos extras.
                self.buffer_out += get_file_listing(self.directory)
            elif argc == 2 and command == 'get_metadata':
                # Comando get_metadata con un argumento como corresponde.
                # Luego la función chequea la forma del argumento.
                self.buffer_out += get_metadata(self.directory, argv[1])
            elif argc == 4 and command == 'get_slice':
                # El comando es get_slice y número de argumentos es correcto.
                # La función se encarga de las formas de dichos argumentos.
                # Se concatenan distintos iterables en una lista.
                # Cada uno corresponde a una llamada a get_slice. De esta
                # maneram, dos llamadas simultaneas, (antes de ser respondidas)
                # no se pisan.
                self.iterables = chain.from_iterable(
                                        [self.iterables, get_slice(
                                            self.directory, argv[1], argv[2],
                                            argv[3])])

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
