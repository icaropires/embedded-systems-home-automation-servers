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
DeviceType = Enum('DeviceType', 'SENSOR_OPENNING SENSOR_PRESENCE LAMP AIR_CONDITIONING')


def states_handler():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST_CENTRAL, PORT_CENTRAL))

        while True:
            # device_type = random.randint(1, len(DeviceType))
            # device_states = random.randint(0, 2**64-1)

            # Struct('<')

            sleep(1)
            s.send(b'1')
            print('estados atualizados')


def commands_handler(conn):
    while True:
        command = conn.recv(3)

        struct = Struct('<BBB')
        type_, device_type, device_id = struct.unpack(command)

        type_ = CommandType(type_)
        device_type = DeviceType(device_type)

        value = -1
        if type_ == CommandType.AUTO:
            value = conn.recv(4)
            value, *_ = Struct('f').unpack(value)

        print(f'comando = {type_!s}, device = {device_type}, device_id = {device_id}, temperatura = {value}')


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
