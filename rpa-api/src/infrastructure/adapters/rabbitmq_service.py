"""RabbitMQ service for publishing execution messages."""
import json
import logging
import os
import time
from typing import Optional

import pika
from ...config.config import get_rabbitmq_config

logger = logging.getLogger(__name__)


def publish_execution_message(payload: dict) -> bool:
    """
    Publish RobotOperatorSaga message to RabbitMQ queue - pure function.
    
    Args:
        payload: Dictionary containing robot_operator_saga_id, saga_id, robot_operator_id, robot_test_file, callback_path, rpa_request, robot_saga
        
    Returns:
        bool: True if published successfully, False otherwise
    """
    try:
        config = get_rabbitmq_config()
        host = config["RABBITMQ_HOST"]
        port = int(config["RABBITMQ_PORT"])
        user = config["RABBITMQ_USER"]
        password = config["RABBITMQ_PASSWORD"]
        vhost = config["RABBITMQ_VHOST"]
        queue = config["RABBITMQ_ROUTING_KEY"]
        
        logger.info(f"Publishing to RabbitMQ: host={host}, port={port}, vhost={vhost}, queue={queue}, user={user}")

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
                logger.info(f"Connecting to RabbitMQ (attempt {attempt}/{connection_attempts})...")
                connection = pika.BlockingConnection(parameters)
                channel = connection.channel()
                logger.info(f"Channel created. Declaring queue: {queue} (durable=True)")
                channel.queue_declare(queue=queue, durable=True)
                logger.info(f"Queue declared successfully: {queue}")
                
                # Publish message
                json_payload = json.dumps(payload, separators=(',', ':'), ensure_ascii=False)
                robot_saga_id = payload.get('robot_operator_saga_id') or payload.get('saga_id', 'unknown')
                logger.info(f"Publishing message to queue '{queue}': robot_operator_saga_id={robot_saga_id}, payload_size={len(json_payload)} bytes")
                channel.basic_publish(
                    exchange='',
                    routing_key=queue,
                    body=json_payload,
                    properties=pika.BasicProperties(
                        content_type='application/json',
                        delivery_mode=2  # Persistent message
                    )
                )
                robot_saga_id = payload.get('robot_operator_saga_id') or payload.get('saga_id', 'unknown')
                logger.info(f"Message published successfully to queue '{queue}' for robot_operator_saga_id={robot_saga_id}")
                
                connection.close()
                logger.info(f"Connection closed. Published RobotOperatorSaga message for robot_operator_saga_id={robot_saga_id}")
                return True
                
            except Exception as connect_error:
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
        logger.error(f"Failed to publish execution message: {e}")
        return False
