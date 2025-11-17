"""RabbitMQ configuration helpers."""
from dataclasses import dataclass

from .env import get_required_env, get_env


@dataclass(frozen=True)
class RabbitMQConfig:
    """RabbitMQ configuration."""
    host: str
    user: str
    password: str
    queue: str
    vhost: str = "/"


def load_rabbitmq_config() -> RabbitMQConfig:
    """
    Load RabbitMQ configuration from environment variables.
    
    Returns:
        RabbitMQConfig instance
        
    Raises:
        RuntimeError: If required environment variables are missing
    """
    return RabbitMQConfig(
        host=get_required_env('RABBITMQ_HOST'),
        user=get_required_env('RABBITMQ_USER'),
        password=get_required_env('RABBITMQ_PASSWORD'),
        queue=get_required_env('RABBITMQ_ROBOT_OPERATOR_QUEUE')
    )

