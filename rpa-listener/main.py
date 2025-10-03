#!/usr/bin/env python3
"""
RPA Listener - RabbitMQ to Robot Framework Bridge
"""

import json
import logging
import os
import subprocess
import sys
from pathlib import Path

import pika
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RPAListener:
    def __init__(self):
        self.connection = None
        self.channel = None
        
        # Load configuration from environment
        self.rabbitmq_host = os.getenv('RABBITMQ_HOST', 'localhost')
        self.rabbitmq_user = os.getenv('RABBITMQ_USER', 'admin')
        self.rabbitmq_password = os.getenv('RABBITMQ_PASSWORD', 'pass')
        self.queue_name = os.getenv('RABBITMQ_QUEUE', 'rpa_events')
        self.project_dir = os.getenv('PROJECT_DIR')
        
        if not self.project_dir:
            raise ValueError("PROJECT_DIR environment variable is required")
        
        # Setup paths
        self.project_path = Path(self.project_dir)
        self.robot_exe = self.project_path / 'venv' / 'Scripts' / 'robot.exe'
        self.tests_path = self.project_path / 'tests'
        self.results_dir = self.project_path / 'results'
        
        # Validate paths
        if not self.robot_exe.exists():
            raise FileNotFoundError(f"Robot executable not found: {self.robot_exe}")
        if not self.tests_path.exists():
            raise FileNotFoundError(f"Tests directory not found: {self.tests_path}")
        
        # Ensure results directory exists
        self.results_dir.mkdir(exist_ok=True)
        
        logger.info(f"Project: {self.project_dir}")
        logger.info(f"Queue: {self.queue_name}")

    def connect(self):
        """Connect to RabbitMQ and set up the queue"""
        try:
            credentials = pika.PlainCredentials(self.rabbitmq_user, self.rabbitmq_password)
            self.connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host=self.rabbitmq_host,
                    credentials=credentials
                )
            )
            self.channel = self.connection.channel()
            self.channel.queue_declare(queue=self.queue_name, durable=True)
            logger.info(f"Connected to RabbitMQ at {self.rabbitmq_host}")
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            raise

    def run_robot_tests(self, rpa_id):
        """Run Robot Framework tests via PowerShell"""
        try:
            cmd = [
                'powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command',
                f"Set-Location '{self.project_dir}'; & '{self.robot_exe}' -d '{self.results_dir}' '{self.tests_path}'"
            ]
            
            logger.info(f"Running Robot tests for job {rpa_id}")
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.project_dir)
            
            if result.returncode == 0:
                logger.info(f"Job {rpa_id} completed successfully")
                return True
            else:
                logger.error(f"Job {rpa_id} failed (exit code: {result.returncode})")
                return False
                
        except Exception as e:
            logger.error(f"Exception running tests for job {rpa_id}: {e}")
            return False

    def process_message(self, ch, method, properties, body):
        """Process incoming RabbitMQ message"""
        try:
            message = json.loads(body.decode('utf-8'))
            rpa_id = message.get('rpa-id')
            
            if not rpa_id:
                logger.error("Message missing 'rpa-id' field")
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
                return
            
            logger.info(f"Received job {rpa_id}")
            success = self.run_robot_tests(rpa_id)
            
            if success:
                ch.basic_ack(delivery_tag=method.delivery_tag)
            else:
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON message: {e}")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

    def start_consuming(self):
        """Start consuming messages from the queue"""
        try:
            self.channel.basic_qos(prefetch_count=1)
            self.channel.basic_consume(
                queue=self.queue_name,
                on_message_callback=self.process_message
            )
            
            logger.info("Starting to consume messages. Press Ctrl+C to stop.")
            self.channel.start_consuming()
            
        except KeyboardInterrupt:
            logger.info("Received interrupt signal. Stopping...")
            if self.channel and not self.channel.is_closed:
                self.channel.stop_consuming()
            if self.connection and not self.connection.is_closed:
                self.connection.close()
        except Exception as e:
            logger.error(f"Error while consuming messages: {e}")
            if self.channel and not self.channel.is_closed:
                self.channel.stop_consuming()
            if self.connection and not self.connection.is_closed:
                self.connection.close()

    def run(self):
        """Main run method"""
        try:
            self.connect()
            self.start_consuming()
        except Exception as e:
            logger.error(f"Fatal error: {e}")
            sys.exit(1)

def main():
    """Main entry point"""
    try:
        listener = RPAListener()
        listener.run()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
