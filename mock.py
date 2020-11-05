#!/bin/python3

import random
import threading
import socket
from time import sleep
from struct import Struct
from enum import Enum


HOST_CENTRAL = ''
PORT_CENTRAL = 10008

PORT_DISTRIBUTED = 10108

CommandType = Enum('CommandType', 'ON OFF AUTO')


def states_handler():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST_CENTRAL, PORT_CENTRAL))

        while True:
            sleep(1)
            s.send(b'1')
            print('estados atualizados')


def commands_handler(conn):
    while True:
        command = conn.recv(4)

        type_ = int.from_bytes(command, 'little')
        type_ = CommandType(type_)

        if type_ == CommandType.AUTO:
            value = conn.recv(4)
            value, *_ = Struct('f').unpack(value)

            print(f'comando = {type_!s}, temperatura = {value}')

        print(f'comando = {type_!s}')


def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', PORT_DISTRIBUTED))
        s.listen()

        threading.Thread(target=states_handler, daemon=True).start()
        conn, addr = s.accept()

        with conn:
            commands_handler(conn)

if __name__ == '__main__':
    main()
