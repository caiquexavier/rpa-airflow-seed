"""Unit tests for request controller."""
import pytest
from unittest.mock import patch

from src.controllers.request_controller import handle_request_rpa_exec
from src.validations.request_models import RpaRequestModel


class TestHandleRequestRpaExec:
    """Test handle_request_rpa_exec function."""
    
    @patch('src.controllers.request_controller.publish_execution_message')
    @patch('src.controllers.request_controller.insert_exec_record')
    def test_successful_request_with_callback(self, mock_insert, mock_publish):
        """Test successful request with callback URL."""
        # Setup
        mock_insert.return_value = 123
        
        payload = RpaRequestModel(
            rpa_key_id="job-001",
            callback_url="http://localhost:3000/callback",
            rpa_request={"nota_fiscal": "12345"}
        )
        
        # Execute
        result = handle_request_rpa_exec(payload)
        
        # Verify
        assert result["status"] == "queued"
        assert result["rpa_id"] == "job-001"
        assert result["has_callback"] is True
        
        mock_insert.assert_called_once()
        mock_publish.assert_called_once()
    
    @patch('src.controllers.request_controller.publish_execution_message')
    @patch('src.controllers.request_controller.insert_exec_record')
    def test_successful_request_without_callback(self, mock_insert, mock_publish):
        """Test successful request without callback URL."""
        # Setup
        mock_insert.return_value = 123
        
        payload = RpaRequestModel(rpa_key_id="job-001")
        
        # Execute
        result = handle_request_rpa_exec(payload)
        
        # Verify
        assert result["status"] == "queued"
        assert result["rpa_id"] == "job-001"
        assert result["has_callback"] is False
        
        mock_insert.assert_called_once()
        mock_publish.assert_called_once()
    
    @patch('src.controllers.request_controller.publish_execution_message')
    @patch('src.controllers.request_controller.insert_exec_record')
    def test_database_insert_fails(self, mock_insert, mock_publish):
        """Test when database insert fails."""
        # Setup
        mock_insert.side_effect = Exception("Database error")
        
        payload = RpaRequestModel(rpa_key_id="job-001")
        
        # Execute
        result = handle_request_rpa_exec(payload)
        
        # Verify - should continue with RabbitMQ even if DB fails
        assert result["status"] == "queued"
        assert result["rpa_id"] == "job-001"
        assert result["has_callback"] is False
        
        mock_insert.assert_called_once()
        mock_publish.assert_called_once()
    
    @patch('src.controllers.request_controller.publish_execution_message')
    @patch('src.controllers.request_controller.insert_exec_record')
    def test_message_structure(self, mock_insert, mock_publish):
        """Test that message has correct structure."""
        # Setup
        mock_insert.return_value = 123
        
        payload = RpaRequestModel(
            rpa_key_id="job-001",
            callback_url="http://localhost:3000/callback",
            rpa_request={"nota_fiscal": "12345"}
        )
        
        # Execute
        handle_request_rpa_exec(payload)
        
        # Verify message structure
        mock_publish.assert_called_once()
        message = mock_publish.call_args[0][0]
        
        assert message["rpa_id"] == "job-001"
        assert message["callback_url"] == "http://localhost:3000/callback"
        assert message["rpa_request"] == {"nota_fiscal": "12345"}
        assert message["exec_id"] == 123
