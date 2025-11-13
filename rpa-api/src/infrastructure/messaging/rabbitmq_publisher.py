"""RabbitMQ message publisher."""
from typing import Dict, Any

from ..adapters.rabbitmq_service import publish_execution_message


def publish_message(message: Dict[str, Any]) -> bool:
    """
    Publish message to RabbitMQ.
    
    Returns:
        True if published successfully
    """
    return publish_execution_message(message)

