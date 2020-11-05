#!/bin/python3

import asyncio
import signal
import logging
import random
import struct
from functools import partial
from enum import Enum
from typing import NamedTuple


HOST_CENTRAL = ''
PORT_CENTRAL = 10008

PORT_DISTRIBUTED = 10108

CommandType = Enum('CommandType', 'ON OFF AUTO')
DeviceType = Enum('DeviceType', 'SENSOR_OPENNING SENSOR_PRESENCE LAMP AIR_CONDITIONING')

ALARM_TYPES = (DeviceType.SENSOR_OPENNING, DeviceType.SENSOR_PRESENCE)


class Command(NamedTuple):
    type_ : CommandType
    device_type : DeviceType
    device_id : int  # until 63
    value: float = -1  # Auxiliar for AUTO
    

async def play_alarm():
    print("ALARM!!!!")


async def states_handler(reader):
    while True:
        states_struct = struct.Struct('<BQ')

        payload = await reader.readexactly(states_struct.size)
        device_type, states = states_struct.unpack(payload)

        device_type = DeviceType(device_type)

        if device_type in ALARM_TYPES:
            await play_alarm()

        print(f'TIPO DE DISPOSITIVO: {device_type} <-> ESTADO RECEBIDO: {states:064b}')


async def commands_handler(writer, queue):
    while True:
        command = await queue.get()

        assert command.device_id <= 63, 'Invalid Device ID'

        command_args = list(command)
        command_args[0] = command.type_.value
        command_args[1] = command.device_type.value

        if command.type_ == CommandType.AUTO:
            command_bytes = struct.pack('<BBBf', *command_args)
        else:
            command_bytes = struct.pack('<BBB', *command_args[:-1])

        writer.write(command_bytes)
        print('COMANDO ENVIADO')
        await writer.drain()


async def connection_handler(reader, writer, commands_queue):
    host, port, *_ = writer.get_extra_info('peername')

    # Exclusive connection for pushing commands
    #   maybe could be the same server connection, but this is more resistant
    #   to protocol changes
    _, push_writer = await asyncio.open_connection(host, PORT_DISTRIBUTED)

    tasks = asyncio.gather(
        get_user_command(commands_queue),
        commands_handler(push_writer, commands_queue),

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


async def get_user_command(commands_queue):
    while True:
        await asyncio.sleep(random.randint(1, 5))

        type_ = CommandType(random.randint(1, len(CommandType)))
        device_type = DeviceType(random.randint(1, len(DeviceType)))
        device_id = random.randint(1, 63)

        value = -1
        if type_ == CommandType.AUTO:
            value = random.randint(0, 50)
            device_type = DeviceType.AIR_CONDITIONING  # The only available

        command = Command(type_, device_type, device_id, value)
        await commands_queue.put(command)


async def main():
    max_queue_size = 10
    commands_queue = asyncio.Queue(max_queue_size)
    command_callback = partial(connection_handler, commands_queue=commands_queue)

    server = await asyncio.start_server(command_callback, HOST_CENTRAL, PORT_CENTRAL)

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
