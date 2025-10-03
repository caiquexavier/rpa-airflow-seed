"""Unit tests for publish controller."""
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.main import app

client = TestClient(app)


class TestPublishController:
    """Test cases for publish controller."""
    
    @patch('src.controllers.publish_controller.QueueService')
    def test_publish_success_with_extra_fields(self, mock_queue_service):
        """Test that extra fields are filtered out and only rpa-id is sent to queue."""
        mock_service_instance = mock_queue_service.return_value
        
        # Test payload with extra fields
        payload = {
            "rpa-id": "job-001",
            "extra_field": "should_be_ignored",
            "nested": {"data": "also_ignored"},
            "array": [1, 2, 3]
        }
        
        response = client.post("/publish/", json=payload)
        
        assert response.status_code == 202
        assert response.json() == {"status": "queued", "rpa-id": "job-001"}
        
        # Verify that only the clean payload was sent to the queue service
        mock_service_instance.publish.assert_called_once_with({"rpa-id": "job-001"})
    
    @patch('src.controllers.publish_controller.QueueService')
    def test_publish_success_minimal_payload(self, mock_queue_service):
        """Test publishing with minimal payload (only rpa-id)."""
        mock_service_instance = mock_queue_service.return_value
        
        payload = {"rpa-id": "job-002"}
        
        response = client.post("/publish/", json=payload)
        
        assert response.status_code == 202
        assert response.json() == {"status": "queued", "rpa-id": "job-002"}
        
        # Verify the payload was sent correctly
        mock_service_instance.publish.assert_called_once_with({"rpa-id": "job-002"})
    
    def test_publish_missing_rpa_id(self):
        """Test that missing rpa-id returns 422."""
        payload = {"other_field": "value"}
        
        response = client.post("/publish/", json=payload)
        
        assert response.status_code == 422
        assert "Validation error" in response.json()["detail"]
    
    def test_publish_empty_rpa_id(self):
        """Test that empty rpa-id returns 422."""
        payload = {"rpa-id": ""}
        
        response = client.post("/publish/", json=payload)
        
        assert response.status_code == 422
        assert "Validation error" in response.json()["detail"]
    
    def test_publish_invalid_rpa_id_type(self):
        """Test that non-string rpa-id returns 422."""
        payload = {"rpa-id": 123}
        
        response = client.post("/publish/", json=payload)
        
        assert response.status_code == 422
        assert "Validation error" in response.json()["detail"]
    
    @patch('src.controllers.publish_controller.QueueService')
    def test_publish_queue_error_returns_503(self, mock_queue_service):
        """Test that queue service errors return 503."""
        from src.services.queue_service import QueuePublishError
        
        mock_service_instance = mock_queue_service.return_value
        mock_service_instance.publish.side_effect = QueuePublishError("Queue unavailable")
        
        payload = {"rpa-id": "job-003"}
        
        response = client.post("/publish/", json=payload)
        
        assert response.status_code == 503
        assert response.json()["detail"] == "queue_unavailable"
