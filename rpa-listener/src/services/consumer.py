"""RabbitMQ consumer service for RPA events."""
import json
from typing import Callable

import pika

from ..config.rabbitmq import RabbitMQConfig


class RpaConsumer:
    def __init__(self, config: RabbitMQConfig):
        self._config = config
        credentials = pika.PlainCredentials(config.user, config.password)
        self._connection = pika.BlockingConnection(
            pika.ConnectionParameters(host=config.host, credentials=credentials)
        )
        self._channel = self._connection.channel()
        self._channel.queue_declare(queue=config.queue, durable=True)

    def start(self, on_message: Callable[[dict], bool]) -> None:
        """Start consuming messages. on_message should return True on success, False on failure."""
        def _callback(ch, method, properties, body):
            try:
                print(f"Received message: {body.decode('utf-8')}")
                message = json.loads(body.decode('utf-8'))
                ok = on_message(message)
                if ok:
                    ch.basic_ack(delivery_tag=method.delivery_tag)
                else:
                    ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            except Exception as exc:
                print(f"Error processing message: {exc}")
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

        self._channel.basic_qos(prefetch_count=1)
        self._channel.basic_consume(queue=self._config.queue, on_message_callback=_callback)
        print(f"Waiting for messages on queue '{self._config.queue}'. Press Ctrl+C to exit.")
        self._channel.start_consuming()


