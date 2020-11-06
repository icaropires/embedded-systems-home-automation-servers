#!/bin/python3

import random
import threading
import socket
import struct
from time import sleep
from struct import Struct
from enum import Enum

HOST_CENTRAL = ''
PORT_CENTRAL = 10008

PORT_DISTRIBUTED = 10108

DeviceType = Enum(
    'DeviceType',
    'SENSOR_OPENNING SENSOR_PRESENCE LAMP AIR_CONDITIONING AIR_CONDITIONING_AUTO'
)

# Types which have automatic control
AUTO_TYPES = (DeviceType.AIR_CONDITIONING_AUTO,)


def states_handler():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST_CENTRAL, PORT_CENTRAL))

        while True:
            device_type = random.randint(1, len(DeviceType))
            device_states = random.randint(0, 2**64-1)

            states = struct.pack('<BQ', device_type, device_states)
            s.send(states)

            sleep(1)
            print('estados atualizados')


def commands_handler(conn):
    while True:
        command = conn.recv(1)

        device_type, *_ = struct.unpack('<B', command)
        device_type = DeviceType(device_type)

        if device_type not in AUTO_TYPES:
            command = conn.recv(8)
            states, *_ = struct.unpack('<Q', command)
            print(f'device_type = {device_type}\nstates = {states:064b}\n')
        else:
            # command = conn.recv(4)
            # value = struct.unpack('<f', command)
            value = -1
            print(f'device_type = {device_type}\ntemperatura = {value}\n')

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
