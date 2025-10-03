"""Queue service for publishing messages to RabbitMQ."""
import logging
from typing import Dict, Any

from ..libs.rabbitmq_client import publish_json

logger = logging.getLogger(__name__)


class QueuePublishError(Exception):
    """Exception raised when queue publishing fails."""
    pass


class QueueService:
    """Service for publishing messages to RabbitMQ queue."""
    
    def publish(self, payload: Dict[str, Any]) -> None:
        """
        Publish a payload to the RabbitMQ queue.
        
        Args:
            payload: The payload dictionary to publish
            
        Raises:
            QueuePublishError: If publishing fails
        """
        try:
            logger.info(f"Publishing payload to queue: {payload}")
            
            success = publish_json(payload)
            
            if not success:
                raise QueuePublishError("Failed to publish message to queue")
            
            logger.info("Payload published successfully")
            
        except Exception as e:
            logger.error(f"Queue publish error: {e}")
            raise QueuePublishError(f"Queue publishing failed: {e}") from e
