#!/bin/python3

import asyncio
import signal
import logging
import random
import struct
from functools import partial
from typing import NamedTuple
from collections import defaultdict

from gui import Gui
from constants import (
    HOST_CENTRAL,
    PORT_CENTRAL,
    PORT_DISTRIBUTED,
    CommandType,
    DeviceType,
    ALARM_TYPES,
    AUTO_DEVICE_NAME,
)


class Device:
    # Idenfified by (device type, device id)
    id_counters = defaultdict(int)

    def __init__(self, name, type_):
        type_ = DeviceType(type_)

        self.name = name
        self.type = type_

        self.id = Device.id_counters[self.type]
        Device.id_counters[self.type] += 1


async def play_alarm():
    ...
    # print("ALARM!!!!")


def update_state(a, b):
    ...


async def states_handler(reader):
    while True:
        # TODO: Add temperature and umidity
        states_struct = struct.Struct('<BQ')

        payload = await reader.readexactly(states_struct.size)
        device_type, states = states_struct.unpack(payload)

        device_type = DeviceType(device_type)

        if device_type in ALARM_TYPES:
            await play_alarm()

        update_state(device_type, states)

def devices_to_commands(devices):
    'Returns one command by type'
    states = {d.type: 0 for d in devices}

    for device in devices:
        if device.name == AUTO_DEVICE_NAME:
            continue

        states[device.type] |= 1 << device.id

    commands = [
        struct.pack('<BBB', CommandType.ON_OR_OFF.value, t.value, s)
        for t, s in states.items()
    ]

    # TODO: Add AUTO commands
    # commands += []

    return commands


async def get_user_commands(gui_commands_queue):
    selected_devices = await gui_commands_queue.get()
    commands = devices_to_commands(selected_devices)

    return commands


async def commands_handler(writer, queue):
    while True:
        commands = await get_user_commands(queue)

        for command in commands:
            writer.write(command)

        await writer.drain()


def get_registered_devices():
    # For now, static
    return [
        # Manually activables
        Device('Lâmpada 01 (Cozinha)', DeviceType.LAMP),
        Device('Lâmpada 02 (Sala)', DeviceType.LAMP),
        Device('Lâmpada 03 (Quarto 01)', DeviceType.LAMP),
        Device('Lâmpada 04 (Quarto 02)', DeviceType.LAMP),
        Device('Ar-Condicionado 01 (Quarto 01)', DeviceType.AIR_CONDITIONING),
        Device('Ar-Condicionado 02 (Quarto 02)', DeviceType.AIR_CONDITIONING),
        Device(AUTO_DEVICE_NAME, DeviceType.AIR_CONDITIONING),

        # Passives #TODO: Differentiate on interface
        Device('Sensor de Presença 01 (Sala)', DeviceType.SENSOR_PRESENCE),
        Device('Sensor de Presença 02 (Cozinha)', DeviceType.SENSOR_PRESENCE),
        Device('Sensor Abertura 01 (Porta Cozinha)', DeviceType.SENSOR_OPENNING),
        Device('Sensor Abertura 02 (Janela Cozinha)', DeviceType.SENSOR_OPENNING),
        Device('Sensor Abertura 03 (Porta Sala)', DeviceType.SENSOR_OPENNING),
        Device('Sensor Abertura 04 (Janela Sala)', DeviceType.SENSOR_OPENNING),
        Device('Sensor Abertura 05 (Janela Quarto 01)', DeviceType.SENSOR_OPENNING),
        Device('Sensor Abertura 06 (Janela Quarto 02)', DeviceType.SENSOR_OPENNING),
    ]

async def connection_handler(reader, writer):
    host, port, *_ = writer.get_extra_info('peername')

    # Exclusive connection for pushing commands
    #   maybe could be the same server connection, but this is more resistant
    #   to protocol changes
    _, push_writer = await asyncio.open_connection(host, PORT_DISTRIBUTED)

    max_queue_size = 10
    states_queue = asyncio.Queue(max_queue_size)
    gui_commands_queue = asyncio.Queue(max_queue_size)

    devices = get_registered_devices()
    gui = Gui(devices, states_queue, gui_commands_queue)

    tasks = asyncio.gather(
        gui.start(),
        commands_handler(push_writer, gui_commands_queue),
        states_handler(reader),
    )

    try:
        await tasks
    except asyncio.CancelledError:
        tasks.cancel()

    try:
        await tasks
    except asyncio.CancelledError:
        ...
    finally:
        writer.close()
        await writer.wait_closed()

        logging.info("Closed connection to %s:%s", host, port)


async def main():
    server = await asyncio.start_server(connection_handler, HOST_CENTRAL, PORT_CENTRAL)

    host, port, *_ = server.sockets[0].getsockname()
    logging.info('Waiting for connections on %s:%s ...', host, port)

    async with server:
        await server.serve_forever()


if __name__ == '__main__':
    logging.getLogger().setLevel(logging.DEBUG)

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Server interrupted. Finishing...")
    finally:
        logging.info("Server Finished")
