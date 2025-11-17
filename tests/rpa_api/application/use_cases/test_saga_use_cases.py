"""Unit tests for saga use cases."""
import pytest
from datetime import datetime

from src.domain.entities.saga import Saga, SagaState, SagaEvent
from src.application.commands.create_saga_command import CreateSagaCommand
from src.application.commands.add_saga_event_command import AddSagaEventCommand
from src.application.queries.get_saga_query import GetSagaQuery
from src.application.use_cases.saga_use_cases import (
    create_saga, add_saga_event, get_saga, _determine_saga_state
)


@pytest.mark.unit
class TestCreateSaga:
    """Tests for create_saga use case."""

    def test_create_saga_success(
        self,
        sample_rpa_request: dict,
        mock_save_saga,
        mock_publish_event
    ):
        """Test successful saga creation."""
        command = CreateSagaCommand(
            exec_id=1,
            rpa_key_id="test_rpa",
            rpa_request_object=sample_rpa_request
        )

        saga_id = create_saga(
            command=command,
            save_saga=mock_save_saga,
            publish_event=mock_publish_event
        )

        assert saga_id > 0
        mock_save_saga.assert_called_once()
        mock_publish_event.assert_called_once()

        # Verify the saga that was saved
        saved_saga = mock_save_saga.call_args[0][0]
        assert saved_saga.exec_id == command.exec_id
        assert saved_saga.rpa_key_id == command.rpa_key_id
        assert saved_saga.rpa_request_object == command.rpa_request_object
        assert saved_saga.current_state == SagaState.PENDING
        assert len(saved_saga.events) == 0

    def test_create_saga_publishes_event(
        self,
        sample_rpa_request: dict,
        mock_save_saga,
        mock_publish_event
    ):
        """Test that saga creation publishes TaskEvent."""
        command = CreateSagaCommand(
            exec_id=1,
            rpa_key_id="test_rpa",
            rpa_request_object=sample_rpa_request
        )

        create_saga(
            command=command,
            save_saga=mock_save_saga,
            publish_event=mock_publish_event
        )

        # Verify event was published
        mock_publish_event.assert_called_once()
        published_event = mock_publish_event.call_args[0][0]
        assert published_event.exec_id == command.exec_id
        assert published_event.event_type == "SagaCreated"


