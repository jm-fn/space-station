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
QUEUE_SIZE = 50000

logger = logging.getLogger(__name__)


class PikaConsumer:
    def __init__(self, connection: AbstractRobustConnection):
        self.consumed: int = 0
        self.connection = connection
        self.start: float = 0

    @staticmethod
    async def create(loop):
        logger.info("Creating pika client.")
        connection = await aio_pika.connect_robust(
            rabbitmq_url,
            loop=loop,
        )
        queue_name = "space-long"
        channel = await connection.channel()
        queue = await channel.declare_queue(
            queue_name, arguments={"x-max-length": QUEUE_SIZE}
        )
        pika_client = PikaConsumer(connection)
        await queue.consume(pika_client.process_message)
        return pika_client

    async def process_message(
        self,
        message: AbstractIncomingMessage,
    ) -> None:
        async with message.process():
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
            async with AsyncSession(db.engine) as session:
                created, kosmo = await db.create_kosmonaut(session, kosmonaut)
            if not created:
                logger.warning(
                    "There is already kosmonaut by the same name %s registered.",
                    kosmo_name,
                )
        self.consumed += 1
        print(self.consumed)
        if self.consumed == 1:
            self.time = time.time()
        if self.consumed == 5001:
            logger.info("Time per 5000 messages: %i", time.time() - self.time)
