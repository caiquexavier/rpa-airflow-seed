"""RabbitMQ consumer service for RPA events."""
import json
import time
import logging
from typing import Callable
from threading import Event
import pika
from pika.exceptions import AMQPConnectionError, AMQPChannelError, StreamLostError
from ...core.config.rabbitmq import RabbitMQConfig

logger = logging.getLogger(__name__)


class RpaConsumer:
    def __init__(self, config: RabbitMQConfig):
        self._config = config
        self._connection = None
        self._channel = None
        self._stop_event: Event = Event()

    def _connect(self):
        """Establish connection and channel with retry logic."""
        credentials = pika.PlainCredentials(self._config.user, self._config.password)
        parameters = pika.ConnectionParameters(host=self._config.host, virtual_host="/", credentials=credentials, heartbeat=600, blocked_connection_timeout=300, socket_timeout=300, connection_attempts=3, retry_delay=2, stack_timeout=300)
        max_retries = 5
        retry_delay = 5
        for attempt in range(1, max_retries + 1):
            try:
                logger.info(
                    "Connecting to RabbitMQ",
                    extra={"host": self._config.host, "queue": self._config.queue, "attempt": attempt},
                )
                self._connection = pika.BlockingConnection(parameters)
                self._channel = self._connection.channel()
                self._channel.queue_declare(queue=self._config.queue, durable=True, passive=False)
                logger.info("Connected to RabbitMQ", extra={"queue": self._config.queue})
                return
            except (AMQPConnectionError, StreamLostError, ConnectionAbortedError, OSError) as e:
                logger.warning("RabbitMQ connection attempt failed: %s", e)
                if attempt < max_retries:
                    time.sleep(retry_delay)
                else:
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
        if not self._stop_event.is_set():
            self._connect()

    def stop(self) -> None:
        """Signal the consumer to stop consuming."""
        self._stop_event.set()
        try:
            if self._channel and not self._channel.is_closed:
                self._channel.stop_consuming()
        except Exception:
            pass

    def close(self) -> None:
        """Gracefully stop and close channel/connection."""
        self.stop()
        try:
            if self._connection and not self._connection.is_closed:
                self._connection.close()
        except Exception:
            pass

    def start(self, on_message: Callable[[dict], bool]) -> None:
        """Start consuming messages with automatic reconnection on connection errors."""
        self._connect()
        def _callback(ch, method, properties, body):
            message_processed = False
            try:
                message = json.loads(body.decode('utf-8'))
                logger.info(
                    "Message received from queue",
                    extra={
                        "delivery_tag": method.delivery_tag,
                        "queue": self._config.queue,
                        "headers": getattr(properties, "headers", None),
                    },
                )
                ok = on_message(message)
                message_processed = True
                try:
                    if ok:
                        logger.info(
                            "Message processed successfully",
                            extra={"delivery_tag": method.delivery_tag, "queue": self._config.queue},
                        )
                        ch.basic_ack(delivery_tag=method.delivery_tag)
                    else:
                        logger.warning(
                            "Message processing failed; sending NACK",
                            extra={"delivery_tag": method.delivery_tag, "queue": self._config.queue},
                        )
                        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
                except (AMQPChannelError, StreamLostError, ConnectionAbortedError, OSError):
                    raise
            except (AMQPChannelError, StreamLostError, ConnectionAbortedError, OSError):
                raise
            except Exception:
                logger.exception("Unhandled error while processing message")
                if not message_processed:
                    try:
                        logger.warning(
                            "NACK-ing message due to unhandled exception",
                            extra={"delivery_tag": method.delivery_tag, "queue": self._config.queue},
                        )
                        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
                    except (AMQPChannelError, StreamLostError, ConnectionAbortedError, OSError):
                        raise
        while not self._stop_event.is_set():
            try:
                self._channel.basic_qos(prefetch_count=1)
                self._channel.basic_consume(
                    queue=self._config.queue, 
                    on_message_callback=_callback,
                    auto_ack=False
                )
                logger.info("Starting RabbitMQ consumption loop", extra={"queue": self._config.queue})
                self._channel.start_consuming()
            except (AMQPConnectionError, StreamLostError, ConnectionAbortedError, OSError):
                if self._stop_event.is_set():
                    break
                logger.warning("RabbitMQ connection lost; attempting to reconnect")
                self._reconnect()
                time.sleep(2)
            except KeyboardInterrupt:
                self.stop()
                break
            except Exception:
                if self._stop_event.is_set():
                    break
                logger.exception("Unexpected consumer error; reconnecting")
                self._reconnect()
                time.sleep(2)

