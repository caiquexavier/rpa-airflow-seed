"""
Azure Key Vault configuration loader for RPA API.
Loads credentials from environment variables set by centralized loader.
"""

import os
from typing import Optional

class AzureConfig:
    """Centralized configuration for Azure Key Vault credentials."""
    
    @staticmethod
    def get_rabbitmq_host() -> str:
        """Get RabbitMQ host from environment."""
        return os.getenv('RABBITMQ_HOST', 'localhost')
    
    @staticmethod
    def get_rabbitmq_port() -> int:
        """Get RabbitMQ port from environment."""
        return int(os.getenv('RABBITMQ_PORT', '5672'))
    
    @staticmethod
    def get_rabbitmq_user() -> str:
        """Get RabbitMQ username from Azure Key Vault."""
        return os.getenv('RABBITMQ_USER')
    
    @staticmethod
    def get_rabbitmq_password() -> str:
        """Get RabbitMQ password from Azure Key Vault."""
        return os.getenv('RABBITMQ_PASSWORD')
    
    @staticmethod
    def get_rabbitmq_queue() -> str:
        """Get RabbitMQ queue name from environment."""
        return os.getenv('RABBITMQ_QUEUE', 'rpa_events')
    
    @staticmethod
    def validate_credentials() -> bool:
        """Validate that all required credentials are present."""
        required_vars = ['RABBITMQ_USER', 'RABBITMQ_PASSWORD']
        return all(os.getenv(var) for var in required_vars)
