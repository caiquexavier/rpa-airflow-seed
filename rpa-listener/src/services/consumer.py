"""RabbitMQ consumer service for RPA events."""
import json
import time
from typing import Callable

import pika
from pika.exceptions import AMQPConnectionError, AMQPChannelError, StreamLostError

from ..config.rabbitmq import RabbitMQConfig


class RpaConsumer:
    def __init__(self, config: RabbitMQConfig):
        self._config = config
        self._connection = None
        self._channel = None

    def _connect(self):
        """Establish connection and channel with retry logic."""
        credentials = pika.PlainCredentials(self._config.user, self._config.password)
        parameters = pika.ConnectionParameters(
            host=self._config.host,
            virtual_host="/",
            credentials=credentials,
            heartbeat=600,  # Heartbeat every 10 minutes (longer for robot executions)
            blocked_connection_timeout=300,  # 5 minutes
            socket_timeout=300,  # 5 minutes
            connection_attempts=3,
            retry_delay=2,
            stack_timeout=300  # 5 minutes
        )
        
        max_retries = 5
        retry_delay = 5
        
        for attempt in range(1, max_retries + 1):
            try:
                self._connection = pika.BlockingConnection(parameters)
                self._channel = self._connection.channel()
                self._channel.queue_declare(queue=self._config.queue, durable=True)
                print(f"Successfully connected to RabbitMQ (attempt {attempt})")
                return
            except (AMQPConnectionError, StreamLostError, ConnectionAbortedError, OSError) as e:
                if attempt < max_retries:
                    print(f"Connection attempt {attempt}/{max_retries} failed: {e}. Retrying in {retry_delay}s...")
                    time.sleep(retry_delay)
                else:
                    print(f"Failed to connect after {max_retries} attempts: {e}")
                    raise

    def _reconnect(self):
        """Close existing connection and reconnect."""
        try:
            if self._channel and not self._channel.is_closed:
                self._channel.stop_consuming()
        except Exception:
            pass
        
        try:
            if self._connection and not self._connection.is_closed:
                self._connection.close()
        except Exception:
            pass
        
        print("Reconnecting to RabbitMQ...")
        self._connect()

    def start(self, on_message: Callable[[dict], bool]) -> None:
        """Start consuming messages with automatic reconnection on connection errors."""
        self._connect()
        
        def _callback(ch, method, properties, body):
            message_processed = False
            try:
                print(f"Received message: {body.decode('utf-8')}")
                message = json.loads(body.decode('utf-8'))
                # Process message: robot executes, returns response, listener sends webhook
                ok = on_message(message)
                message_processed = True
                # Ack message after successful processing
                try:
                    if ok:
                        ch.basic_ack(delivery_tag=method.delivery_tag)
                        print(f"Message processed successfully, acknowledged")
                    else:
                        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
                        print(f"Message processing failed, not requeued")
                except (AMQPChannelError, StreamLostError, ConnectionAbortedError, OSError) as ack_error:
                    # Connection lost during ack - message was processed, so it's safe to continue
                    print(f"Connection lost during ack (message was processed): {ack_error}")
                    raise  # Re-raise to trigger reconnection
            except (AMQPChannelError, StreamLostError, ConnectionAbortedError, OSError) as conn_error:
                # Connection errors - re-raise to trigger reconnection
                if message_processed:
                    # Message was processed and webhook sent - connection loss is non-critical
                    print(f"Connection lost after message processing (webhook sent): {conn_error}")
                    print("This is non-critical - message was processed successfully")
                else:
                    print(f"Connection lost during message processing: {conn_error}")
                raise
            except Exception as exc:
                # Other processing errors
                print(f"Error processing message: {exc}")
                if not message_processed:
                    try:
                        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
                    except (AMQPChannelError, StreamLostError, ConnectionAbortedError, OSError):
                        print("Channel closed while nacking message, will reconnect")
                        raise

        while True:
            try:
                self._channel.basic_qos(prefetch_count=1)
                self._channel.basic_consume(queue=self._config.queue, on_message_callback=_callback)
                print(f"Waiting for messages on queue '{self._config.queue}'. Press Ctrl+C to exit.")
                self._channel.start_consuming()
            except (AMQPConnectionError, StreamLostError, ConnectionAbortedError, OSError) as e:
                print(f"Connection lost: {e}. Attempting to reconnect...")
                self._reconnect()
                time.sleep(2)  # Brief pause before retrying
            except KeyboardInterrupt:
                print("Interrupted by user")
                break
            except Exception as e:
                print(f"Unexpected error: {e}. Attempting to reconnect...")
                self._reconnect()
                time.sleep(2)


