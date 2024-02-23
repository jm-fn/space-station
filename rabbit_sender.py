#!/usr/bin/env python

import asyncio
import argparse

import aio_pika
import pandas as pd
from numpy import NaN


QUEUE_SIZE = 50000


async def push_message(channel, msg, routing_key):
    await channel.default_exchange.publish(
        aio_pika.Message(body=msg.encode()), routing_key=routing_key
    )
    print(f"Sending {msg} to orbit.")


async def main(host, port, number) -> None:
    rabbitmq_url = f"amqp://guest:guest@{host}:{port}/"
    connection = await aio_pika.connect_robust(rabbitmq_url)

    # Get some names...
    name_df = pd.read_csv("names.csv", sep=",", encoding="latin")
    boys = name_df["boy name"]
    girls = name_df["girl name"]
    names = pd.concat([boys, girls])

    messages = list(f'{{"name": "{x}"}}' for x in names if x is not NaN)[:number]
    print(len(messages))

    async with connection:
        routing_key = "space-long"

        channel = await connection.channel()

        await channel.declare_queue(routing_key, arguments={"x-max-length": QUEUE_SIZE})
        await asyncio.gather(
            *(push_message(channel, msg, routing_key) for msg in messages)
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="Rabbit Sender", description="")
    parser.add_argument("-d", "--dest", help="RabbitMQ host", default="localhost")
    parser.add_argument("-p", "--port", help="RabbitMQ port", default="5672")
    parser.add_argument(
        "-n", "--number", help="Number of messages sent", default=5100, type=int
    )

    args = parser.parse_args()
    asyncio.run(main(args.dest, args.port, args.number))
