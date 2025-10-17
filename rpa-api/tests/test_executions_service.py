"""Unit tests for execution service."""
import pytest
from unittest.mock import patch, MagicMock

from src.services.executions_service import (
    create_execution, update_execution_status, 
    set_execution_running, get_execution
)
from src.validations.executions_models import ExecutionStatus


class TestCreateExecution:
    """Test create_execution function."""
    
    @patch('src.services.executions_service.execute_insert')
    def test_create_execution_success(self, mock_execute_insert):
        """Test successful execution creation."""
        mock_execute_insert.return_value = 123
        
        payload = {
            "rpa_key_id": "job-001",
            "callback_url": "http://localhost:3000/callback",
            "rpa_request": {"nota_fiscal": "12345"}
        }
        
        exec_id = create_execution(payload)
        
        assert exec_id == 123
        mock_execute_insert.assert_called_once()
    
    @patch('src.services.executions_service.execute_insert')
    def test_create_execution_database_error(self, mock_execute_insert):
        """Test execution creation with database error."""
        mock_execute_insert.side_effect = Exception("Database error")
        
        payload = {"rpa_key_id": "job-001"}
        
        with pytest.raises(Exception) as exc_info:
            create_execution(payload)
        
        assert "Failed to create execution record" in str(exc_info.value)


class TestUpdateExecutionStatus:
    """Test update_execution_status function."""
    
    @patch('src.services.executions_service.execute_query')
    @patch('src.services.executions_service.execute_update')
    def test_update_execution_success(self, mock_execute_update, mock_execute_query):
        """Test successful execution update."""
        mock_execute_query.return_value = [(123, "PENDING")]
        mock_execute_update.return_value = 1
        
        result = update_execution_status(
            exec_id=123,
            rpa_key_id="job-001",
            status=ExecutionStatus.SUCCESS,
            rpa_response={"files": ["pod.pdf"]}
        )
        
        assert result is True
        mock_execute_query.assert_called_once()
        mock_execute_update.assert_called_once()
    
    @patch('src.services.executions_service.execute_query')
    def test_update_execution_not_found(self, mock_execute_query):
        """Test update execution that doesn't exist."""
        mock_execute_query.return_value = []
        
        result = update_execution_status(
            exec_id=999,
            rpa_key_id="job-001",
            status=ExecutionStatus.SUCCESS,
            rpa_response={}
        )
        
        assert result is False
    
    @patch('src.services.executions_service.execute_query')
    def test_update_execution_already_terminal(self, mock_execute_query):
        """Test update execution that's already in terminal state."""
        mock_execute_query.return_value = [(123, "SUCCESS")]
        
        with pytest.raises(ValueError) as exc_info:
            update_execution_status(
                exec_id=123,
                rpa_key_id="job-001",
                status=ExecutionStatus.FAIL,
                rpa_response={}
            )
        
        assert "already in terminal state" in str(exc_info.value)
    
    @patch('src.services.executions_service.execute_query')
    def test_update_execution_idempotent(self, mock_execute_query):
        """Test idempotent update with same terminal status."""
        mock_execute_query.return_value = [(123, "SUCCESS")]
        
        result = update_execution_status(
            exec_id=123,
            rpa_key_id="job-001",
            status=ExecutionStatus.SUCCESS,
            rpa_response={"files": ["pod.pdf"]}
        )
        
        assert result is True


class TestSetExecutionRunning:
    """Test set_execution_running function."""
    
    @patch('src.services.executions_service.execute_update')
    def test_set_running_success(self, mock_execute_update):
        """Test successful status update to RUNNING."""
        mock_execute_update.return_value = 1
        
        result = set_execution_running(123)
        
        assert result is True
        mock_execute_update.assert_called_once()
    
    @patch('src.services.executions_service.execute_update')
    def test_set_running_database_error(self, mock_execute_update):
        """Test set running with database error."""
        mock_execute_update.side_effect = Exception("Database error")
        
        with pytest.raises(Exception) as exc_info:
            set_execution_running(123)
        
        assert "Failed to update execution status" in str(exc_info.value)


class TestGetExecution:
    """Test get_execution function."""
    
    @patch('src.services.executions_service.execute_query')
    def test_get_execution_success(self, mock_execute_query):
        """Test successful execution retrieval."""
        mock_execute_query.return_value = [(
            123, "job-001", "SUCCESS", 
            {"nota_fiscal": "12345"}, 
            {"files": ["pod.pdf"]},
            "http://localhost:3000/callback",
            "2023-01-01T00:00:00Z",
            "2023-01-01T00:01:00Z",
            "2023-01-01T00:01:00Z",
            None
        )]
        
        result = get_execution(123)
        
        assert result is not None
        assert result["exec_id"] == 123
        assert result["rpa_key_id"] == "job-001"
        assert result["exec_status"] == "SUCCESS"
    
    @patch('src.services.executions_service.execute_query')
    def test_get_execution_not_found(self, mock_execute_query):
        """Test get execution that doesn't exist."""
        mock_execute_query.return_value = []
        
        result = get_execution(999)
        
        assert result is None
