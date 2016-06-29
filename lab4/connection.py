# encoding: utf-8
# $Rev: 512 $

"""
Módulo que provee manejo de conexiones genéricas
"""

from socket import error as socket_error
from urlparse import urlparse  # Para el parseo del url
import logging
from config import HOSTS, PORT
from queue import Queue, ProtocolError, SEPARATOR, BAD_REQUEST


# Estados posibles de la conexion
DIR_READ = +1   # Hay que esperar que lleguen más datos
DIR_WRITE = -1  # Hay datos para enviar
# Longitud maxima de un receive
RECV_SIZE = 4096
# Codigos de error
HOST_ERROR = 403
INTERNAL_ERROR = 500


class Connection(object):
    """Abstracción de conexión. Maneja colas de entrada y salida de datos,
    y una funcion de estado (task). Maneja tambien el avance de la maquina de
    estados.
    """
    def __init__(self, fd, address=''):
        """Crea una conexión asociada al descriptor fd"""
        self.socket = fd
        self.task = None  # El estado de la maquina de estados
        self.input = Queue()
        self.output = Queue()
        # Esto se setea a true para pedir al proxy que desconecte
        self.remove = False
        self.address = address

    def fileno(self):
        """
        Número de descriptor del socket asociado.
        Este metodo tiene que existir y llamarse así
        para poder pasar instancias
        de esta clase a select.poll()
        """
        return self.socket.fileno()

    def direction(self):
        """
        Modo de la conexión, devuelve uno de las constantes DIR_*;
        también puede devolver None si el estado es el final
         y no hay datos para enviar.
        """
        # La cola de salida puede estar vacia por dos motivos:
        #   -1) Se enviaron todos los datos -> Remove es True
        #   -2) La cola de salida no esta lista AUN -> Sigue recibiendo
        if self.output.data == "":
            if self.remove:  # (1)
                return None  # El estado es el final
            else:  # (2)
                return DIR_READ  # Sigue recibiendo
        else:  # La cola de salida esta lista para enviarse
            return DIR_WRITE

    def recv(self):
        """
        Lee datos del socket y los pone en la cola de entrada.
        También maneja lo que pasa cuando el remoto se desconecta.
        Aqui va la unica llamada a recv() sobre sockets.
        """
        try:
            data = self.socket.recv(RECV_SIZE)  # Receive
            if data == "":  # El remoto se ha desconectado
                self.remove = True  # Hay que removerlo
            self.input.put(data)  # Encola los datos recibidos
        except socket_error:
            self.send_error(INTERNAL_ERROR, "Internal Error")
            self.remove = True

    def send(self):
        """Manda lo que se pueda de la cola de salida"""
        # Envia sended_size bytes
        sended_size = self.socket.send(self.output.data)
        # Elimina los datos enviados de la cola
        self.output.remove(sended_size)

    def close(self):
        """Cierra el socket. OJO que tambien hay que avisarle al proxy que nos
        borre.
        """
        self.socket.close()
        self.remove = True
        self.output.clear()

    def send_error(self, code, message):
        """Funcion auxiliar para mandar un mensaje de error"""
        logging.warning("Generating error response %s [%s]",
                        code, self.address)
        self.output.put("HTTP/1.1 %d %s\r\n" % (code, message))
        self.output.put("Content-Type: text/html\r\n")
        self.output.put("\r\n")
        self.output.put(
            "<body><h1>%d ERROR: %s</h1></body>\r\n" % (code, message))
        self.remove = True


class Forward(object):
    """Estado: todo lo que venga, lo retransmito a la conexión target"""
    def __init__(self, target):
        self.target = target

    def apply(self, connection):

        # La cola de entrada puede estar vacia por dos motivos:
        # -1) El remoto se ha desconectado (remove es True)
        # -2) El remoto no tiene mas datos para enviar
        # En ambos casos debe haber ocurrido un apply previo
        # que borra la cola de entrada (ultimo paso de apply)
        # Si la cola de entrada no esta vacia -> copio la cola de
        # entrada de connection tal cual llega en la salida de target

        if not connection.input.data:  # No hay que hacer nada
            return None
        else:  # Copia de connection a target
            self.target.output.put(connection.input.data)
            connection.input.clear()  # Vacia la cola de entrada
            return self  # Va a seguir retransmitiendo


