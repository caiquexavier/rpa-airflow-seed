#!/usr/bin/env python3
"""
RPA Listener - Minimal implementation
Connects to rpa_events queue and executes robot framework tests
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pika
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def get_rabbitmq_config():
    """Get RabbitMQ configuration from environment variables"""
    return {
        'host': os.getenv('RABBITMQ_HOST', 'localhost'),
        'user': os.getenv('RABBITMQ_USER', 'guest'),
        'password': os.getenv('RABBITMQ_PASSWORD', 'guest'),
        'queue': 'rpa_events'
    }


def get_robot_paths():
    """Get robot framework paths"""
    repo_root = Path(__file__).resolve().parent.parent
    project_path = repo_root / 'rpa-robots'
    robot_exe = project_path / 'venv' / 'Scripts' / 'robot.exe'
    tests_path = project_path / 'tests'
    results_dir = project_path / 'results'
    
    return {
        'project_path': project_path,
        'robot_exe': robot_exe,
        'tests_path': tests_path,
        'results_dir': results_dir
    }


def run_robot_tests(project_path, robot_exe, tests_path, results_dir):
    """Execute robot framework tests"""
    cmd = [
        'powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command',
        f"Set-Location '{project_path}'; & '{robot_exe}' -d '{results_dir}' '{tests_path}'"
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=project_path)
    return result.returncode == 0


def process_message(ch, method, properties, body, robot_config):
    """Process incoming message and run robot tests"""
    try:
        print(f"Received message: {body.decode('utf-8')}")
        message = json.loads(body.decode('utf-8'))
        rpa_id = message.get('rpa-id')
        
        if not rpa_id:
            print("Error: Message missing 'rpa-id' field")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            return
        
        print(f"Processing RPA ID: {rpa_id}")
        success = run_robot_tests(
            robot_config['project_path'],
            robot_config['robot_exe'],
            robot_config['tests_path'],
            robot_config['results_dir']
        )
        
        if success:
            print(f"Robot tests completed successfully for RPA ID: {rpa_id}")
            ch.basic_ack(delivery_tag=method.delivery_tag)
        else:
            print(f"Robot tests failed for RPA ID: {rpa_id}")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            
    except (json.JSONDecodeError, Exception) as e:
        print(f"Error processing message: {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)


def main():
    """Main function"""
    try:
        # Get configurations
        rabbitmq_config = get_rabbitmq_config()
        robot_config = get_robot_paths()
        
        print(f"RabbitMQ Config: {rabbitmq_config}")
        print(f"Robot Config: {robot_config}")
        
        # Validate robot paths
        if not robot_config['robot_exe'].exists():
            raise FileNotFoundError(f"Robot executable not found: {robot_config['robot_exe']}")
        if not robot_config['tests_path'].exists():
            raise FileNotFoundError(f"Tests directory not found: {robot_config['tests_path']}")
        
        # Create results directory
        robot_config['results_dir'].mkdir(exist_ok=True)
        
        # Connect to RabbitMQ
        print(f"Connecting to RabbitMQ at {rabbitmq_config['host']}...")
        credentials = pika.PlainCredentials(rabbitmq_config['user'], rabbitmq_config['password'])
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(host=rabbitmq_config['host'], credentials=credentials)
        )
        channel = connection.channel()
        print(f"Connected to RabbitMQ successfully")
        
        # Declare queue
        print(f"Declaring queue: {rabbitmq_config['queue']}")
        channel.queue_declare(queue=rabbitmq_config['queue'], durable=True)
        print(f"Queue declared successfully")
        
        # Set up message processing
        def callback(ch, method, properties, body):
            process_message(ch, method, properties, body, robot_config)
        
        channel.basic_qos(prefetch_count=1)
        channel.basic_consume(queue=rabbitmq_config['queue'], on_message_callback=callback)
        
        print(f"Waiting for messages on queue '{rabbitmq_config['queue']}'. Press Ctrl+C to exit.")
        # Start consuming
        channel.start_consuming()
        
    except KeyboardInterrupt:
        pass
    except Exception as exc:
        sys.stderr.write(f"Fatal error: {exc}\n")
        sys.exit(1)
    finally:
        try:
            if 'channel' in locals() and not channel.is_closed:
                channel.stop_consuming()
        except Exception:
            pass
        try:
            if 'connection' in locals() and not connection.is_closed:
                connection.close()
        except Exception:
            pass


if __name__ == '__main__':
    main()