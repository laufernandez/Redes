# encoding: utf-8
# $Rev: 512 $

import logging


class ProtocolError (Exception):
    """Excepción para indicar errores de parseo en mensajes"""

    def __init__(self, code, message):
        self.code = code
        self.message = message

SEPARATOR = '\r\n'
BAD_REQUEST = 400
UNKNOWN_VERSION = 505


class Queue(object):
    """
    Cola de transmisión abstracta. Maneja flujo de datos, y parseo de HTTP

    El campo 'data' se puede acceder públicamente y tiene el contenido de
    la cola.
    """

    def __init__(self):
        """Crear una cola vacía"""
        self.data = ''
        self.headers_finished = False
        self.headers = []

    def put(self, data):
        """Encolar data"""
        self.data += data

    def remove(self, count):
        """Eliminar count bytes del comienzo de la cola"""
        self.data = self.data[count:]

    def clear(self):
        """
        Vaciar el contenido de la cola. El contenido anterior se descarta.
        """
        self.data = ''

    def read_request_line(self):
        if SEPARATOR in self.data:
            line, self.data = self.data.split(SEPARATOR, 1)
            parts = line.split(' ')
            if len(parts) != 3:
                raise ProtocolError(
                    BAD_REQUEST,
                    "Invalid request line, should be <method> <url> <version>")
            method, url, protocol = parts
            if protocol not in ('HTTP/1.0', 'HTTP/1.1'):
                raise ProtocolError(
                    UNKNOWN_VERSION,
                    "Invalid/unknown HTTP version")
            return method, url, protocol
        else:
            return None, None, None

    def parse_headers(self):
        while SEPARATOR in self.data:
            if self.data.startswith(SEPARATOR):
                self.remove(len(SEPARATOR))
                self.headers_finished = True
                return True
            line, self.data = self.data.split(SEPARATOR, 1)
            if ':' not in line:
                raise ProtocolError(
                    BAD_REQUEST,
                    "Invalid header line (missing ':')")
            header = line.split(':', 1)
            self.headers.append(header)
        return False
