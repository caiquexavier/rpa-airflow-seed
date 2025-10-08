"""RabbitMQ client library for rpa-api."""
import json
import logging
import os
import time
from typing import Optional

import pika
from ..config.azure_config import AzureConfig
 

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
        # Validate Azure credentials are loaded
        if not AzureConfig.validate_credentials():
            logger.error("Azure Key Vault credentials not loaded. Run load-azure-keys.py first.")
            return False
        
        # Get credentials from Azure Key Vault
        host = AzureConfig.get_rabbitmq_host()
        port = AzureConfig.get_rabbitmq_port()
        user = AzureConfig.get_rabbitmq_user()
        password = AzureConfig.get_rabbitmq_password()
        vhost = os.getenv("RABBITMQ_VHOST", "/")
        queue = AzureConfig.get_rabbitmq_queue()

        heartbeat = int(os.getenv("RABBITMQ_HEARTBEAT", "30"))
        blocked_connection_timeout = float(os.getenv("RABBITMQ_BLOCKED_TIMEOUT", "30"))
        socket_timeout = float(os.getenv("RABBITMQ_SOCKET_TIMEOUT", "10"))
        connection_attempts = int(os.getenv("RABBITMQ_CONN_ATTEMPTS", "3"))
        retry_delay_seconds = float(os.getenv("RABBITMQ_RETRY_DELAY", "2"))

        credentials = pika.PlainCredentials(user, password)
        parameters = pika.ConnectionParameters(
            host=host,
            port=port,
            virtual_host=vhost,
            credentials=credentials,
            heartbeat=heartbeat,
            blocked_connection_timeout=blocked_connection_timeout,
            socket_timeout=socket_timeout,
            connection_attempts=connection_attempts,
            retry_delay=0,
        )

        last_error: Optional[Exception] = None
        for attempt in range(1, connection_attempts + 1):
            try:
                connection = pika.BlockingConnection(parameters)
                channel = connection.channel()
                channel.queue_declare(queue=queue, durable=True)
                publish(channel, queue, payload)
                connection.close()
                return True
            except Exception as connect_error:  # retryable
                last_error = connect_error
                logger.warning(
                    f"RabbitMQ publish attempt {attempt}/{connection_attempts} failed: {connect_error}"
                )
                if attempt < connection_attempts:
                    time.sleep(retry_delay_seconds)

        if last_error:
            raise last_error
        return False
    except Exception as e:
        logger.error(f"Failed to publish message: {e}")
        return False
