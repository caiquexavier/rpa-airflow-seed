"""Unit tests for execution use cases."""
import pytest
from datetime import datetime
from unittest.mock import Mock, patch

from src.domain.entities.execution import Execution, ExecutionStatus
from src.domain.events.execution_events import (
    ExecutionCreated, ExecutionCompleted, ExecutionFailed
)
from src.application.commands.create_execution_command import CreateExecutionCommand
from src.application.commands.update_execution_command import UpdateExecutionCommand
from src.application.queries.get_execution_query import GetExecutionQuery
from src.application.use_cases.execution_use_cases import (
    create_execution, update_execution, get_execution
)


@pytest.mark.unit
class TestCreateExecution:
    """Tests for create_execution use case."""

    def test_create_execution_success(
        self,
        sample_rpa_request: dict,
        mock_save_execution,
        mock_publish_event,
        mock_publish_message
    ):
        """Test successful execution creation."""
        command = CreateExecutionCommand(
            rpa_key_id="test_rpa",
            callback_url="http://example.com/callback",
            rpa_request=sample_rpa_request
        )

        with patch('src.infrastructure.repositories.saga_repository.get_saga_by_exec_id', return_value=None):
            exec_id, published = create_execution(
                command=command,
                save_execution=mock_save_execution,
                publish_event=mock_publish_event,
                publish_message=mock_publish_message
            )

        assert exec_id > 0
        assert published is True
        mock_save_execution.assert_called_once()
        mock_publish_event.assert_called_once()
        mock_publish_message.assert_called_once()

    def test_create_execution_without_callback_url(
        self,
        sample_rpa_request: dict,
        mock_save_execution,
        mock_publish_event,
        mock_publish_message
    ):
        """Test execution creation without callback URL."""
        command = CreateExecutionCommand(
            rpa_key_id="test_rpa",
            callback_url=None,
            rpa_request=sample_rpa_request
        )

        with patch('src.infrastructure.repositories.saga_repository.get_saga_by_exec_id', return_value=None):
            exec_id, published = create_execution(
                command=command,
                save_execution=mock_save_execution,
                publish_event=mock_publish_event,
                publish_message=mock_publish_message
            )

        assert exec_id > 0
        assert published is True

    def test_create_execution_with_empty_request(
        self,
        mock_save_execution,
        mock_publish_event,
        mock_publish_message
    ):
        """Test execution creation with empty request."""
        command = CreateExecutionCommand(
            rpa_key_id="test_rpa",
            callback_url=None,
            rpa_request=None
        )

        with patch('src.infrastructure.repositories.saga_repository.get_saga_by_exec_id', return_value=None):
            exec_id, published = create_execution(
                command=command,
                save_execution=mock_save_execution,
                publish_event=mock_publish_event,
                publish_message=mock_publish_message
            )

        assert exec_id > 0
        assert published is True

    def test_create_execution_publish_failure(
        self,
        sample_rpa_request: dict,
        mock_save_execution,
        mock_publish_event
    ):
        """Test execution creation when message publishing fails."""
        def mock_publish_failure(message: dict) -> bool:
            return False

        command = CreateExecutionCommand(
            rpa_key_id="test_rpa",
            callback_url="http://example.com/callback",
            rpa_request=sample_rpa_request
        )

        with patch('src.infrastructure.repositories.saga_repository.get_saga_by_exec_id', return_value=None):
            exec_id, published = create_execution(
                command=command,
                save_execution=mock_save_execution,
                publish_event=mock_publish_event,
                publish_message=mock_publish_failure
            )

        assert exec_id > 0
        assert published is False


