#!/usr/bin/env python3
"""Test RabbitMQ connection directly."""
import pika
import os

def test_rabbitmq_connection():
    try:
        # Get configuration
        host = os.getenv("RABBITMQ_HOST", "localhost")
        port = int(os.getenv("RABBITMQ_PORT", "5672"))
        user = os.getenv("RABBITMQ_USER", "admin")
        password = os.getenv("RABBITMQ_PASSWORD", "pass")
        vhost = os.getenv("RABBITMQ_VHOST", "/")
        
        print(f"Connecting to RabbitMQ at {host}:{port}")
        print(f"User: {user}, VHost: {vhost}")
        
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
        
        print("SUCCESS: Connected to RabbitMQ!")
        
        # Test queue declaration
        queue = os.getenv("RABBITMQ_QUEUE", "rpa_events")
        channel.queue_declare(queue=queue, durable=True)
        print(f"SUCCESS: Declared queue: {queue}")
        
        # Test publishing WITHOUT publisher confirms
        test_message = '{"rpa-id": "test-connection"}'
        channel.basic_publish(
            exchange='',
            routing_key=queue,
            body=test_message,
            properties=pika.BasicProperties(
                content_type='application/json',
                delivery_mode=2
            )
        )
        
        print("SUCCESS: Published test message!")
        
        connection.close()
        print("SUCCESS: Connection closed")
        
    except Exception as e:
        print(f"ERROR: {e}")
        return False
    
    return True

if __name__ == "__main__":
    test_rabbitmq_connection()
