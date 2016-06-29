#!/usr/bin/env python
# encoding: utf-8

"""
Proxy reverso HTTP
Redes y Sistemas Distribuidos,
FaMAF, Univ. Nac. de Córdoba, Argentina, 2013.
"""
import sys
import logging

from proxy import Proxy

from config import *

if __name__ == '__main__':
    logging.basicConfig(level=getattr(logging, LOGLEVEL.upper()))
    p = Proxy(PORT, HOSTS)
    p.run()
