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
    DeviceType,
    ALARM_TYPES,
    AUTO_TYPES,
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


class Server:
    def __init__(self, host=HOST_CENTRAL, port=PORT_CENTRAL):
        self.host = host
        self.port = port
        self.max_queue_size = 10

        self.devices = self.get_registered_devices()

        logging.basicConfig(
            level=logging.INFO,
            format="[%(levelname)s] %(asctime)s: %(message)s",
        )
        self.logger = logging.getLogger('fse_server')

    async def states_handler(self, writer, reader, states_queue):
        def decode_states(states):
            return [s == '1' for s in f'{states:064b}']

        while True:
            states_struct = struct.Struct('<BQff')

            try:
                payload = await reader.readexactly(states_struct.size)
            except asyncio.IncompleteReadError:
                host, port, *_ = writer.get_extra_info('peername')

                self.logger.error(
                    "Probably %s:%s was interrupted. Dropping connection..",
                    host, port
                )

                raise asyncio.CancelledError

            device_type, states, temperature, umidity = states_struct.unpack(payload)
            device_type = DeviceType(device_type)

            if device_type in ALARM_TYPES:
                await play_alarm()

            states = decode_states(states)
            await states_queue.put((device_type, states, temperature, umidity))

    def devices_to_commands(self, selected_devices):
        'Returns one command by type'
        # states = {d.type: 0 for d in self.devices}
        states = {d.type: 0 for d in self.devices if d.type not in AUTO_TYPES}

        for device in selected_devices:
            if device.type in AUTO_TYPES:
                continue

            states[device.type] |= 1 << device.id

        commands = [
            struct.pack('<BQ', t.value, s)
            for t, s in states.items()
        ]

        # TODO: Add AUTO commands
        # commands += []

        return commands

    async def get_user_commands(self, gui_commands_queue):
        selected_devices = await gui_commands_queue.get()

        if selected_devices is None:
            return selected_devices

        commands = self.devices_to_commands(selected_devices)

        return commands

    async def commands_handler(self, writer, gui_commands_queue):
        while True:
            commands = await self.get_user_commands(gui_commands_queue)

            if commands is None:
                break

            for command in commands:
                writer.write(command)

            await writer.drain()

    @staticmethod
    def get_registered_devices():
        # Also could not be just static
        return [
            # Manually activables
            Device('Lâmpada 01 (Cozinha)', DeviceType.LAMP),
            Device('Lâmpada 02 (Sala)', DeviceType.LAMP),
            Device('Lâmpada 03 (Quarto 01)', DeviceType.LAMP),
            Device('Lâmpada 04 (Quarto 02)', DeviceType.LAMP),
            Device('Ar-Condicionado 01 (Quarto 01)', DeviceType.AIR_CONDITIONING),
            Device('Ar-Condicionado 02 (Quarto 02)', DeviceType.AIR_CONDITIONING),
            Device('Temperatura automática', DeviceType.AIR_CONDITIONING_AUTO),

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

    async def connection_handler(self, reader, writer):
        host, port, *_ = writer.get_extra_info('peername')

        # Exclusive connection for pushing commands
        #   maybe could be the same server connection, but this is more resistant
        #   to protocol changes
        _, push_writer = await asyncio.open_connection(host, PORT_DISTRIBUTED)

        self.logger.info("Connected to %s:%s", host, port)

        states_queue = asyncio.Queue(self.max_queue_size)
        gui_commands_queue = asyncio.Queue(self.max_queue_size)

        gui = Gui(self.devices, states_queue, gui_commands_queue)

        tasks = asyncio.gather(
            gui.start(),
            self.commands_handler(push_writer, gui_commands_queue),
            self.states_handler(writer, reader, states_queue),
        )

        try:
            await tasks
        except asyncio.CancelledError:
            tasks.cancel()
            gui.stop()

        try:
            await tasks
        except asyncio.CancelledError:
            ...
        finally:
            writer.close()
            await writer.wait_closed()

            self.logger.info("Closed connection to %s:%s", host, port)

    async def start(self):
        server = await asyncio.start_server(
            self.connection_handler,
            self.host, self.port
        )

        host, port, *_ = server.sockets[0].getsockname()
        self.logger.info('Waiting for connections on %s:%s ...', host, port)

        async with server:
            await server.serve_forever()


if __name__ == '__main__':
    server = Server()

    try:
        asyncio.run(server.start())
    except KeyboardInterrupt:
        logging.info("Server interrupted. Finishing...")
    finally:
        logging.info("Server Finished")
