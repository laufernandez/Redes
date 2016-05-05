# encoding: utf-8
# Revisiones 2013-2014 Carlos Bederián
# Revisión 2011 Nicolás Wolovick
# Copyright 2008-2010 Natalia Bidart y Daniel Moisset
# $Id: constants.py 388 2011-03-22 14:20:06Z nicolasw $

DEFAULT_DIR = 'testdata'
DEFAULT_ADDR = 'localhost'
DEFAULT_PORT = 19500

EOL = '\r\n'
CR = '\n'
SP = ' '

CODE_OK = 0
BAD_EOL = 100
BAD_REQUEST = 101
INTERNAL_ERROR = 199
INVALID_COMMAND = 200
INVALID_ARGUMENTS = 201
FILE_NOT_FOUND = 202
BAD_OFFSET = 203

RECV_SIZE = 4096

MAX_READ_SIZE = 4096

NUM_CLIENTS = 5

COMMAND_LIST = ['get_file_listing', 'get_metadata', 'get_slice', 'quit']

QUIT_MESSAGE = "CONNECTION CLOSED"

error_messages = {

    CODE_OK: "OK",
    # 1xx: Errores fatales (no se pueden atender más pedidos)
    BAD_EOL: "BAD EOL",
    BAD_REQUEST: "BAD REQUEST",
    INTERNAL_ERROR: "INTERNAL SERVER ERROR",
    # 2xx: Errores no fatales (no se pudo atender este pedido)
    INVALID_COMMAND: "NO SUCH COMMAND",
    INVALID_ARGUMENTS: "INVALID ARGUMENTS FOR COMMAND",
    FILE_NOT_FOUND: "FILE NOT FOUND",
    BAD_OFFSET: "OFFSET EXCEEDS FILE SIZE",
}


def valid_status(s):
    return s in error_messages.keys()


def fatal_status(s):
    assert valid_status(s)
    return 100 <= s < 200


VALID_CHARS = set(".-_")
for i in xrange(ord('A'), ord('Z') + 1):
    VALID_CHARS.add(chr(i))
for i in xrange(ord('a'), ord('z') + 1):
    VALID_CHARS.add(chr(i))
for i in xrange(ord('0'), ord('9') + 1):
    VALID_CHARS.add(chr(i))
