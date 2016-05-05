Informe Laboratorio 2
==================

## Protocolo HFTP en Servidor Concurrente

---

### Objetivos:

> Aprender a menejar pedidos de múltiples clientes de forma concurrente. 

> Adaptar el servidor de HFTP para que acepte múltiples conexiones usando la primitiva de poll.

> Evaluar el diseño del servidor monocliente luego de la adaptación. 

> Entender de manera básica los problemas de escalabilidad que enfrenta un servidor.  


---

### Paso a Paso:

> Como primer paso, fué necesario comprender el uso de la primitiva **poll** como mecanismo para la paralelización del servidor HFTP.
La fuente principal que utilizamos fué la [documentación de python](https://docs.python.org/2/library/select.html#poll-objects).

> Comprendidos los conceptos, el siguiente paso sería la implementación de la clase AsyncServer. Definir sus atributos, configurarlos e implementar el metodo *serve()*, loop principal donde se multiplexa entre clientes.

> Una vez funcionando la paralelización, se debieron adaptar los métodos del módulo Connection para que se comporten de acuerdo a lo esperado. Siguiendo el diseño sugerido, el metodo *handle* se dividió en *handle_input* y *handle_output* encargados de la recepción de pedidos y el envio de respuestas desde y hacia cada cliente.

> A esta altura el servidor aceptaba múltiples conexiones, sin embargo, al testear, las respuestas no eran las esperadas. El servidor se rompía o los pedidos no se atendian concurrentemente. La solución fué repensar el metodo *handle_output* para que realice un envío por llamada y modificar el resto del código donde este método ejercía influencia. (Más detalles en Decisiones de Diseño)

> Se corrieron los tests sobre una primera versión estable del servidor y los resultados conllevaron a pequeñas modificaciones del código para atender los conflictos.

> Una vez superados los tests, tanto de la cátedra como testeo manual, el paso siguiente fue ordenar, renombrar variables, acomodar el estilo y tratar de adaptar el diseño lo más posible al sugerido por la cátedra.

> Por último una serie de revisiones y modificaciones para tener en cuenta todos los detalles. Cabe destacar el uso de una lista de iterables que permitiera ejecutar dos llamados a *get_slice* sin pisar sus resultados. (Ver Decisiones de Diseño)

> Finalmente pep8 sobre los archivos y la redacción del informe.


### Decisiones de Diseño:

#### Módulo AsyncServer: ####

> La clase Server pasa a llamarse *AsyncServer* acorde al proyecto.

> Se configuraron los sockets server y cliente para que las llamadas a recv y send sean no bloqueantes.

> El método *serve* sería el encargado de multiplexar entre las conexiones. Para esto, recorre una lista de eventos asociados con los sockets clientes o servidor y pregunta a que tipo de evento corresponde- Se diferencia entre eventos del servidor, y eventos de salida o entrada para el cliente. (Tiene en cuenta si el cliente pidió desconectarse y en caso afirmativo cierra su conexión).

#### Módulo Connection: ####

> Como adelantamos, se separa el manejo de los pedidos en dos.

> Un método *handle_input* encargado de recibir los pedidos y procesarlos y un método llamado *handle_output* que se encargaría de enviar las respuestas hacia el cliente.

> Para *handle_input* fueron necesarias las siguientes consideraciones:

> Los pedidos se evaluarían completos, es decir, todos los requests existentes en un único recv() serían procesados secuencialmente. Sus respuestas serían encoladas en el buffer de salida para luego ser manejadas por el método antes citado. Para requests incompletos, el siguiente llamado a handle_input concatenaría la información recibida y nuevamente se intentaría procesar.

> En el caso de las respuestas, como la idea del laboratorio era justamente simular concurrencia, fué necesario reimplementar el método encargado de ellas. *handle_output* se encargaría entonces de enviar las respuestas por partes, más precisamente de a un send() por llamada.   

> Esta modificacíon alteró el comportamiento de nuestro servidor arrojando ciertos errores que fueron analizados, comprendidos y solucionados. Uno de ellos, la explosión de un assert que chequeaba previo procesamiento de un comando, que el buffer de salida se encontrara vacío. Dicha restricción era válida en la implementación del servidor monocliente precisamente por el flujo de datos que allí ocurría (pedido -> request -> procesar request -> enviar respuesta).

> Para el caso del multicliente, el buffer de salida muy probablemente tuviera información previa a cada llamada de *handle_output*.    

> El assert fué entonces suspendido y ahora las respuestas de los comandos serían concatenadas a los buffers de salida asegurando así, no 'pisar' data previa. Un caso particular de esto fué la implementacíon o modificación de la respuesta de *get_slice*. Dos llamados a get_slice en el server monocliente eran atendidos correctamente, pero para el asyncserver, dos llamados consecutivos a la función, pisarían el iterable si éste último aún quedara con información para iterar.

> La solución vino de la mano de [*chain.from_iterable*](https://docs.python.org/3/library/itertools.html) que nos ayudó a concatenar dos o mas iterables en una lista y recorrerlos de principio a fin sin problemas.

> Por último, la implementación del método *events()* (siguiendo el diseño sugerido) que evaluaría la situación actual de la conexión y determinaría si el socket sería 'sensible'a eventos de tipo POLLIN o POLLOUT. (La evaluación se centró en el estado del buffer de salida.)


---

### Extras:

> Se creó una constante *NUM_CLIENTS* = 5, definida en el modulo Constans para determinar la cantidad máxima de clientes que un servidor podría escuchar al mismo tiempo.

> No fué necesario cambio alguno en el resto de los módulos.
---

### Integrantes:

* [Lucas Astrada]                  lucas_astrada11@hotmail.com
* [Miguel Roldan]                  miguee009@gmail.com
* [Lautaro Fernandez]              fernandezarticolautaro@gmail.com

---