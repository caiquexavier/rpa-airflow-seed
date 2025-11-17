"""Unit tests for execution repository."""
import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from src.domain.entities.execution import Execution, ExecutionStatus
from src.infrastructure.repositories.execution_repository import (
    save_execution, get_execution, set_execution_running
)


@pytest.mark.unit
class TestSaveExecution:
    """Tests for save_execution function."""

    @patch('src.infrastructure.repositories.execution_repository.execute_insert')
    def test_save_new_execution(self, mock_insert, sample_execution: Execution):
        """Test saving a new execution (insert)."""
        new_execution = Execution(
            exec_id=0,
            rpa_key_id=sample_execution.rpa_key_id,
            exec_status=sample_execution.exec_status,
            rpa_request=sample_execution.rpa_request,
            rpa_response=None,
            error_message=None,
            callback_url=sample_execution.callback_url,
            created_at=sample_execution.created_at,
            updated_at=sample_execution.updated_at,
            finished_at=None
        )
        mock_insert.return_value = 1

        exec_id = save_execution(new_execution)

        assert exec_id == 1
        mock_insert.assert_called_once()

    @patch('src.infrastructure.repositories.execution_repository.execute_update')
    def test_save_existing_execution(self, mock_update, sample_execution: Execution):
        """Test saving an existing execution (update)."""
        exec_id = save_execution(sample_execution)

        assert exec_id == sample_execution.exec_id
        mock_update.assert_called_once()

    @patch('src.infrastructure.repositories.execution_repository.execute_insert')
    def test_save_execution_with_none_id(self, mock_insert, sample_execution: Execution):
        """Test saving execution when insert returns None."""
        new_execution = Execution(
            exec_id=0,
            rpa_key_id=sample_execution.rpa_key_id,
            exec_status=sample_execution.exec_status,
            rpa_request=sample_execution.rpa_request,
            rpa_response=None,
            error_message=None,
            callback_url=sample_execution.callback_url,
            created_at=sample_execution.created_at,
            updated_at=sample_execution.updated_at,
            finished_at=None
        )
        mock_insert.return_value = None

        exec_id = save_execution(new_execution)

        assert exec_id == 0


@pytest.mark.unit
class TestGetExecution:
    """Tests for get_execution function."""

    @patch('src.infrastructure.repositories.execution_repository.execute_query')
    def test_get_execution_success(self, mock_query, sample_execution: Execution):
        """Test getting an existing execution."""
        mock_query.return_value = [{
            "exec_id": sample_execution.exec_id,
            "rpa_key_id": sample_execution.rpa_key_id,
            "exec_status": sample_execution.exec_status.value,
            "rpa_request": '{"key": "value"}',
            "rpa_response": None,
            "callback_url": sample_execution.callback_url,
            "created_at": sample_execution.created_at,
            "updated_at": sample_execution.updated_at,
            "finished_at": None,
            "error_message": None
        }]

        result = get_execution(sample_execution.exec_id)

        assert result is not None
        assert result.exec_id == sample_execution.exec_id
        assert result.rpa_key_id == sample_execution.rpa_key_id

    @patch('src.infrastructure.repositories.execution_repository.execute_query')
    def test_get_execution_not_found(self, mock_query):
        """Test getting non-existent execution."""
        mock_query.return_value = []

        result = get_execution(999)

        assert result is None

    @patch('src.infrastructure.repositories.execution_repository.execute_query')
    def test_get_execution_with_json_strings(self, mock_query):
        """Test getting execution with JSON string fields."""
        mock_query.return_value = [{
            "exec_id": 1,
            "rpa_key_id": "test_rpa",
            "exec_status": "SUCCESS",
            "rpa_request": '{"dt_list": []}',
            "rpa_response": '{"result": "ok"}',
            "callback_url": "http://example.com",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "finished_at": datetime.utcnow(),
            "error_message": None
        }]

        result = get_execution(1)

        assert result is not None
        assert isinstance(result.rpa_request, dict)
        assert isinstance(result.rpa_response, dict)


@pytest.mark.unit
class TestSetExecutionRunning:
    """Tests for set_execution_running function."""

    @patch('src.infrastructure.repositories.execution_repository.execute_update')
    def test_set_execution_running_success(self, mock_update):
        """Test setting execution to RUNNING status."""
        mock_update.return_value = 1

        result = set_execution_running(1)

        assert result is True
        mock_update.assert_called_once()

    @patch('src.infrastructure.repositories.execution_repository.execute_update')
    def test_set_execution_running_no_rows(self, mock_update):
        """Test setting execution when no rows are affected."""
        mock_update.return_value = 0

        result = set_execution_running(999)

        assert result is False

