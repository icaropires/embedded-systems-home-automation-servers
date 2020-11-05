#!/bin/python3

import asyncio
import signal
import logging
import random
from struct import Struct
from functools import partial
from enum import Enum
from typing import NamedTuple


HOST_CENTRAL = ''
PORT_CENTRAL = 10008

PORT_DISTRIBUTED = 10108

CommandType = Enum('CommandType', 'ON OFF AUTO')


class Command(NamedTuple):
    type_ : CommandType
    value: float = -1
    

async def play_alarm():
    print("ALARM!!!!")


async def states_handler(reader):
    while True:
        states = await reader.readexactly(1)
        await asyncio.sleep(1)

        if False: #TODO
            play_alarm()

        print('ESTADO RECEBIDO')


async def commands_handler(writer, queue):
    while True:
        command = await queue.get()

        if command.type_ == CommandType.AUTO:
            struct = Struct('If')
            command_bytes = struct.pack(command.type_.value, command.value)
        else:
            type_ = command.type_.value
            command_bytes = type_.to_bytes(4, 'little')

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
        await asyncio.sleep(random.randint(3, 8))
        type_ = random.choice([CommandType.ON, CommandType.OFF, CommandType.AUTO])

        value = -1
        if type_ == CommandType.AUTO:
            value = random.randint(0, 50)

        await commands_queue.put(Command(type_, value))


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
