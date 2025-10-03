"""Unit tests for queue service."""
import pytest
from unittest.mock import patch

from src.services.queue_service import QueueService, QueuePublishError


class TestQueueService:
    """Test cases for QueueService."""
    
    @patch('src.services.queue_service.publish_json')
    def test_publish_success(self, mock_publish_json):
        """Test successful message publishing."""
        mock_publish_json.return_value = True
        
        service = QueueService()
        payload = {"rpa-id": "test-123", "data": "value"}
        
        # Should not raise an exception
        service.publish(payload)
        
        # Verify publish_json was called with the payload
        mock_publish_json.assert_called_once_with(payload)
    
    @patch('src.services.queue_service.publish_json')
    def test_publish_failure_raises_error(self, mock_publish_json):
        """Test that publish failure raises QueuePublishError."""
        mock_publish_json.return_value = False
        
        service = QueueService()
        payload = {"rpa-id": "test-123"}
        
        with pytest.raises(QueuePublishError) as exc_info:
            service.publish(payload)
        
        assert "Failed to publish message to queue" in str(exc_info.value)
    
    @patch('src.services.queue_service.publish_json')
    def test_publish_with_publish_json(self, mock_publish_json):
        """Test publishing using the publish_json convenience function."""
        mock_publish_json.return_value = True
        
        service = QueueService()
        payload = {"rpa-id": "test-456", "extra": "data"}
        
        # Should not raise an exception
        service.publish(payload)
        
        # Verify publish_json was called with the payload
        mock_publish_json.assert_called_once_with(payload)
    
    @patch('src.services.queue_service.publish_json')
    def test_publish_exception_handling(self, mock_publish_json):
        """Test that exceptions during publishing are properly handled."""
        mock_publish_json.side_effect = Exception("Connection failed")
        
        service = QueueService()
        payload = {"rpa-id": "test-789"}
        
        with pytest.raises(QueuePublishError) as exc_info:
            service.publish(payload)
        
        assert "Queue publishing failed" in str(exc_info.value)
        assert "Connection failed" in str(exc_info.value)
