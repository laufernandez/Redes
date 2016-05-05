#!/usr/bin/env python
# encoding: utf-8
# Revisión 2014 Carlos Bederián
# Revisión 2011 Nicolás Wolovick
# Copyright 2008-2010 Natalia Bidart y Daniel Moisset
# $Id: server.py 656 2013-03-18 23:49:11Z bc $

import optparse
import socket
import connection
from constants import *
import select


class AsyncServer(object):
    """
    Server multicliente que atiende un numero prefijado de clientes.

    Multiplexa con la llamada a sistema poll() entre diferentes
    conexiones pero siempre en un mismo proceso.
    """

    def __init__(self, addr=DEFAULT_ADDR, port=DEFAULT_PORT,
                 directory=DEFAULT_DIR):
        """
        Setea y configura el socket server y sus atributos.
        """
        print "Serving %s on %s:%s." % (directory, addr, port)
        self.directory = directory
        # Se crea el socket y se configura para poder reutilizarse
        # inmediatamente luego de una desconexión.
        self.socket_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Las llamadas a send y recv ahora no seran bloqueantes
        self.socket_server.setblocking(0)
        self.socket_server.setsockopt(
                                    socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # El server escucha sobre puerto y addr esperando un cliente
        self.socket_server.bind((addr, port))
        self.socket_server.listen(NUM_CLIENTS)

    def serve(self):
        """
        Loop principal del servidor.

        Acepta 'NUM_CLIENTS' conexiones simultaneas.

        Atiende los pedidos de cada una simulando paralelismo.
        """
        # Se crea el objeto poll
        poll = select.poll()
        # Se registra al servidor 'sensible' a eventos POLLIN
        poll.register(self.socket_server, select.POLLIN)
        # Se crea un diccionario de clientes
        clients = {}
        # Loop principal
        while True:
            try:
                # Se llama al metodo poll() (bloq. mientras espera un evento)
                # Devuelve el polling set sobre el cual se itera atendiendo
                # los pedidos de multiples clientes (concurrentemente')
                events = poll.poll()
                # Se recorre la lista de eventos
                for fileno, event in events:
                    # Si el evento ocurre en el servidor
                    if fileno == self.socket_server.fileno():
                        # Un cliente quiere conectarse -> 'Salta' un POLLIN
                        if event & select.POLLIN:
                            # Se crea y configura socket cliente
                            s_client, addr = self.socket_server.accept()
                            s_client.setblocking(0)
                            # Se crea una conexion con el cliente
                            client_connection = connection.Connection(
                                                s_client, self.directory)
                            # Se registra el cliente al objeto poll
                            # A esta altura el cliente no realizó pedidos
                            # No hace falta registrarlo 'sensible' a POLLOUT
                            poll.register(s_client.fileno(), select.POLLIN)
                            print str(addr) + ' is now connected.'
                            # Se agrega el cliente al diccionario
                            clients[s_client.fileno()] = client_connection
                    # El evento ocurre en un cliente
                    else:
                        client = clients[fileno]
                        # La conexion esta estable
                        if not client.remove:
                            # Un cliente envia un pedido -> 'Salta' un POLLIN
                            if event & select.POLLIN:
                                # La llamada a handle_in() maneja los pedidos
                                client.handle_input()
                                # Ahora el cliente puede ser sensible a POLLOUT
                                # si espera una respuesta a un pedido procesado
                                client_event = client.events()
                                poll.modify(fileno, client_event)
                            # Llega la resp a un pedido de cliente -> POLLOUT
                            elif event & select.POLLOUT:
                                # La llamada a handle_out() maneja las resp
                                client.handle_output()
                                # Si la resp se envió completamente -> POLLIN
                                # para atender futuros request
                                # Caso contrario POLLOUT para completar la resp
                                client_event = client.events()
                                poll.modify(fileno, client_event)

                        # El flag remove puede ser True por dos motivos:
                        # - Errores 1xx -> Se envia el mensaje correspondiente
                        # - El cliente hizo un quit -> Se envia un CODE_OK
                        # En ambos casos luego del mensaje -> cerrar conexion
                        elif event & select.POLLOUT:
                            # Se llama a handle_out() que envia el mensaje
                            client.handle_output()
                            # Se quita al cliente del registro
                            poll.unregister(fileno)
                            # Se elimina su entrada en el diccionario
                            del clients[fileno]
                            # Se cierra la conexion
                            client.socket.close()

            except socket.error:  # Ante un socket.error el server no se cae.
                print 'Connection Error!'


def main():
    """Parsea los argumentos y lanza el server"""

    parser = optparse.OptionParser()
    parser.add_option(
        "-p", "--port",
        help=u"Número de puerto TCP donde escuchar", default=DEFAULT_PORT)
    parser.add_option(
        "-a", "--address",
        help=u"Dirección donde escuchar", default=DEFAULT_ADDR)
    parser.add_option(
        "-d", "--datadir",
        help=u"Directorio compartido", default=DEFAULT_DIR)

    options, args = parser.parse_args()
    if len(args) > 0:
        parser.print_help()
        sys.exit(1)
    try:
        port = int(options.port)
    except ValueError:
        sys.stderr.write(
            "Numero de puerto invalido: %s\n" % repr(options.port))
        parser.print_help()
        sys.exit(1)

    server = AsyncServer(options.address, port, options.datadir)
    server.serve()

if __name__ == '__main__':
    main()
