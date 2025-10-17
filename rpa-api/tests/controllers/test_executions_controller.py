"""Unit tests for executions controller."""
import pytest
from unittest.mock import patch, MagicMock

from src.controllers.executions_controller import (
    handle_request_rpa_exec, handle_update_rpa_execution
)
from src.validations.executions_models import (
    RpaExecutionRequestModel, UpdateExecutionRequestModel, ExecutionStatus
)


class TestHandleRequestRpaExec:
    """Test handle_request_rpa_exec function."""
    
    @patch('src.controllers.executions_controller.publish_execution_message')
    @patch('src.controllers.executions_controller.set_execution_running')
    @patch('src.controllers.executions_controller.create_execution')
    def test_successful_request(self, mock_create, mock_set_running, mock_publish):
        """Test successful execution request."""
        # Setup
        mock_create.return_value = 123
        mock_publish.return_value = True
        
        payload = RpaExecutionRequestModel(
            rpa_key_id="job-001",
            callback_url="http://localhost:3000/callback",
            rpa_request={"nota_fiscal": "12345"}
        )
        
        # Execute
        result = handle_request_rpa_exec(payload)
        
        # Verify
        assert result.exec_id == 123
        assert result.rpa_key_id == "job-001"
        assert result.status == "ENQUEUED"
        assert result.published is True
        
        mock_create.assert_called_once()
        mock_publish.assert_called_once()
        mock_set_running.assert_called_once_with(123)
    
    @patch('src.controllers.executions_controller.create_execution')
    def test_create_execution_fails(self, mock_create):
        """Test when execution creation fails."""
        mock_create.return_value = None
        
        payload = RpaExecutionRequestModel(rpa_key_id="job-001")
        
        with pytest.raises(Exception) as exc_info:
            handle_request_rpa_exec(payload)
        
        assert "Failed to create execution record" in str(exc_info.value)
    
    @patch('src.controllers.executions_controller.publish_execution_message')
    @patch('src.controllers.executions_controller.create_execution')
    def test_publish_fails(self, mock_create, mock_publish):
        """Test when message publishing fails."""
        mock_create.return_value = 123
        mock_publish.return_value = False
        
        payload = RpaExecutionRequestModel(rpa_key_id="job-001")
        
        result = handle_request_rpa_exec(payload)
        
        assert result.status == "FAILED"
        assert result.published is False


class TestHandleUpdateRpaExecution:
    """Test handle_update_rpa_execution function."""
    
    @patch('src.controllers.executions_controller.update_execution_status')
    @patch('src.controllers.executions_controller.get_execution')
    def test_successful_update(self, mock_get, mock_update):
        """Test successful execution update."""
        # Setup
        mock_get.return_value = {
            "exec_id": 123,
            "rpa_key_id": "job-001",
            "exec_status": "PENDING"
        }
        mock_update.return_value = True
        
        payload = UpdateExecutionRequestModel(
            exec_id=123,
            rpa_key_id="job-001",
            rpa_response={"files": ["pod.pdf"]},
            status=ExecutionStatus.SUCCESS
        )
        
        # Execute
        result = handle_update_rpa_execution(payload)
        
        # Verify
        assert result.exec_id == 123
        assert result.updated is True
        assert result.status == "SUCCESS"
        
        mock_get.assert_called_once_with(123)
        mock_update.assert_called_once()
    
    @patch('src.controllers.executions_controller.get_execution')
    def test_execution_not_found(self, mock_get):
        """Test when execution is not found."""
        mock_get.return_value = None
        
        payload = UpdateExecutionRequestModel(
            exec_id=999,
            rpa_key_id="job-001",
            rpa_response={},
            status=ExecutionStatus.SUCCESS
        )
        
        with pytest.raises(ValueError) as exc_info:
            handle_update_rpa_execution(payload)
        
        assert "Execution 999 not found" in str(exc_info.value)
    
    @patch('src.controllers.executions_controller.get_execution')
    def test_rpa_key_id_mismatch(self, mock_get):
        """Test when rpa_key_id doesn't match."""
        mock_get.return_value = {
            "exec_id": 123,
            "rpa_key_id": "different-job",
            "exec_status": "PENDING"
        }
        
        payload = UpdateExecutionRequestModel(
            exec_id=123,
            rpa_key_id="job-001",
            rpa_response={},
            status=ExecutionStatus.SUCCESS
        )
        
        with pytest.raises(ValueError) as exc_info:
            handle_update_rpa_execution(payload)
        
        assert "RPA key ID mismatch for execution 123" in str(exc_info.value)
    
    @patch('src.controllers.executions_controller.get_execution')
    def test_already_terminal_state_idempotent(self, mock_get):
        """Test idempotent update for terminal state."""
        mock_get.return_value = {
            "exec_id": 123,
            "rpa_key_id": "job-001",
            "exec_status": "SUCCESS"
        }
        
        payload = UpdateExecutionRequestModel(
            exec_id=123,
            rpa_key_id="job-001",
            rpa_response={"files": ["pod.pdf"]},
            status=ExecutionStatus.SUCCESS
        )
        
        with patch('src.controllers.executions_controller.update_execution_status') as mock_update:
            mock_update.return_value = True
            
            result = handle_update_rpa_execution(payload)
            
            assert result.updated is True
            assert result.status == "SUCCESS"
    
    @patch('src.controllers.executions_controller.get_execution')
    def test_already_terminal_state_conflict(self, mock_get):
        """Test conflict when trying to change terminal state."""
        mock_get.return_value = {
            "exec_id": 123,
            "rpa_key_id": "job-001",
            "exec_status": "SUCCESS"
        }
        
        payload = UpdateExecutionRequestModel(
            exec_id=123,
            rpa_key_id="job-001",
            rpa_response={},
            status=ExecutionStatus.FAIL,
            error_message="Test error"
        )
        
        with patch('src.controllers.executions_controller.update_execution_status') as mock_update:
            mock_update.side_effect = ValueError("Execution 123 is already in terminal state: SUCCESS")
            
            with pytest.raises(ValueError) as exc_info:
                handle_update_rpa_execution(payload)
            
            assert "already in terminal state" in str(exc_info.value)
