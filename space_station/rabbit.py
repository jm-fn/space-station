import os
import json
import time
import logging

import aio_pika
from aio_pika.abc import AbstractIncomingMessage
from sqlalchemy.ext.asyncio.session import AsyncSession
from aio_pika.robust_connection import AbstractRobustConnection

from space_station.models import Kosmonaut
from space_station import db


rabbitmq_password = os.environ.get("RABBITMQ_PASSWORD", "guest")
rabbitmq_user = os.environ.get("RABBITMQ_USER", "guest")
rabbitmq_port = os.environ.get("RABBITMQ_PORT", 5672)

# get host - if there is a k8s defined env var, use it.
rabbitmq_env_host = os.environ.get("RABBITMQ_HOST", "localhost")
rabbitmq_k8s_host = os.environ.get("SPACE_STATION_RABBITMQ_SERVICE_HOST", None)
rabbitmq_host = rabbitmq_k8s_host or rabbitmq_env_host

rabbitmq_url = (
    f"amqp://{rabbitmq_user}:{rabbitmq_password}@{rabbitmq_host}:{rabbitmq_port}/"
)

QUEUE_NAME = "space"
QUEUE_SIZE = 50000
QUEUE_ARGUMENTS = {"x-max-length": QUEUE_SIZE}
BATCH_SIZE = 100

logger = logging.getLogger(__name__)


class PikaConsumer:
    def __init__(self, connection: AbstractRobustConnection, channel):
        self.kosmo_batch: list[Kosmonaut] = []
        self.consumed: int = 0
        self.connection = connection
        self.start: float = 0
        self.channel = channel

    @staticmethod
    async def create(loop):
        logger.info("Creating pika client.")
        connection = await aio_pika.connect_robust(
            rabbitmq_url,
            loop=loop,
        )
        channel = await connection.channel()
        queue = await channel.declare_queue(QUEUE_NAME, arguments=QUEUE_ARGUMENTS)
        await channel.set_qos(1)  # FIXME: Is this really needed?
        pika_client = PikaConsumer(connection, channel)
        await queue.consume(pika_client.process_message, no_ack=False)
        return pika_client

    async def get_message_count(self):
        queue_name = "space"
        queue = await self.channel.declare_queue(
            queue_name, arguments={"x-max-length": QUEUE_SIZE}
        )
        return queue.declaration_result.message_count

    async def process_message(
        self,
        message: AbstractIncomingMessage,
    ) -> None:
        async with message.process():
            # Get Kosmonaut from message
            try:
                new_kosmonaut = json.loads(message.body.decode("utf-8"))
                kosmo_name = new_kosmonaut["name"]
                kosmo_age = new_kosmonaut.get("age", None)
                kosmonaut = Kosmonaut(name=kosmo_name, age=kosmo_age)
            except json.JSONDecodeError:
                logger.error(
                    "Got message with invalid JSON: %s", message.body.decode("utf-8")
                )
            except KeyError:
                logger.error(
                    "Got badly formed message: %s", message.body.decode("utf-8")
                )

            # Add kosmonaut to batch
            self.kosmo_batch.append(kosmonaut)

            # Send batch to database if it is full or if there are no more messages
            message_count = await self.get_message_count()
            if len(self.kosmo_batch) >= BATCH_SIZE or message_count == 0:
                async with AsyncSession(db.engine) as session:
                    new_batch = (
                        self.kosmo_batch
                    )  # Ensure no new items are added after sending starts
                    self.kosmo_batch = []

                    results = await db.bulk_create_kosmonaut(session, new_batch)
                    for kosmo_name in (x[1].name for x in results if not x[0]):
                        logger.warning(
                            "There is already kosmonaut by the same name %s registered.",
                            kosmo_name,
                        )
        self.consumed += 1
        if self.consumed == 1:
            self.time = time.time()
        if self.consumed == 5001:
            logger.info("Time per 5000 messages: %i", time.time() - self.time)
