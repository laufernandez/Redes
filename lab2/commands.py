#!/usr/bin/env python
# encoding: utf-8

from os import listdir, stat
from os.path import join
from constants import *


def quit():
    """
    Envía un mensaje de éxito de cierre de conexión.
    """
    return str(CODE_OK)+" "+QUIT_MESSAGE+EOL


def get_file_listing(directory):
    """
    Lista el nombre de los archivos contenidos en un directorio.
    """
    try:
        filename_list = listdir(directory)
        buffer_out = message_from_code(CODE_OK)
        for filename in filename_list:
            buffer_out += filename + EOL
        buffer_out += EOL  # Fin del response acorde al protocolo.
    except:
        buffer_out = message_from_code(INTERNAL_ERROR)
    return buffer_out


def get_metadata(directory, filename):
    """
    Devuelve la longitud de un archivo en decimal.
    """
    try:
        validate_filename(filename)  # Chequea filenames válidos por seguridad.
        path = join(directory, filename)
        fd_size = stat(path).st_size
        buffer_out = message_from_code(CODE_OK) + SP + str(fd_size) + EOL
    except OSError:  # El archivo no existe.
        buffer_out = message_from_code(FILE_NOT_FOUND)
    except ValueError:  # Error de la forma de los argumentos.
        buffer_out = message_from_code(INVALID_ARGUMENTS)
    except IOError:
        buffer_out = message_from_code(INTERNAL_ERROR)
    finally:
        return buffer_out


def get_slice(directory, filename, offset, size):
    """
    Lee un archivo iterando sobre fragmentos de longitud máxima MAX_READ_SIZE.

    La suma de esos fragmentos corresponde a una porción del archivo desde una
    posicion offset, size bytes hacia adelante. La suma es el valor de retorno.

    Al realizar la lectura por fragmentos permite leer archivos muy grandes.
    """
    try:
        validate_filename(filename)
        path = join(directory, filename)
        offset, size = int(offset), int(size)  # Arg. incorrectos -> ValueError
        fd_size = stat(path).st_size
        if (offset + size <= fd_size):
            fd = open(path, "r")
            fd.seek(offset, 0)
            yield message_from_code(CODE_OK)  # Mensaje de OK!
            while size:  # Itera hasta agotar el size de lectura restante.
                # La long de lectura es la menor entre MAX_READ_SIZE y size.
                # El último fragmento leído es de long <= que size (restante).
                partial_size = MAX_READ_SIZE if MAX_READ_SIZE < size else size
                data_readed = fd.read(partial_size)  # Fragmento leído.
                size -= partial_size   # Actualiza la long de lectura restante.
                yield str(len(data_readed)) + SP + data_readed + EOL
            yield str(size) + SP + EOL  # Fin del response acorde al protocolo.
        else:
            yield message_from_code(BAD_OFFSET)
    except OverflowError:
        yield message_from_code(BAD_REQUEST)
    except OSError:
        yield message_from_code(FILE_NOT_FOUND)
    except ValueError:
        yield message_from_code(INVALID_ARGUMENTS)
    except:
        yield message_from_code(INTERNAL_ERROR)


def message_from_code(code):
    """
    Recibe un código de error y devuelve el mensaje correspondiente.
    """
    buffer_out = str(code) + SP + error_messages[code] + EOL
    return buffer_out


def validate_filename(filename):
    """
    Chequea la validez de los nombres de archivo caracter por caracter.

    Es una manera de limitar los filenames a nombres seguros.
    """
    for i in filename:
        if i not in VALID_CHARS:
            raise ValueError
