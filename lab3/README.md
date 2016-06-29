Informe Laboratorio 3
===================

## Protocolo ARP para traducción de direcciones entre capas.

---

### Objetivos

> Implementar un protocolo de capas inferiores a la de aplicación.
> Aprender a trabajar sobre un protocolo binario. 
> Aprender a leer una especificación de protocolo real (como un RFC).

--- 

### Paso a paso

> La idea central del laboratorio, comprender e implementar el protocolo ARP, hizo necesario involucrarnos en el tema e investigar sobre su funcionamiento.

> Las fuentes principales fueron, por un lado la wikipedia para comprender a rasgos generales la idea del protocolo y sus variantes, y por el otro, el lado más técnico y mas formal, la [especificación](http://www.faqs.org/rfcs/rfc826.html) del mismo.

> Especificación mediante, se diseñaron las estructuras correspondientes a las tramas Ethernet y a los paquetes ARP. (Detalles en Decisiones de Diseño).

> El paso siguiente fué definir una estructura donde alojar las direcciones MAC relativas a cada IP de la red.

> Definidas las estructuras fué más sencillo comprender la idea de las dos funciones a implementar.

> Por un lado la funcion send_to_ip, se encargaría de enviar cierta cantidad de datos hacia una dirección MAC conocida, o caso contrario, se ensamblaría un paquete ARP que, difundido via *broadcast* alcanzaría todos los destinos de la red preguntando por la dirección MAC asociada a cierta IP. 

> Por el otro, receive_ethernet_packet manejaría el recibo de paquetes Ethernet, identificaría o clasificaría al mismo en datos o paquete ARP y en base a dicha clasificación, se encargaría de enviarlo a la capa de red o procesarlo (respectivamente).
> El procesamiento de un paquete ARP se encuentra descripto en la especificación del RFC826 en manera de pseudocódigo. Esa idea se sigue detalladamente en la implementación.

> Finalmente se testearon las funciones simulando una red con 6 hosts comunicándose entre sí a través del simulador de Omnet e intercambiando información. Se analizaron los resultados y se realizaron las modificaciones pertinentes.

---


### Decisiones de diseño

> Para la estructura de una trama Ethernet, se siguió el diseño sugerido por la catedra. El mismo cuenta con :
	* Dos campos de tipo *MACAddress* (array de 6 Bytes) correspondientes a las direcciones MAC (de origen y destino). 
	* Otro de 16 bits (siguiendo el estándar) para definir el tipo de protocolo encapsulado por el paquete.
	* Un último campo definido como la carga útil o *payload* de la trama, equivalente a un array de 1500 bytes de espacio para datos.

> La segunda estructura fué definida para contener los paquetes ARP. Siguiendo la especificación al pié de la letra, nos encontramos con que la misma debía conformarse por los siguientes 9 campos:
	* Dos enteros de 16 bits para especificar el espacio de direcciones correspondientes tanto al hardware (Ethernet por ejemplo) como al protocolo (IPv4).
	* Dos campos de 8 bits cada uno para especificar las longitudes correspondistes a dichos espacios de direcciones.
	* Un campo de 16 bits para determinar el código de la operación que utilizaba dicho paquete. (REPLY o REQUEST).
	* Un campo para la direccíon hardware origen cuyo tamaño quedaría definido por la constante *HRD_ADDR_SIZE*
	* Un campo definido como un array de *PROT_ADDR_SIZE* elementos para la dirección protocolo de origen.
	* Por último los equivalentes a las direcciones de hardware y protocolo *destino*.

> Se tomó la decisión de definir los campos para las direcciones de origen y destino de manera genérica para permitir el uso de la *estructura* en distintos dispositivos y bajo distintos protocolos. En principio alcanzaría con definir sus tamaños modificando los valores de las constantes antes mencionadas.

> Tanto para la estructura de la trama como para el paquete ARP, se hizo uso de *__attribute__((packed))* al momento de definirlas para asegurar que el compilador no altere el tamaño de las mismas en un intento por alinear la memoria.

> Una decisión no menor tuvo que ver con el diseño de la tabla que contendría las traducciones o asociaciones MAC-IP. Valiéndonos del hecho de que la red sería de tipo C (es decir un máximo de 256 hosts), utilizamos un arreglo de 256 elementos de tipo MACAddress indexados desde el 0 al 255 correspondiéndose dicho índice al valor del host en dicha red.
Luego, la búsqueda e inserción en la tabla son funciones constantes y el uso de memoria (si bién no es óptimo) es aceptable.
> La tabla de traducciones debía ser inicializada con direcciones MAC válidas pero neutrales, con un formato correcto pero cuyo valor no pudiera esta presente en ninguno de los hosts de la red. Se decidió inicializar cada elemento de la tabla con el valor definido para la difusión amplia o *broadcast*.

> De ésta manera, para averiguar si una direccíon MAC (asociada a cierta IP) era conocida, bastaba con encontrar el índice en la tabla para cierta (IP[3]) y comparar el valor alojado con la direccion de broadcast. Si eran iguales, debía ejecutarse el método ARP para resolución de direcciones. Caso contrario, se contaba con esa info.

> Un detalle muy importante a la hora de implementar las funciones *sent_to_ip* y *receive_ethernet_packet* fue la comprensión y el uso de funciones de conversión de [endianess](https://es.wikipedia.org/wiki/Endianness). Las redes deben comunicarse de manera homogénea de independiente a la arquitectura de los dispositivos. Por convención los datos en el protocolo Ethernet siguen el criterio de *Big Endian*. Por lo tanto, cada lectura desde un paquete de red debía adaptarse a la arquitectura de la máquina (funcion *ntohs*) y cada escritura en un paquete debería seguir las normas de la red. (htons convierte al B.E.).

> Para send_to_ip la idea era muy sencilla. Se revisaría la tabla de traducciones buscando cierta entrada correspondiente a cierta dirección MAC (destino) y se pasarían los datos a la capa de red como una trama Ethernet. En caso de desconocerse se armaría un paquete de tipo ARP y se alojaría en el payload de la trama reemplazando los datos que originalmente pensaban ser enviados.

> Para receive_ethernet_packet, se sigue firmemente el pseudocódigo definido en la especificación, inluídos los chequeos (redundantes) para el tamaño de las direcciones de hw y protocolo.


---

### Dificultades

> Encontramos ciertas dificultades a la hora de instalar y ejecutar Omnet en nuestras computadoras.

> Por otro lado, en un principio no comprendimos la idea del protocolo ni las estructuras (quizás demasiado genéricas sus definiciones en el RFC).

> Por último fué necesario hacer incapié con detalle en el uso de las conversiones de la Endiannes.

### Extras

#### Se definieron las siguientes constantes:
> IP_TYPE 0x0800 - EtherType para IPv4.

> ARP_TYPE 0x806 - EtherType para paquete ARP.

> ETHERNET_TYPE 0x0001 - ProtocolType para Ethernet.

> REQUEST_OP_CODE 0x0001 - Codigo de operacion para un ARPRequest.

> REPLY_OP_CODE 0x0002 - Codigo de operacion para un ARPReply.

> *static const MACAddress broadcast_addr = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF} - Direccion para la difusion amplia. 

---


### Integrantes:

* [Lucas Astrada]                  lucas_astrada11@hotmail.com
* [Miguel Roldan]                  miguee009@gmail.com
* [Lautaro Fernandez]              fernandezarticolautaro@gmail.com

---