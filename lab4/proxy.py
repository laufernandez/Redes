# encoding: utf-8
import socket
import select
import logging

from connection import Connection, DIR_READ, DIR_WRITE, RequestHandlerTask
from config import PORT
from random import choice


class Proxy(object):
    """Proxy HTTP"""

    def __init__(self, port, hosts):
        """
        Inicializar, escuchando en port, y sirviendo los hosts indicados en
        el mapa `hosts`
        """

        # Conexión maestra (entrante)
        master_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        master_socket.bind(('', port))
        logging.info("Listening on %d", port)
        master_socket.listen(5)
        self.host_map = hosts
        self.connections = []
        self.master_socket = master_socket
        # AGREGAR estado si lo necesitan

    def run(self):
        """Manejar datos de conexiones hasta que todas se cierren"""
        while True:
            self.handle_ready()  # Procesa
            p = self.polling_set()  # Objeto polleable
            # poll
            events = p.poll()  # Lista de eventos
            self.handle_events(events)  # Manejador de eventos
            self.remove_finished()  # Remueve las conexiones listas

            # COMPLETAR: Quitar conexiones que pidieron que las cierren
            #  - Tienen que tener el remove prendido
            #  - OJO: que pasa si la conexion tiene cosas todavía
            # en cola de salida?
            #  - Acordarse de usar el metodo close() de la conexion

    def polling_set(self):
        """
        Devuelve objeto polleable, con los eventos que corresponden a cada
        una de las conexiones.
        Si alguna conexión tiene procesamiento pendiente (que no requiera
        I/O), realiza ese procesamiento antes de poner la conexión en el
        conjunto.
        """
        # Que seria procesamiento pendiente que no requiera I/O???
        p = select.poll()
        # Registra el master sensible a eventos POLLIN
        p.register(self.master_socket.fileno(), select.POLLIN)
        # Itera sobre las conexiones
        for c in self.connections:
            # Registra segun corresponda
            if c.direction() == DIR_READ:  # Espera datos
                # Conexion registrada sensible a POLLIN
                p.register(c.fileno(), select.POLLIN)
            elif c.direction() == DIR_WRITE:
                # Registra la conexion sensible a POLLOUT
                p.register(c.fileno(), select.POLLOUT)
        return p

    def connection_with_fd(self, fd):
        """
        Devuelve la conexión con el descriptor fd
        """
        for c in self.connections:  # Itera
            if c.fileno() == fd:  # Chequea
                return c

    def handle_ready(self):
        """
        Hace procesamiento en las conexiones que tienen trabajo por hacer.
        Es decir, las que estan leyendo y tienen datos en la cola de entrada
        """
        for c in self.connections:
            # Hacer avanzar la maquinita de estados
            if c.input.data:
                c.task = c.task.apply(c)

    def handle_events(self, events):
        """
        Maneja eventos en las conexiones.
        events es una lista de pares (fd, evento)
        """
        for fileno, event in events:
            # El master solo es sensible a POLLIN
            if fileno == self.master_socket.fileno():
                # Un evento POLLIN es una nueva conexion
                self.accept_new()  # Acepta la nueva conexion
            else:  # No se trata del master
                # Traigo la conexion a partir del fd
                c = self.connection_with_fd(fileno)
                if event & select.POLLIN:
                    # Saltó un evento POLLIN -> Hay datos para leer
                    c.recv()
                elif event & select.POLLOUT:
                    # Evento POLLOUT -> Hay datos para enviar
                    c.send()
                elif event & select.POLLHUP:
                    # Se desconecto -> Marco la conexion para ser removida
                    c.remove = True
                    # run() llama a remove_finished y cierra la conexion

    def accept_new(self):
        """Acepta una nueva conexión"""
        socket, addr = self.master_socket.accept()  # Acepta
        c = Connection(socket, addr)  # Instancia Connection
        # La primera tarea de toda conexion es una instancia a RHT
        c.task = RequestHandlerTask(self)
        self.append(c)  # Agrega a la lista de conexiones

    def remove_finished(self):
        """
        Elimina conexiones marcadas para terminar
        """
        for c in self.connections:  # Itera
            if c.remove:  # Conexion marcada para remover
                while (c.direction() == DIR_WRITE):  # Tiene datos para enviar
                    c.send()  # Envia
                c.close()  # Cierra la conexion
                self.connections.remove(c)  # La quita de la lista

    def connect(self, hostname):
        """
        Establece una nueva conexion saliente al hostname dado. El
        hostname puede tener la forma host:puerto ; si se omite el
        :puerto se asume puerto 80.
        Aqui esta la unica llamada a connect() del sistema. No
        preocuparse por el caso de connect() bloqueante
        """
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # Parseo de host y puerto
        parts = hostname.split(':', 1)
        # No hay ':' -> Setea puerto 80
        if len(parts) == 1:
            port = PORT
            host = hostname
        # Se encontro un ':' -> Hay un puerto definido
        if len(parts) == 2:
            port = parts[0]
            host = parts[1]
        # Genera una conexion balanceada entre los ips del host
        ip_list = self.host_map[host]  # Traigo la lista de ips del host
        ip = choice(ip_list)  # IP aleatorio
        s.connect((ip, port))  # Conecta con ese IP
        c = Connection(s, host)  # Instancia de Conexion
        self.append(c)  # Agrega la conexion a la lista
        return c

    def append(self, c):
        self.connections.append(c)
