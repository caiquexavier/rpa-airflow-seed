"""Unit tests for rabbitmq service."""
import pytest
from unittest.mock import patch, MagicMock

from src.services.rabbitmq_service import publish_execution_message


class TestPublishExecutionMessage:
    """Test publish_execution_message function."""
    
    @patch('src.services.rabbitmq_service.get_rabbitmq_config')
    @patch('src.services.rabbitmq_service.pika.BlockingConnection')
    def test_successful_publish(self, mock_connection_class, mock_get_config):
        """Test successful message publishing."""
        # Setup
        mock_config = {
            'RABBITMQ_HOST': 'localhost',
            'RABBITMQ_PORT': '5672',
            'RABBITMQ_USER': 'guest',
            'RABBITMQ_PASSWORD': 'guest',
            'RABBITMQ_VHOST': '/',
            'RABBITMQ_ROUTING_KEY': 'test_queue'
        }
        mock_get_config.return_value = mock_config
        
        mock_connection = MagicMock()
        mock_channel = MagicMock()
        mock_connection.channel.return_value = mock_channel
        mock_connection_class.return_value = mock_connection
        
        payload = {
            'exec_id': 123,
            'rpa_key_id': 'job-001',
            'callback_url': 'http://localhost:3000/callback',
            'rpa_request': {'nota_fiscal': '12345'}
        }
        
        # Execute
        result = publish_execution_message(payload)
        
        # Verify
        assert result is True
        mock_channel.queue_declare.assert_called_once_with(queue='test_queue', durable=True)
        mock_channel.basic_publish.assert_called_once()
        mock_connection.close.assert_called_once()
    
    @patch('src.services.rabbitmq_service.get_rabbitmq_config')
    @patch('src.services.rabbitmq_service.pika.BlockingConnection')
    def test_publish_with_retry_success(self, mock_connection_class, mock_get_config):
        """Test successful publish after retry."""
        # Setup
        mock_config = {
            'RABBITMQ_HOST': 'localhost',
            'RABBITMQ_PORT': '5672',
            'RABBITMQ_USER': 'guest',
            'RABBITMQ_PASSWORD': 'guest',
            'RABBITMQ_VHOST': '/',
            'RABBITMQ_ROUTING_KEY': 'test_queue'
        }
        mock_get_config.return_value = mock_config
        
        mock_connection = MagicMock()
        mock_channel = MagicMock()
        mock_connection.channel.return_value = mock_channel
        mock_connection_class.return_value = mock_connection
        
        # First call fails, second succeeds
        mock_connection_class.side_effect = [Exception("Connection failed"), mock_connection]
        
        payload = {'exec_id': 123, 'rpa_key_id': 'job-001'}
        
        with patch('src.services.rabbitmq_service.time.sleep'):  # Mock sleep
            # Execute
            result = publish_execution_message(payload)
        
        # Verify
        assert result is True
        assert mock_connection_class.call_count == 2
    
    @patch('src.services.rabbitmq_service.get_rabbitmq_config')
    @patch('src.services.rabbitmq_service.pika.BlockingConnection')
    def test_publish_all_attempts_fail(self, mock_connection_class, mock_get_config):
        """Test when all publish attempts fail."""
        # Setup
        mock_config = {
            'RABBITMQ_HOST': 'localhost',
            'RABBITMQ_PORT': '5672',
            'RABBITMQ_USER': 'guest',
            'RABBITMQ_PASSWORD': 'guest',
            'RABBITMQ_VHOST': '/',
            'RABBITMQ_ROUTING_KEY': 'test_queue'
        }
        mock_get_config.return_value = mock_config
        
        mock_connection_class.side_effect = Exception("Connection failed")
        
        payload = {'exec_id': 123, 'rpa_key_id': 'job-001'}
        
        with patch('src.services.rabbitmq_service.time.sleep'):  # Mock sleep
            # Execute
            result = publish_execution_message(payload)
        
        # Verify
        assert result is False
        assert mock_connection_class.call_count == 3  # Default retry attempts
    
    @patch('src.services.rabbitmq_service.get_rabbitmq_config')
    def test_publish_config_error(self, mock_get_config):
        """Test when config retrieval fails."""
        # Setup
        mock_get_config.side_effect = Exception("Config error")
        
        payload = {'exec_id': 123, 'rpa_key_id': 'job-001'}
        
        # Execute
        result = publish_execution_message(payload)
        
        # Verify
        assert result is False
    
    @patch('src.services.rabbitmq_service.get_rabbitmq_config')
    @patch('src.services.rabbitmq_service.pika.BlockingConnection')
    def test_publish_message_structure(self, mock_connection_class, mock_get_config):
        """Test that published message has correct structure."""
        # Setup
        mock_config = {
            'RABBITMQ_HOST': 'localhost',
            'RABBITMQ_PORT': '5672',
            'RABBITMQ_USER': 'guest',
            'RABBITMQ_PASSWORD': 'guest',
            'RABBITMQ_VHOST': '/',
            'RABBITMQ_ROUTING_KEY': 'test_queue'
        }
        mock_get_config.return_value = mock_config
        
        mock_connection = MagicMock()
        mock_channel = MagicMock()
        mock_connection.channel.return_value = mock_channel
        mock_connection_class.return_value = mock_connection
        
        payload = {
            'exec_id': 123,
            'rpa_key_id': 'job-001',
            'callback_url': 'http://localhost:3000/callback',
            'rpa_request': {'nota_fiscal': '12345'}
        }
        
        # Execute
        publish_execution_message(payload)
        
        # Verify message structure
        mock_channel.basic_publish.assert_called_once()
        call_args = mock_channel.basic_publish.call_args
        
        assert call_args[1]['exchange'] == ''
        assert call_args[1]['routing_key'] == 'test_queue'
        assert call_args[1]['body'] == '{"exec_id":123,"rpa_key_id":"job-001","callback_url":"http://localhost:3000/callback","rpa_request":{"nota_fiscal":"12345"}}'
        assert call_args[1]['properties'].content_type == 'application/json'
        assert call_args[1]['properties'].delivery_mode == 2
