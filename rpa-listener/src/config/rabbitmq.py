"""RabbitMQ configuration helpers."""
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class RabbitMQConfig:
    host: str
    user: str
    password: str
    queue: str


def load_rabbitmq_config() -> RabbitMQConfig:
    return RabbitMQConfig(
        host=os.getenv('RABBITMQ_HOST', 'localhost'),
        user=os.getenv('RABBITMQ_USER', 'guest'),
        password=os.getenv('RABBITMQ_PASSWORD', 'guest'),
        queue=os.getenv('RABBITMQ_QUEUE', 'rpa_events'),
    )