@pytest.mark.unit
class TestAddSagaEvent:
    """Tests for add_saga_event use case."""

    def test_add_saga_event_success(
        self,
        sample_saga: Saga,
        mock_get_saga,
        mock_save_saga,
        mock_save_event
    ):
        """Test successfully adding event to saga."""
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

        assert len(updated_saga.events) == 1
        assert updated_saga.events[0].event_type == "TaskCompleted"
        mock_save_saga.assert_called_once()
        mock_save_event.assert_called_once()

    def test_add_saga_event_not_found(
        self,
        mock_save_saga,
        mock_save_event
    ):
        """Test adding event to non-existent saga raises error."""
        def mock_get_none(saga_id: int):
            return None

        command = AddSagaEventCommand(
            saga_id=999,
            exec_id=1,
            event_type="TaskCompleted",
            event_data={},
            task_id="test_task",
            dag_id="test_dag"
        )

        with pytest.raises(ValueError, match="SAGA 999 not found"):
            add_saga_event(
                command=command,
                get_saga=mock_get_none,
                save_saga=mock_save_saga,
                save_event=mock_save_event
            )

    def test_add_saga_event_exec_id_mismatch(
        self,
        sample_saga: Saga,
        mock_get_saga,
        mock_save_saga,
        mock_save_event
    ):
        """Test adding event with wrong exec_id raises error."""
        command = AddSagaEventCommand(
            saga_id=sample_saga.saga_id,
            exec_id=999,  # Wrong exec_id
            event_type="TaskCompleted",
            event_data={},
            task_id="test_task",
            dag_id="test_dag"
        )

        with pytest.raises(ValueError, match="Execution ID mismatch"):
            add_saga_event(
                command=command,
                get_saga=mock_get_saga,
                save_saga=mock_save_saga,
                save_event=mock_save_event
            )

    def test_add_saga_event_updates_state(
        self,
        sample_saga: Saga,
        mock_get_saga,
        mock_save_saga,
        mock_save_event
    ):
        """Test that adding event updates saga state."""
        command = AddSagaEventCommand(
            saga_id=sample_saga.saga_id,
            exec_id=sample_saga.exec_id,
            event_type="TaskCompleted",
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

        # State should transition to RUNNING for TaskCompleted
        assert updated_saga.current_state == SagaState.RUNNING

    def test_add_saga_event_failed_state(
        self,
        sample_saga: Saga,
        mock_get_saga,
        mock_save_saga,
        mock_save_event
    ):
        """Test that failed event updates state to FAILED."""
        command = AddSagaEventCommand(
            saga_id=sample_saga.saga_id,
            exec_id=sample_saga.exec_id,
            event_type="TaskFailed",
            event_data={"error": "Test error"},
            task_id="test_task",
            dag_id="test_dag"
        )

        updated_saga = add_saga_event(
            command=command,
            get_saga=mock_get_saga,
            save_saga=mock_save_saga,
            save_event=mock_save_event
        )

        assert updated_saga.current_state == SagaState.FAILED

    def test_add_saga_event_completed_state(
        self,
        sample_saga: Saga,
        mock_get_saga,
        mock_save_saga,
        mock_save_event
    ):
        """Test that SagaCompleted event updates state to COMPLETED."""
        command = AddSagaEventCommand(
            saga_id=sample_saga.saga_id,
            exec_id=sample_saga.exec_id,
            event_type="SagaCompleted",
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

        assert updated_saga.current_state == SagaState.COMPLETED


@pytest.mark.unit
class TestGetSaga:
    """Tests for get_saga use case."""

    def test_get_saga_success(
        self,
        sample_saga: Saga,
        mock_get_saga
    ):
        """Test getting existing saga."""
        def get_saga_by_exec_id(exec_id: int):
            if exec_id == sample_saga.exec_id:
                return sample_saga
            return None

        query = GetSagaQuery(exec_id=sample_saga.exec_id)

        result = get_saga(
            query=query,
            get_saga_by_exec_id=get_saga_by_exec_id
        )

        assert result == sample_saga
        assert result.saga_id == sample_saga.saga_id

    def test_get_saga_not_found(self):
        """Test getting non-existent saga returns None."""
        def get_saga_by_exec_id(exec_id: int):
            return None

        query = GetSagaQuery(exec_id=999)

        result = get_saga(
            query=query,
            get_saga_by_exec_id=get_saga_by_exec_id
        )

        assert result is None


@pytest.mark.unit
class TestDetermineSagaState:
    """Tests for _determine_saga_state function."""

    def test_determine_state_task_completed(self, sample_saga: Saga):
        """Test state determination for TaskCompleted."""
        state = _determine_saga_state(sample_saga, "TaskCompleted")
        assert state == SagaState.RUNNING

    def test_determine_state_task_succeeded(self, sample_saga: Saga):
        """Test state determination for TaskSucceeded."""
        state = _determine_saga_state(sample_saga, "TaskSucceeded")
        assert state == SagaState.RUNNING

    def test_determine_state_task_failed(self, sample_saga: Saga):
        """Test state determination for TaskFailed."""
        state = _determine_saga_state(sample_saga, "TaskFailed")
        assert state == SagaState.FAILED

    def test_determine_state_task_error(self, sample_saga: Saga):
        """Test state determination for TaskError."""
        state = _determine_saga_state(sample_saga, "TaskError")
        assert state == SagaState.FAILED

    def test_determine_state_saga_completed(self, sample_saga: Saga):
        """Test state determination for SagaCompleted."""
        state = _determine_saga_state(sample_saga, "SagaCompleted")
        assert state == SagaState.COMPLETED

    def test_determine_state_compensation_started(self, sample_saga: Saga):
        """Test state determination for CompensationStarted."""
        state = _determine_saga_state(sample_saga, "CompensationStarted")
        assert state == SagaState.COMPENSATING

    def test_determine_state_unknown_event(self, sample_saga: Saga):
        """Test state determination for unknown event type."""
        original_state = sample_saga.current_state
        state = _determine_saga_state(sample_saga, "UnknownEvent")
        assert state == original_state

