"""Integration tests for execution endpoints."""
import pytest
import requests
import json
from unittest.mock import patch


class TestExecutionEndpoints:
    """Integration tests for execution endpoints."""
    
    @pytest.fixture
    def base_url(self):
        """Base URL for API requests."""
        return "http://localhost:3000"
    
    @pytest.fixture
    def valid_request_payload(self):
        """Valid request payload for testing."""
        return {
            "rpa_key_id": "job-001",
            "callback_url": "http://localhost:3000/updateRpaExecution",
            "rpa_request": {"nota_fiscal": "12345"}
        }
    
    @pytest.fixture
    def valid_update_payload(self):
        """Valid update payload for testing."""
        return {
            "exec_id": 123,
            "rpa_key_id": "job-001",
            "rpa_response": {"files": ["pod.pdf"]},
            "status": "SUCCESS",
            "error_message": None
        }
    
    def test_request_rpa_exec_success(self, base_url, valid_request_payload):
        """Test successful RPA execution request."""
    with patch('src.services.executions_service.create_execution') as mock_insert, \
         patch('src.services.rabbitmq_service.publish_execution_message') as mock_publish:
            
            mock_insert.return_value = 123
            mock_publish.return_value = True
            
            response = requests.post(
                f"{base_url}/request_rpa_exec",
                json=valid_request_payload,
                headers={"Content-Type": "application/json"}
            )
            
            assert response.status_code == 202
            data = response.json()
            assert "exec_id" in data
            assert data["rpa_key_id"] == "job-001"
            assert data["status"] == "ENQUEUED"
            assert data["published"] is True
    
    def test_request_rpa_exec_validation_error(self, base_url):
        """Test RPA execution request with validation error."""
        invalid_payload = {
            "rpa_key_id": "",  # Empty string should be rejected
            "callback_url": "not-a-url"
        }
        
        response = requests.post(
            f"{base_url}/request_rpa_exec",
            json=invalid_payload,
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_update_rpa_execution_success(self, base_url, valid_update_payload):
        """Test successful execution status update."""
    with patch('src.services.executions_service.get_execution') as mock_get, \
         patch('src.services.executions_service.update_execution_status') as mock_update:
            
            mock_get.return_value = {
                "exec_id": 123,
                "rpa_key_id": "job-001",
                "exec_status": "PENDING"
            }
            mock_update.return_value = True
            
            response = requests.post(
                f"{base_url}/updateRpaExecution",
                json=valid_update_payload,
                headers={"Content-Type": "application/json"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["exec_id"] == 123
            assert data["updated"] is True
            assert data["status"] == "SUCCESS"
    
    def test_update_rpa_execution_not_found(self, base_url, valid_update_payload):
        """Test execution update for non-existent execution."""
        with patch('src.services.executions_service.get_execution') as mock_get:
            mock_get.return_value = None
            
            response = requests.post(
                f"{base_url}/updateRpaExecution",
                json=valid_update_payload,
                headers={"Content-Type": "application/json"}
            )
            
            assert response.status_code == 404
    
    def test_update_rpa_execution_validation_error(self, base_url):
        """Test execution update with validation error."""
        invalid_payload = {
            "exec_id": 123,
            "rpa_key_id": "job-001",
            "rpa_response": {},
            "status": "FAIL"  # Missing required error_message
        }
        
        response = requests.post(
            f"{base_url}/updateRpaExecution",
            json=invalid_payload,
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_update_rpa_execution_idempotent(self, base_url, valid_update_payload):
        """Test idempotent execution update."""
    with patch('src.services.executions_service.get_execution') as mock_get, \
         patch('src.services.executions_service.update_execution_status') as mock_update:
            
            # Execution already in SUCCESS state
            mock_get.return_value = {
                "exec_id": 123,
                "rpa_key_id": "job-001",
                "exec_status": "SUCCESS"
            }
            mock_update.return_value = True
            
            response = requests.post(
                f"{base_url}/updateRpaExecution",
                json=valid_update_payload,
                headers={"Content-Type": "application/json"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["updated"] is True
    
    def test_update_rpa_execution_conflict(self, base_url):
        """Test execution update with conflicting status."""
        with patch('src.services.executions_service.get_execution') as mock_get:
            # Execution already in SUCCESS state
            mock_get.return_value = {
                "exec_id": 123,
                "rpa_key_id": "job-001",
                "exec_status": "SUCCESS"
            }
            
            # Try to update to FAIL (conflict)
            conflict_payload = {
                "exec_id": 123,
                "rpa_key_id": "job-001",
                "rpa_response": {},
                "status": "FAIL",
                "error_message": "Test error"
            }
            
            response = requests.post(
                f"{base_url}/updateRpaExecution",
                json=conflict_payload,
                headers={"Content-Type": "application/json"}
            )
            
            assert response.status_code == 404  # Should be rejected
