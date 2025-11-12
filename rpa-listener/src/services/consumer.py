# RabbitMQ consumer service for RPA events
import json
import time
import logging
from typing import Callable
import pika
from pika.exceptions import AMQPConnectionError, AMQPChannelError, StreamLostError
from ..config.rabbitmq import RabbitMQConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RpaConsumer:
    def __init__(self, config: RabbitMQConfig):
        self._config = config
        self._connection = None
        self._channel = None

    def _connect(self):
        # Establish connection and channel with retry logic
        credentials = pika.PlainCredentials(self._config.user, self._config.password)
        parameters = pika.ConnectionParameters(host=self._config.host, virtual_host="/", credentials=credentials, heartbeat=600, blocked_connection_timeout=300, socket_timeout=300, connection_attempts=3, retry_delay=2, stack_timeout=300)
        max_retries = 5
        retry_delay = 5
        for attempt in range(1, max_retries + 1):
            try:
                self._connection = pika.BlockingConnection(parameters)
                self._channel = self._connection.channel()
                self._channel.queue_declare(queue=self._config.queue, durable=True)
                return
            except (AMQPConnectionError, StreamLostError, ConnectionAbortedError, OSError) as e:
                if attempt < max_retries:
                    time.sleep(retry_delay)
                else:
                    raise

    def _reconnect(self):
        # Close existing connection and reconnect
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
        self._connect()

    def start(self, on_message: Callable[[dict], bool]) -> None:
        # Start consuming messages with automatic reconnection on connection errors
        self._connect()
        def _callback(ch, method, properties, body):
            message_processed = False
            try:
                message = json.loads(body.decode('utf-8'))
                logger.info(f"Received message from queue: {json.dumps(message, indent=2, ensure_ascii=False)}")
                ok = on_message(message)
                message_processed = True
                try:
                    if ok:
                        ch.basic_ack(delivery_tag=method.delivery_tag)
                    else:
                        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
                except (AMQPChannelError, StreamLostError, ConnectionAbortedError, OSError):
                    raise
            except (AMQPChannelError, StreamLostError, ConnectionAbortedError, OSError):
                raise
            except Exception:
                if not message_processed:
                    try:
                        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
                    except (AMQPChannelError, StreamLostError, ConnectionAbortedError, OSError):
                        raise
        while True:
            try:
                self._channel.basic_qos(prefetch_count=1)
                self._channel.basic_consume(queue=self._config.queue, on_message_callback=_callback)
                self._channel.start_consuming()
            except (AMQPConnectionError, StreamLostError, ConnectionAbortedError, OSError):
                self._reconnect()
                time.sleep(2)
            except KeyboardInterrupt:
                break
            except Exception:
                self._reconnect()
                time.sleep(2)


