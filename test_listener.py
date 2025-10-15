#!/usr/bin/env python3
"""
Test script to verify RPA listener is working correctly
"""

import json
import pika
import time

def test_listener():
    """Test if listener can process messages"""
    
    # RabbitMQ connection
    credentials = pika.PlainCredentials('admin', 'admin')
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host='localhost', credentials=credentials)
    )
    channel = connection.channel()
    
    # Declare queue
    channel.queue_declare(queue='rpa_events', durable=True)
    
    # Send test message
    test_message = {
        "rpa_id": "test_listener_verification",
        "callback_url": "https://example.com/callback",
        "rpa_request": {"test": "data"}
    }
    
    print(f"Sending test message: {json.dumps(test_message)}")
    channel.basic_publish(
        exchange='',
        routing_key='rpa_events',
        body=json.dumps(test_message),
        properties=pika.BasicProperties(delivery_mode=2)  # Make message persistent
    )
    
    print("Test message sent to rpa_events queue")
    print("Check listener logs to see if message was processed")
    
    connection.close()

if __name__ == "__main__":
    test_listener()
