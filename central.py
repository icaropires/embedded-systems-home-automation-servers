#!/bin/python3

import asyncio
import signal
import logging


HOST_CENTRAL = ''
PORT_CENTRAL = 10008

PORT_DISTRIBUTED = 10108


async def alarm_handle(reader, writer):
    try:
        while True:
            data = await reader.readexactly(1)
            print('Alarme disparado')
    except (asyncio.CancelledError, asyncio.IncompleteReadError):
        ...
    finally:
        writer.close()
        await writer.wait_closed()

        logging.info("alarm handle ended")


async def states_handle(reader, writer):
    try:
        while True:
            data = await reader.readexactly(1)
            await asyncio.sleep(1)

            print('estado atualizado')
    except (asyncio.CancelledError, asyncio.IncompleteReadError):
        ...
    finally:
        writer.close()
        await writer.wait_closed()

        logging.info("States handle ended")


async def connection_handle(reader, writer):
    host, port, *_ = writer.get_extra_info('peername')

    states_task = asyncio.create_task(alarm_handle(reader, writer))

    alarm_reader, alarm_writer = await asyncio.open_connection(host, PORT_DISTRIBUTED)
    alarm_task = asyncio.create_task(states_handle(alarm_reader, alarm_writer))

    try:
        await asyncio.wait([states_task, alarm_task], return_when=asyncio.FIRST_COMPLETED)
    except asyncio.CancelledError:
        await states_task.cancel()
        await alarm_task.cancel()
    finally:
        logging.info(f"Closed connection to {host}:{port}")


async def main():
    server = await asyncio.start_server(
        connection_handle, HOST_CENTRAL, PORT_CENTRAL
    )

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
