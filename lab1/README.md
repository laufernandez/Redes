
Informe Laboratorio 1
==================

## Protocolo HFTP en Servidor Secuencial

---

### Objetivos:

> Comprender, diseñar e implementar un programa servidor de archivos secuencial.

> Estudiar e implementar un protocolo.

> Aprender a usar las primitivas de sockets para crear servidores.

> Entender que las aplicaciones de red son agnósticas respecto a la arquitectura, el sistema operativo y el lenguaje de programación utilizados.

> Comprender la problemática de una aplicación servidor (funcionamiento permanente, robustez, tolerancia a fallas, seguridad, uso apropiado de los recursos), e implementar algunas de estas características.

---

### Paso a Paso:

> Como punto de partida para alcanzar los objetivos fue necesario investigar sobre el uso de sockets y sus primitivas. La fuente principal que utilizamos fue la [documentación de python](https://docs.python.org/2/library/socket.html). 

> Una vez comprendidos los principios básicos del uso de sockets en conexiones cliente-servidor, el paso siguiente fue analizar el código fuente provisto por la catedra para entender con qué herramientas contábamos y cúales eran necesarias implementar.

> El siguiente paso fué diseñar a gran escala como debía comportarse nuestro servidor sin tener en cuenta el protocolo sinó más bien enfocandonos solamente en la conexión. El servidor debía atender de a una conexión por turno y el método **handle** debía encargarse de manejar sus pedidos.

> Una vez creado y configurado el socket servidor, es puesto a escuchar sobre un puerto y una dirección especificadas. (Por defecto debía escuchar el puerto 19500 y la dirección de host local). 

> El servidor además debía contar con un método, **serve**, encargado de escuchar y aceptar solicitudes de clientes y crear una conexíon para atender sus peticiones.

> Era turno ahora de implementar el módulo **connection** donde debían definirse una clase con los atributos y métodos propios de una conexión. Como anticipamos, en esta altura los métodos solo se enfocaban en la conexión y no en las peticiones ni en los servicios que el servidor debía ofrecer.

> A esta altura los clientes establecían conexiones exitosas con el servidor. Era necesario pasar al siguiente nivel: descrifrar los pedidos de los clientes e implementar los comandos que responderían  a dichas solicitudes (**get_file_listing**, **get_metadata**, **get_slice** y **quit**). 
> Para esta etapa fué de gran utilidad nuevamente la documentación de python, especificamente las secciones [Input and Output](https://docs.python.org/2/tutorial/inputoutput.html), [Miscellaneous operating system interfaces](https://docs.python.org/2/library/os.html) y [Common pathname manipulations](https://docs.python.org/2/library/os.path.html)

> Finalmente una vez consolidados los comandos y los métodos de la conexíon, se puso incapié en la transmisión de los mensajes de respuesta siguiendo las reglas del protocolo.

> El paso siguiente fue modularizar el código y optimizar las funciones lo más que se pueda.
> Y finalmente una revisión linea por linea de codigo mejorando el estilo, la simplicidad, los nombres de variables, redundancias, comentarios y docstrings.

---

### Decisiones de Diseño:

> Una de las primeras decisiones fué sobre la necesidad de utilizar mecanismos de buffering tanto para el ingreso de solicitudes como para el egreso de respuestas.
>  Un **buffer_in** guardaría los mensajes recibidos del cliente y un **buffer_out** las respuestas que se debían enviar.

> Sin dudas la más significativa de las decisiones fué cómo iba a funcionar el método **handle** de una conexión.
>  Acordamos en la idea de leer los mensajes de clientes y atender secuencialmente las solicitudes, es decir, leer, procesar y responder, leer, procesar y responde y asi sucesivamente mientras queden pendientes.
La idea que se llevó a cabo divide la tarea en **4 pasos**:

>* 1) Recepción, y separación de los mensajes de clientes en **requests** tomando en cuenta como punto de división, la aparición del delimitador EOL. Mientras no se encontrara ninguno, la conexión debía seguir recibiendo mensajes.
La primera aparición de un EOL, dividiría al mensaje en dos (gracias a la función **split** de python). Por un lado la parte del mensaje anterior al EOL, que correspondería a un request de desconocida validez y por el otro, el resto del mensaje, con cuyo valor se actualizaría el buffer de entrada.

>* 2) Decodificación de cada **request** en comandos válidos o inválidos contemplando todos los posibles errores que podían aparecer. (i.e. comandos inválidos, argumentos inválidos, BAD_EOL, etc).
> La función encargada de esto fué **process_request** que tomando como argumento un pedido de cliente (derivado del primer split en handle), se encargaba de dividirlo según los espacios que encontrara en su interior y entendiendo cada parte como un argumento que irían a parar a una lista (**argv**). El primero siempre sería el "potencial comando" y a continuación podrían o no haber argumentos.

>* 3) Si el comando era válido, el mismo se ejecutaba y la respuesta se guardaba en el buffer de salida. Caso contrario se manejaba el error correspondiente con la función **command_error**.

>* 4) La respuesta (guardada en el buffer por **request_process**) debía ser enviada de vuelta hacia el cliente. En este punto, fué necesario implementar un mecanismo de vaciado del buffer_out para asegurar que el mensaje se envíe por completo.
> Un ciclo while enviaría al cliente siempre y cuando el buffer no este vacío, o en caso de estarlo, que no haya un objeto iterable sobre el cual seguir obteniendo datos. (Mas adelante abordaremos este caso particular que corresponde a una respuesta del comando **get_slice**).

> A la hora de implementar los comandos, la decisión en torno a la cual giraría nuestro diseño tendría que ver con alcanzar la mayor abstracción posible en la defición de las funciones. 
> Las funciones debían mantenerse totalmente independientes a la conexión. Sin sockets de por medio y sin buffers compartidos. Finalmente modularizamos esta sección del código con todos los métodos necesarios.

