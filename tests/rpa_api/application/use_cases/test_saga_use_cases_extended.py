"""Extended unit tests for saga use cases - additional scenarios."""
import pytest
from datetime import datetime

from src.domain.entities.saga import Saga, SagaState, SagaEvent
from src.domain.events.execution_events import TaskEvent
from src.application.commands.add_saga_event_command import AddSagaEventCommand
from src.application.use_cases.saga_use_cases import (
    add_saga_event, _determine_saga_state
)


@pytest.mark.unit
class TestAddSagaEventExtended:
    """Extended tests for add_saga_event use case."""

    def test_add_saga_event_with_state_transition(
        self,
        sample_saga: Saga,
        mock_get_saga,
        mock_save_saga,
        mock_save_event
    ):
        """Test adding event that triggers state transition."""
        command = AddSagaEventCommand(
            saga_id=sample_saga.saga_id,
            exec_id=sample_saga.exec_id,
            event_type="TaskCompleted",
            event_data={"status": "SUCCESS"},
            task_id="test_task",
            dag_id="test_dag"
        )

        updated_saga = add_saga_event(
            command=command,
            get_saga=mock_get_saga,
            save_saga=mock_save_saga,
            save_event=mock_save_event
        )

        # State should transition to RUNNING
        assert updated_saga.current_state == SagaState.RUNNING
        assert len(updated_saga.events) == 1
        mock_save_saga.assert_called_once()
        mock_save_event.assert_called_once()

    def test_add_saga_event_without_state_transition(
        self,
        sample_saga: Saga,
        mock_get_saga,
        mock_save_saga,
        mock_save_event
    ):
        """Test adding event that doesn't change state."""
        command = AddSagaEventCommand(
            saga_id=sample_saga.saga_id,
            exec_id=sample_saga.exec_id,
            event_type="UnknownEvent",
            event_data={},
            task_id="test_task",
            dag_id="test_dag"
        )

        updated_saga = add_saga_event(
            command=command,
            get_saga=mock_get_saga,
            save_saga=mock_save_saga,
            save_event=mock_save_event
        )

        # State should remain PENDING
        assert updated_saga.current_state == SagaState.PENDING
        assert len(updated_saga.events) == 1

    def test_add_saga_event_saves_task_event(
        self,
        sample_saga: Saga,
        mock_get_saga,
        mock_save_saga,
        mock_save_event
    ):
        """Test that TaskEvent is saved to event store."""
        command = AddSagaEventCommand(
            saga_id=sample_saga.saga_id,
            exec_id=sample_saga.exec_id,
            event_type="TaskCompleted",
            event_data={"status": "SUCCESS"},
            task_id="test_task",
            dag_id="test_dag"
        )

        add_saga_event(
            command=command,
            get_saga=mock_get_saga,
            save_saga=mock_save_saga,
            save_event=mock_save_event
        )

        # Verify TaskEvent was saved
        mock_save_event.assert_called_once()
        saved_event = mock_save_event.call_args[0][0]
        assert isinstance(saved_event, TaskEvent)
        assert saved_event.exec_id == sample_saga.exec_id
        assert saved_event.saga_id == sample_saga.saga_id
        assert saved_event.task_id == "test_task"

    def test_add_saga_event_with_none_task_id(
        self,
        sample_saga: Saga,
        mock_get_saga,
        mock_save_saga,
        mock_save_event
    ):
        """Test adding event with None task_id."""
        command = AddSagaEventCommand(
            saga_id=sample_saga.saga_id,
            exec_id=sample_saga.exec_id,
            event_type="TaskCompleted",
            event_data={},
            task_id=None,
            dag_id=None
        )

        updated_saga = add_saga_event(
            command=command,
            get_saga=mock_get_saga,
            save_saga=mock_save_saga,
            save_event=mock_save_event
        )

        assert len(updated_saga.events) == 1
        # Verify TaskEvent was saved with empty strings for None values
        saved_event = mock_save_event.call_args[0][0]
        assert saved_event.task_id == ""
        assert saved_event.dag_id == ""


@pytest.mark.unit
class TestDetermineSagaStateExtended:
    """Extended tests for _determine_saga_state function."""

    def test_determine_state_returns_current_when_no_change(self, sample_saga: Saga):
        """Test that state remains unchanged for unknown event types."""
        original_state = sample_saga.current_state
        new_state = _determine_saga_state(sample_saga, "UnknownEventType")
        assert new_state == original_state

    def test_determine_state_running_to_completed(self, sample_saga: Saga):
        """Test state transition from RUNNING to COMPLETED."""
        running_saga = sample_saga.transition_to(SagaState.RUNNING)
        new_state = _determine_saga_state(running_saga, "SagaCompleted")
        assert new_state == SagaState.COMPLETED

    def test_determine_state_pending_to_failed(self, sample_saga: Saga):
        """Test state transition from PENDING to FAILED."""
        new_state = _determine_saga_state(sample_saga, "TaskFailed")
        assert new_state == SagaState.FAILED

    def test_determine_state_running_to_compensating(self, sample_saga: Saga):
        """Test state transition to COMPENSATING."""
        running_saga = sample_saga.transition_to(SagaState.RUNNING)
        new_state = _determine_saga_state(running_saga, "CompensationStarted")
        assert new_state == SagaState.COMPENSATING

