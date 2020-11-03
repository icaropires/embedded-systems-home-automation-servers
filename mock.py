#!/bin/python3

import random
import threading
import socket
import time


HOST_CENTRAL = ''
PORT_CENTRAL = 10008

PORT_DISTRIBUTED = 10108


def states_handle(conn):
    while True:
        conn.send(b'1')
        time.sleep(1)
        print('estado atualizado')


def activate_alarm():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST_CENTRAL, PORT_CENTRAL))

        while True:
            time.sleep(random.randint(3, 8))
            s.send(b'1')
            print('alarme disparado')


with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.bind(('', PORT_DISTRIBUTED))
    s.listen()

    threading.Thread(target=activate_alarm, daemon=True).start()
    conn, addr = s.accept()

    with conn:
        t_states = threading.Thread(target=states_handle, args=[conn])
        t_states.start()

        t_states.join()