> En el comando **get_slice** teniendo en cuenta los requisitos pedidos, se utilizó la idea de **generadores** de python para realizar lecturas parciales de un archivo permitiendo entonces tratar con longitudes muy grandes (mayores a la capacidad RAM de nuestros servidores). 
> 
> La idea radica en lo siguiente, el servidor abre un archivo, se posiciona según el offser y lee de a un fragmento de tamaño **MAX_READ_SIZE** (prefijado desde el modulo de las constantes) siempre y cuando el tamaño pedido por el cliente (**size**) sea mayor a esta constante, paso siguiente resta MAX_READ_SIZE a size y vuelve a iterar hasta agotar size. Caso contrario, realiza una lectura de tamaño size.
El retorno de la función, haciendo uso de **yield**, devuelve un **objeto iterable** donde cada iteración corresponde a la lectura de un fragmento.
Este objeto se itera desde la función **handle** hasta el final y su contenido se guarda en el buffer de salida para ser enviado.

Leyendo fragmentos en el archivo:

```python
while size:
    partial_size = MAX_READ_SIZE if MAX_READ_SIZE < size else size
    data_readed = fd.read(partial_size)
    size -= partial_size
    yield str(len(data_readed)) + SP + data_readed + EOL
```

Recorriendo el objeto iterable:
```python
while True:
...
...
    elif self.iterable:
        try:
            self.buffer_out = self.iterable.next()
            except StopIteration:  # Ultima iteración
            self.iterable = None
    else:
        break
```

> Se implementaron además funciones auxiliares para el chequeo de filenames que podrían generar problemas en nuestro servidor (Solo es posible el uso de nombre con caracteres alfanumericos y los especiales ".", "-", y "_"), y para el manejo y formato de los mensajes de error. Estas son **validate_filename** y **message_from_code**.

---

### Extras:

> Para evitar la demora que significa esperar a que se libere la dirección luego de una desconexión del servidor, configuramos el socket server con la opción **SO_REUSEADDR**.

> Handle mantendría su ciclo siempre y cuando el cliente se encuentre conectado. Para su implementación se crea un atributo llamado **connected** utilizado como flag de estado de conexión. En el caso del flag en Falso, la conexión se cierra.

> El manejo de excepciones de python resultó de gran utilidad para tratar con los errores de tipo de argumento de los comandos, los archivos no existentes en el servidor, un offset que sobrepasa los límites, y la validez de los nombres de archivos así como también las iteraciones del comando get_slice y los posibles errores de sockets que pueden producirse durante la conexión.

> Se declararon constantes para fijar tamaños de lectura y recepcion máximos, lista de comandos válidos, mensaje de desconexión exitosa, el caracter '\n' y el espacio.

> Para unir los nombres de archivos con la dirección del directorio, utilizamos la función provista por python **os.path.join**.

---

### Implementación de los Comandos:

> `get_file_listing` debía listar los archivos de un directorio específico. Para su implementación se utilizó la función **listdir** que justamente recibiendo un directorio como argmumento devueve una lista de los archivos contenidos. Esta función no trajo mayores complicaciones que el manejo de los archivos inexistentes.
> La función **os.stat** nos devuelve una lista con los metadatos del archivo pasado como argumento entre los cuales se encuentra el tamaño del mismo.
> Fué necesario además contemplar las posibilidades de archivos inexistentes y nombres de archivos inválidos.

> `get_metadata` devolvería la longitud de un archivo especificado. Para su implementación, fue necesario ademas incorporar como argumento el directorio en el cual buscar el archivo. 
> La función **os.stat** nos devuelve una lista con los metadatos del archivo pasado como argumento entre los cuales se encuentra el tamaño del mismo.
> Fué necesario además contemplar las posibilidades de archivos inexistentes y nombres de archivos inválidos.

> `get_slice` fué sin dudas la función de mayor dificultad. Esta función debía devolver un fragmento leído de un archivo específico. El requisito pedía que el comando se llame junto a 3 argumentos, el primero, un nombre de archivo, el segundo el offset sobre el cual deberiamos posicionarnos en el archivo y el tercero, la dimensión del archivo a ser leída.  
>Se utilizaron funciones de apertura, posicionamiento y lectura de archivos provistas en el modulo **os** de python.
> Sin embargo la dificultad radicaba en un requisito extra del enunciado: el comando debía soportar archivos muy grandes. Como anticipamos, la lectura debía realizarse en fragmentos.
> Fué necesario entonces, [indagar](http://chernando.eu/python/python-generators/) sobre el uso de generadores en python y diseñar un mecanismo que permitiera, en caso de existir, recorrer un objeto iterable a fin de realizar lecturas parciales del archivo. 
> La solución fue agregar un atributo extra a la clase **Connection** llamado **iterable**, inicializado en el nulo correspondiente y en la función principal **handle** iterar sobre el mismo y llenar con su contenido el buffer previo a hacer un **send**.

> `quit`, la función más simple. Debía enviar un mensaje de éxito de fin de conexión y posterior a su invocación, se debía cerrar la conexión con el cliente.
> Como nuestra implementación debía ser abstracta a la conexión, la función simplemente retorna un mensaje con el formato adecuado y desde el lugar desde donde se llama a la misma se setea el flag **connected** a False. Como vimos anteriormente, si el flag es falso la conexión se cierra desde el handle.

---

### Integrantes:
>
* [Lucas Astrada]                  lucas_astrada11@hotmail.com
* [Miguel Roldan]                  miguee009@gmail.com
* [Lautaro Fernandez]        fernandezarticolautaro@gmail.com

---
