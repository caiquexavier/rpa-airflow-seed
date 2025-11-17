"""Extended unit tests for execution use cases - additional scenarios."""
import pytest
from datetime import datetime
from unittest.mock import Mock, patch

from src.domain.entities.execution import Execution, ExecutionStatus
from src.domain.entities.saga import Saga, SagaState
from src.domain.events.execution_events import (
    ExecutionCreated, ExecutionCompleted, ExecutionFailed
)
from src.application.commands.create_execution_command import CreateExecutionCommand
from src.application.commands.update_execution_command import UpdateExecutionCommand
from src.application.use_cases.execution_use_cases import (
    create_execution, update_execution
)


@pytest.mark.unit
class TestCreateExecutionExtended:
    """Extended tests for create_execution use case."""

    @patch('src.infrastructure.repositories.saga_repository.get_saga_by_exec_id')
    def test_create_execution_with_saga(
        self,
        mock_get_saga,
        sample_rpa_request: dict,
        mock_save_execution,
        mock_publish_event,
        mock_publish_message
    ):
        """Test execution creation when saga exists."""
        command = CreateExecutionCommand(
            rpa_key_id="test_rpa",
            callback_url="http://example.com/callback",
            rpa_request=sample_rpa_request
        )

        mock_saga = Saga(
            saga_id=1,
            exec_id=1,
            rpa_key_id="test_rpa",
            rpa_request_object=sample_rpa_request,
            current_state=SagaState.RUNNING,
            events=[],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        mock_get_saga.return_value = mock_saga

        exec_id, published = create_execution(
            command=command,
            save_execution=mock_save_execution,
            publish_event=mock_publish_event,
            publish_message=mock_publish_message
        )

        assert exec_id > 0
        assert published is True
        # Verify saga was included in message
        call_args = mock_publish_message.call_args[0][0]
        assert "saga" in call_args
        assert call_args["saga"]["saga_id"] == 1

    @patch('src.infrastructure.repositories.saga_repository.get_saga_by_exec_id')
    def test_create_execution_without_saga(
        self,
        mock_get_saga,
        sample_rpa_request: dict,
        mock_save_execution,
        mock_publish_event,
        mock_publish_message
    ):
        """Test execution creation when saga doesn't exist yet."""
        command = CreateExecutionCommand(
            rpa_key_id="test_rpa",
            callback_url="http://example.com/callback",
            rpa_request=sample_rpa_request
        )

        mock_get_saga.return_value = None

        exec_id, published = create_execution(
            command=command,
            save_execution=mock_save_execution,
            publish_event=mock_publish_event,
            publish_message=mock_publish_message
        )

        assert exec_id > 0
        assert published is True
        # Verify saga structure in message (without saga_id)
        call_args = mock_publish_message.call_args[0][0]
        assert "saga" in call_args
        assert call_args["saga"]["current_state"] == "PENDING"


@pytest.mark.unit
class TestUpdateExecutionExtended:
    """Extended tests for update_execution use case."""

    def test_update_execution_publishes_completed_event(
        self,
        sample_execution: Execution,
        mock_get_execution,
        mock_save_execution,
        mock_publish_event
    ):
        """Test that update to SUCCESS publishes ExecutionCompleted event."""
        command = UpdateExecutionCommand(
            exec_id=sample_execution.exec_id,
            rpa_key_id=sample_execution.rpa_key_id,
            status=ExecutionStatus.SUCCESS,
            rpa_response={"notas_fiscais": []},
            error_message=None
        )

        updated = update_execution(
            command=command,
            get_execution=mock_get_execution,
            save_execution=mock_save_execution,
            publish_event=mock_publish_event
        )

        assert updated.exec_status == ExecutionStatus.SUCCESS
        # Verify ExecutionCompleted event was published
        published_event = mock_publish_event.call_args[0][0]
        assert isinstance(published_event, ExecutionCompleted)
        assert published_event.exec_id == updated.exec_id

    def test_update_execution_publishes_failed_event(
        self,
        sample_execution: Execution,
        mock_get_execution,
        mock_save_execution,
        mock_publish_event
    ):
        """Test that update to FAIL publishes ExecutionFailed event."""
        command = UpdateExecutionCommand(
            exec_id=sample_execution.exec_id,
            rpa_key_id=sample_execution.rpa_key_id,
            status=ExecutionStatus.FAIL,
            rpa_response={"error": "Test error"},
            error_message="Test error"
        )

        updated = update_execution(
            command=command,
            get_execution=mock_get_execution,
            save_execution=mock_save_execution,
            publish_event=mock_publish_event
        )

        assert updated.exec_status == ExecutionStatus.FAIL
        # Verify ExecutionFailed event was published
        published_event = mock_publish_event.call_args[0][0]
        assert isinstance(published_event, ExecutionFailed)
        assert published_event.error_message == "Test error"

    def test_update_execution_sets_finished_at_for_terminal(
        self,
        sample_execution: Execution,
        mock_get_execution,
        mock_save_execution,
        mock_publish_event
    ):
        """Test that finished_at is set for terminal states."""
        command = UpdateExecutionCommand(
            exec_id=sample_execution.exec_id,
            rpa_key_id=sample_execution.rpa_key_id,
            status=ExecutionStatus.SUCCESS,
            rpa_response={"notas_fiscais": []},
            error_message=None
        )

        updated = update_execution(
            command=command,
            get_execution=mock_get_execution,
            save_execution=mock_save_execution,
            publish_event=mock_publish_event
        )

        assert updated.finished_at is not None

    def test_update_execution_does_not_set_finished_at_for_running(
        self,
        sample_execution: Execution,
        mock_get_execution,
        mock_save_execution,
        mock_publish_event
    ):
        """Test that finished_at is not set for non-terminal states."""
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

        assert updated.finished_at is None

