# RabbitMQ configuration helpers
import os
from dataclasses import dataclass


def _get_required_env(name: str) -> str:
    # Get required environment variable or raise error
    value = os.getenv(name)
    if value is None or value == "":
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


@dataclass(frozen=True)
class RabbitMQConfig:
    host: str
    user: str
    password: str
    queue: str
    vhost: str = "/"


def load_rabbitmq_config() -> RabbitMQConfig:
    # Load RabbitMQ configuration from required environment variables
    return RabbitMQConfig(host=_get_required_env('RABBITMQ_HOST'), user=_get_required_env('RABBITMQ_USER'), password=_get_required_env('RABBITMQ_PASSWORD'), queue=os.getenv('RABBITMQ_QUEUE', 'rpa_events'))


