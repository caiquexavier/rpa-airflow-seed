"""RabbitMQ client library for rpa-api."""
import json
import logging
import os

import pika

logger = logging.getLogger(__name__)


def publish(channel, queue: str, payload: dict) -> None:
    """
    Publish a JSON payload to a queue.
    
    Args:
        channel: RabbitMQ channel
        queue: Queue name
        payload: Dictionary to serialize and publish
    """
    json_payload = json.dumps(payload, separators=(',', ':'), ensure_ascii=False)
    channel.basic_publish(
        exchange='',
        routing_key=queue,
        body=json_payload,
        properties=pika.BasicProperties(
            content_type='application/json',
            delivery_mode=2  # Persistent message
        )
    )


def publish_json(payload: dict) -> bool:
    """
    Publish a JSON payload to RabbitMQ queue.
    
    Args:
        payload: Dictionary to serialize and publish
        
    Returns:
        bool: True if published successfully, False otherwise
    """
    try:
        # Get configuration from environment
        host = os.getenv("RABBITMQ_HOST", "localhost")
        port = int(os.getenv("RABBITMQ_PORT", "5672"))
        user = os.getenv("RABBITMQ_USER", "guest")
        password = os.getenv("RABBITMQ_PASSWORD", "guest")
        vhost = os.getenv("RABBITMQ_VHOST", "/")
        queue = os.getenv("RABBITMQ_QUEUE", "rpa_events")
        
        # Create connection
        credentials = pika.PlainCredentials(user, password)
        parameters = pika.ConnectionParameters(
            host=host,
            port=port,
            virtual_host=vhost,
            credentials=credentials
        )
        
        connection = pika.BlockingConnection(parameters)
        channel = connection.channel()
        
        # Declare queue
        channel.queue_declare(queue=queue, durable=True)
        
        # Publish message
        publish(channel, queue, payload)
        
        # Close connection
        connection.close()
        
        logger.info(f"Message published successfully to queue: {queue}")
        return True
            
    except Exception as e:
        logger.error(f"Failed to publish message: {e}")
        return False