@pytest.mark.unit
class TestUpdateExecution:
    """Tests for update_execution use case."""

    def test_update_execution_to_success(
        self,
        sample_execution: Execution,
        mock_get_execution,
        mock_save_execution,
        mock_publish_event
    ):
        """Test updating execution to SUCCESS status."""
        command = UpdateExecutionCommand(
            exec_id=sample_execution.exec_id,
            rpa_key_id=sample_execution.rpa_key_id,
            status=ExecutionStatus.SUCCESS,
            rpa_response={"result": "ok"},
            error_message=None
        )

        updated = update_execution(
            command=command,
            get_execution=mock_get_execution,
            save_execution=mock_save_execution,
            publish_event=mock_publish_event
        )

        assert updated.exec_status == ExecutionStatus.SUCCESS
        assert updated.rpa_response == {"result": "ok"}
        assert updated.finished_at is not None
        mock_save_execution.assert_called_once()
        mock_publish_event.assert_called_once()

    def test_update_execution_to_fail(
        self,
        sample_execution: Execution,
        mock_get_execution,
        mock_save_execution,
        mock_publish_event
    ):
        """Test updating execution to FAIL status."""
        command = UpdateExecutionCommand(
            exec_id=sample_execution.exec_id,
            rpa_key_id=sample_execution.rpa_key_id,
            status=ExecutionStatus.FAIL,
            rpa_response={},
            error_message="Test error"
        )

        updated = update_execution(
            command=command,
            get_execution=mock_get_execution,
            save_execution=mock_save_execution,
            publish_event=mock_publish_event
        )

        assert updated.exec_status == ExecutionStatus.FAIL
        assert updated.error_message == "Test error"
        assert updated.finished_at is not None

    def test_update_execution_to_running(
        self,
        sample_execution: Execution,
        mock_get_execution,
        mock_save_execution,
        mock_publish_event
    ):
        """Test updating execution to RUNNING status."""
        command = UpdateExecutionCommand(
            exec_id=sample_execution.exec_id,
            rpa_key_id=sample_execution.rpa_key_id,
            status=ExecutionStatus.RUNNING,
            rpa_response={},
            error_message=None
        )

        updated = update_execution(
            command=command,
            get_execution=mock_get_execution,
            save_execution=mock_save_execution,
            publish_event=mock_publish_event
        )

        assert updated.exec_status == ExecutionStatus.RUNNING
        assert updated.finished_at is None

    def test_update_execution_not_found(
        self,
        mock_save_execution,
        mock_publish_event
    ):
        """Test updating non-existent execution raises error."""
        def mock_get_none(exec_id: int):
            return None

        command = UpdateExecutionCommand(
            exec_id=999,
            rpa_key_id="test_rpa",
            status=ExecutionStatus.SUCCESS,
            rpa_response={},
            error_message=None
        )

        with pytest.raises(ValueError, match="Execution 999 not found"):
            update_execution(
                command=command,
                get_execution=mock_get_none,
                save_execution=mock_save_execution,
                publish_event=mock_publish_event
            )

    def test_update_execution_rpa_key_mismatch(
        self,
        sample_execution: Execution,
        mock_get_execution,
        mock_save_execution,
        mock_publish_event
    ):
        """Test updating execution with wrong rpa_key_id raises error."""
        command = UpdateExecutionCommand(
            exec_id=sample_execution.exec_id,
            rpa_key_id="wrong_key",
            status=ExecutionStatus.SUCCESS,
            rpa_response={},
            error_message=None
        )

        with pytest.raises(ValueError, match="RPA key ID mismatch"):
            update_execution(
                command=command,
                get_execution=mock_get_execution,
                save_execution=mock_save_execution,
                publish_event=mock_publish_event
            )

    def test_update_execution_idempotent_terminal(
        self,
        sample_execution: Execution,
        mock_get_execution,
        mock_save_execution,
        mock_publish_event
    ):
        """Test idempotent update to terminal state."""
        success_execution = Execution(
            exec_id=sample_execution.exec_id,
            rpa_key_id=sample_execution.rpa_key_id,
            exec_status=ExecutionStatus.SUCCESS,
            rpa_request=sample_execution.rpa_request,
            rpa_response={"result": "ok"},
            error_message=None,
            callback_url=sample_execution.callback_url,
            created_at=sample_execution.created_at,
            updated_at=sample_execution.updated_at,
            finished_at=datetime.utcnow()
        )

        def mock_get_success(exec_id: int):
            return success_execution

        command = UpdateExecutionCommand(
            exec_id=success_execution.exec_id,
            rpa_key_id=success_execution.rpa_key_id,
            status=ExecutionStatus.SUCCESS,
            rpa_response={"result": "ok"},
            error_message=None
        )

        result = update_execution(
            command=command,
            get_execution=mock_get_success,
            save_execution=mock_save_execution,
            publish_event=mock_publish_event
        )

        assert result == success_execution
        mock_save_execution.assert_not_called()
        mock_publish_event.assert_not_called()

    def test_update_execution_invalid_transition(
        self,
        sample_execution: Execution,
        mock_get_execution,
        mock_save_execution,
        mock_publish_event
    ):
        """Test updating execution with invalid transition raises error."""
        success_execution = Execution(
            exec_id=sample_execution.exec_id,
            rpa_key_id=sample_execution.rpa_key_id,
            exec_status=ExecutionStatus.SUCCESS,
            rpa_request=sample_execution.rpa_request,
            rpa_response={"result": "ok"},
            error_message=None,
            callback_url=sample_execution.callback_url,
            created_at=sample_execution.created_at,
            updated_at=sample_execution.updated_at,
            finished_at=datetime.utcnow()
        )

        def mock_get_success(exec_id: int):
            return success_execution

        command = UpdateExecutionCommand(
            exec_id=success_execution.exec_id,
            rpa_key_id=success_execution.rpa_key_id,
            status=ExecutionStatus.FAIL,
            rpa_response={},
            error_message="New error"
        )

        with pytest.raises(ValueError, match="already in terminal state"):
            update_execution(
                command=command,
                get_execution=mock_get_success,
                save_execution=mock_save_execution,
                publish_event=mock_publish_event
            )


@pytest.mark.unit
class TestGetExecution:
    """Tests for get_execution use case."""

    def test_get_execution_success(
        self,
        sample_execution: Execution,
        mock_get_execution
    ):
        """Test getting existing execution."""
        query = GetExecutionQuery(exec_id=sample_execution.exec_id)

        result = get_execution(
            query=query,
            get_execution=mock_get_execution
        )

        assert result == sample_execution
        assert result.exec_id == sample_execution.exec_id

    def test_get_execution_not_found(self):
        """Test getting non-existent execution returns None."""
        def mock_get_none(exec_id: int):
            return None

        query = GetExecutionQuery(exec_id=999)

        result = get_execution(
            query=query,
            get_execution=mock_get_none
        )

        assert result is None

