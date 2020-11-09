#!/bin/python3

import os
import asyncio
import signal
import logging
import random
import struct
import time
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

    def __init__(self, name, type_, passive=True):
        type_ = DeviceType(type_)

        self.name = name
        self.type = type_
        self.passive = passive

        self.id = Device.id_counters[self.type]
        Device.id_counters[self.type] += 1


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

    @staticmethod
    def decode_states(states):
        return [s == '1' for s in f'{states:064b}']

    async def states_handler(self, writer, reader, states_queue, csv_log):
        while True:
            states_struct = struct.Struct('>BQff')

            try:
                payload = await reader.readexactly(states_struct.size)
            except asyncio.IncompleteReadError:
                host, port, *_ = writer.get_extra_info('peername')

                self.logger.error(
                    "Probably %s:%s was interrupted. Dropping connection..",
                    host, port
                )

                raise asyncio.CancelledError

            device_type, states, temperature, humidity = states_struct.unpack(payload)
            device_type = DeviceType(device_type)

            decoded_states = self.decode_states(states)

            if device_type in ALARM_TYPES and any(decoded_states):
                # May delay execution if disk is slow
                with open(csv_log, 'a') as f:
                    f.write(f'{device_type},{states:064b},True\n')

                await self.play_alarm()

            await states_queue.put((device_type, decoded_states, temperature, humidity))

    async def play_alarm(self):
        alarm_file = 'alarm.mp3'

        path = os.path.dirname(os.path.abspath(__file__))
        path = os.path.dirname(path)
        path = os.path.join(path, alarm_file)

        await asyncio.create_subprocess_shell(
            f'omxplayer {path}',
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL
        )

    def devices_to_commands(self, selected_devices, csv_log):
        'Returns one command by type'
        # states = {d.type: 0 for d in self.devices}
        states = {d.type: 0 for d in self.devices if d.type not in AUTO_TYPES}

        for device in selected_devices:
            if device.type in AUTO_TYPES:
                continue

            states[device.type] |= 1 << device.id

        for type_, type_states in states.items():
            # May delay execution if disk is slow
            with open(csv_log, 'a') as f:
                f.write(f'{type_},{type_states:064b},False\n')


        commands = [
            struct.pack('>BQ', t.value, s)
            for t, s in states.items()
        ]


        # TODO: Add AUTO commands
        # commands += []

        return commands

    async def get_user_commands(self, gui_commands_queue, csv_log):
        selected_devices = await gui_commands_queue.get()

        if selected_devices is None:
            return selected_devices

        commands = self.devices_to_commands(selected_devices, csv_log)

        return commands

    async def commands_handler(self, writer, gui_commands_queue, csv_log):
        while True:
            commands = await self.get_user_commands(gui_commands_queue, csv_log)

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
            Device('Lâmpada 01 (Cozinha)', DeviceType.LAMP, False),
            Device('Lâmpada 02 (Sala)', DeviceType.LAMP, False),
            Device('Lâmpada 03 (Quarto 01)', DeviceType.LAMP, False),
            Device('Lâmpada 04 (Quarto 02)', DeviceType.LAMP, False),
            Device('Ar-Condicionado 01 (Quarto 01)', DeviceType.AIR_CONDITIONING, False),
            Device('Ar-Condicionado 02 (Quarto 02)', DeviceType.AIR_CONDITIONING, False),

            # Passives
            Device('Sensor de Presença 01 (Sala)', DeviceType.SENSOR_PRESENCE),
            Device('Sensor de Presença 02 (Cozinha)', DeviceType.SENSOR_PRESENCE),
            Device('Sensor Abertura 01 (Porta Cozinha)', DeviceType.SENSOR_OPENNING),
            Device('Sensor Abertura 02 (Janela Cozinha)', DeviceType.SENSOR_OPENNING),
            Device('Sensor Abertura 03 (Porta Sala)', DeviceType.SENSOR_OPENNING),
            Device('Sensor Abertura 04 (Janela Sala)', DeviceType.SENSOR_OPENNING),
            Device('Sensor Abertura 05 (Janela Quarto 01)', DeviceType.SENSOR_OPENNING),
            Device('Sensor Abertura 06 (Janela Quarto 02)', DeviceType.SENSOR_OPENNING),

            Device('Temperatura automática', DeviceType.AIR_CONDITIONING_AUTO, False),
        ]

    def get_csv_name(self, host, port):
        localtime = time.localtime()
        time_str = f'{localtime.tm_hour:02d}{localtime.tm_min:02d}{localtime.tm_sec:02d}'

        return f'{time_str}_{host}_{port}_log.csv'

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

        csv_log = self.get_csv_name(host, port)

        with open(csv_log, 'w') as f:
            f.write(f'device type,states,is_alarm\n')

        tasks = asyncio.gather(
            gui.start(),
            self.commands_handler(push_writer, gui_commands_queue, csv_log),
            self.states_handler(writer, reader, states_queue, csv_log),
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
