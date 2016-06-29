Informe Laboratorio 4
==================

## Un proxy HTTasTP

---
## Objetivos

> Realizar una implementación a nivel aplicación de un cliente y un servidor de un protocolo real
> Manejar pedidos y respuestas de forma concurrente.
> Afianzar conceptos adquiridos en los laboratorios anteriores.

---

## Paso a paso

> Como siempre, el primer paso fue involucrarnos en el tema. Lecturas en la web sobre el uso y funcionamiento de los proxys, junto con la explicacion de la catedra fueron suficientes para tener una idea general. No obstante para comprender la idea de la implementacion pedida, fue necesario releer varias veces el codigo esqueleto.

> Una vez comprendidas las bases, se comienza por implementar aquellas funciones que parecian en principio mas sencillas del modulo connection(direction, recv, send). Fue necesario tener mucho cuidado con el manejo de excepciones y tener en cuenta los casos particulares y los posibles errores.

> Comprendidas e implementadas las funciones sencillas, seguimos por la clase Forward y finalmente se implementa la clase HandleRequestTask, que sin dudas fue la funcion mas dificil.

> Con una primera base del modulo de las conexiones, el siguiente paso fue implementar las funciones de proxy.py, notablemente mas sencillas (Buena experiencia para manejar conexiones con Poll)

> Implementadas todas las funciones, llego la hora de testear. Modificamos el archivo /etc/hosts para redirigir a nuestro proxy a las paginas que figuraban en el diccionario de hosts del modulo config. Probamos ingresar a dichos hosts desde el navegador y debuggeamos con la consola y los mensajes de python.

> Paso a paso fueron quedando menos errores hasta que finalmente las paginas aparecian en el navegador. Si cerrabamos nuestro proxy, no podiamos acceder a esos mismos url => Nuestro proxy funcionaba

---

### Decisiones de diseño

> La decision de diseño mas importante tiene que ver ni mas ni menos con la clase HandleRequestTask.
Para esta clase fue muy complicado pensar en el parseo correcto de los datos.
En un princpio lo que se hace es leer la primera linea (request-line) y obtener de ella los valores del metodo, url y protocolo.
Una vez obtenidos (si los mismos son validos), utilizamos urlparse para obtener un objeto "parseado" de la url en cuestion. Dicho objeto cuenta con varios atributos. Uno de ellos, scheme, parsea el protocolo utilizado mientas que netloc en caso de no ser vacio y de haber pasado correctamente el protocolo, guarda el host.
Estos valores seran necesarios para evaluar un protocolo valido y un host explicito (Caso contrario ->Error 400)
El paso siguiente del parseo era atacar los encabezados.
El esqueleto provee una funcion que se encarga de ello.
Debiamos hacernos cargo, sin embargo, de buscar en la lista de encabezados si se encontraban HOST (obligatorio en http/1.0) y CONNECTION (para setear su valor en close y no permitir conexiones persistentes)
Se manejaron las exepciones correspondientes.
Una vez parseados y seteados los encabezados, se creo la conexion sin problemas y se genero un nuevo request con los valores actualizados (headers), este request viajaria (Forward) sin permitir conexiones persistentes.


> Para proxy, todos los casos fueron mas sencillos. El polling set era similar al laboratorio numero 2 al igual que handle_events().

> En connect, se diseño un parser sencillo para ubicar el puerto y host al cual conectarse y para generar el balanceo de conexiones, se decidió llamar a una funcion random sobre la lista de IP's asociados a un cierto host. De esta manera, a la larga (como todas las IP deberian tener probabilidades similares de caer luego de la llamada random.choice) las conexiones se encontrarian balanceadas o distribuidas correctamente entre todas esas IP's.


---

### Dificultades

> Fue de gran dificultad comprender en profundidad lo que debiamos implementar, sobre todo las clases Forward y HandleRequestTask y la idea de la maquina de estados.
La solucion fue diagramar el funcionamiento que deberia tener nuestro proxy y sobre eso pensar cada caso particular y asociarlo con las funciones del esqueleto.

> Fue necesario introducirse profundamente en el protocolo http con el fin de respetarlo a rajatabla.

> Otra gran dificultad surgió al no comprender en que momento debiamos setear remove a un remoto. Finalmente comprendimos que al realizar un recv igual a '', esto significaria que el remoto, al comprender que la conexion no era persistente se habria desconectado (Tanto el servidor como el navegador se ocuparian de desconectar. Luego, nosotros seguiriamos recibiendo hasta encontrarnos con ''.)

> Finalmente la falta de tiempo dedicado previo (mas que nada por parciales de otras materias) nos llevo a una entrega a destiempo y muy ajustada.

---

### Integrantes:

* [Lucas Astrada]                  lucas_astrada11@hotmail.com
* [Miguel Roldan]                  miguee009@gmail.com
* [Lautaro Fernandez]              fernandezarticolautaro@gmail.com

---