class RequestHandlerTask(object):

    def __init__(self, proxy):
        self.proxy = proxy
        self.host = None
        # self.url = None

    def apply(self, connection):

        # Parsear lo que se vaya podiendo de self.input (utilizar los metodos
        # de Queue). Esto puede devolver
        # - None en caso de error, por ejemplo:
        #    * hubo un error de parseo
        #    * la url no empieza con http://
        #       (es decir, no manejamos este protocolo)
        #   (error 400 al cliente)
        #    * Falta un encabezado Host y la URL del pedido tampoco tiene host
        #   (error 400 al cliente)
        #    * Nos pidieron hacer proxy para algo
        #       que no esta en la configuracion
        #   (error 403 al cliente)
        # - Una instancia de Forward a una nueva conexion si se puede proxyar
        #    En este caso también hay que crear la conexion
        #    y avisarle al Proxy()
        try:
            # Lee el Request-Line y detecta errores de formato en el pedido.
            method, url, protocol = connection.input.read_request_line()
            if (method, url, protocol) == (None, None, None):  # No hay EOL
                return self  # Pedido aun incompleto

            # Parsea url para errores de host y protoloco invalidos
            url_parsed = urlparse(url)
            protocol_parsed = url_parsed.scheme
            host_parsed = url_parsed.netloc

            # read_request_line borra de la cola de entrada la linea de pedido
            # Lo que queda ahora en la cola de entrada pueden ser encabezados
            # Parseo de Headers
            if not connection.input.parse_headers():
                return self  # No se encuentra un EOL en lo que queda de pedido
            else:
                if connection.input.headers_finished:  # Parseo completo
                    # Recorre la lista de encabezados
                    for header in connection.input.headers:
                        if header[0] == 'Host':  # El encabezado es Host
                            # Copia el valor del mismo
                            self.host = header[1][1:]
                        if header[0] == 'Connection':  # La conexion
                            header[1] = 'close'  # Ahora es no persistente
                    if not self.host:  # No se encontro encabezado Host
                        # Para HTTP/1.1 es obligatorio tenerlo
                        if protocol == 'HTTP/1.1':
                            raise ProtocolError(
                                BAD_REQUEST,
                                "Header 'Host' not found")
                        # Si es HTTP/1.0 debe tenerlo en la url
                        if protocol_parsed != 'http' or not host_parsed:
                            # El protocolo esta mal formado
                            raise ProtocolError(
                                BAD_REQUEST,
                                "Error: Invalid Protocol or Host not found")
                        if host_parsed:
                            # El protocolo es correcto y la url tiene host
                            # Crea un nuevo encabezado Host con ese valor
                            connection.input.headers.append(
                                ['Host', host_parsed])
                            self.host = host_parsed  # Util para consultar (*)
                    if self.host not in HOSTS:
                        raise ProtocolError(
                                HOST_ERROR,
                                "Error: Invalid Host: " + self.host)

                else:  # Parseo incompleto
                    return self

            # Crea la conexion
            # Se conecta al host
            new_connection = self.proxy.connect(self.host)
            new_connection.task = Forward(connection)  # Nuevo estado

            # Retransmite el mensaje original con las modificaciones necesarias
            # Genera una nueva Request-Line
            new_connection.output.put(method + ' ')  # Metodo
            new_connection.output.put(url + ' ')  # Url
            new_connection.output.put(protocol + SEPARATOR)  # Protocolo y Fin
            # Agrega los Headers
            for header in connection.input.headers:  # Itero sobre los Headers
                new_connection.output.put(header[0] + ':' + header[1])
                new_connection.output.put(SEPARATOR)  # Header:Valor y EOL
            # Final de los Headers
            new_connection.output.put(SEPARATOR)

            # Devuelve una instancia de Fordward a la nueva conexion
            return Forward(new_connection)

        # Si ocurre una excepcion de protocolo, retorna None
        except ProtocolError as error:
            connection.send_error(error.code, error.message)
            return None
