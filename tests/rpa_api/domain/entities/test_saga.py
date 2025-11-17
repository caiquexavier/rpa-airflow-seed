"""Unit tests for Saga entity."""
import pytest
from datetime import datetime

from src.domain.entities.saga import Saga, SagaState, SagaEvent


@pytest.mark.unit
class TestSagaState:
    """Tests for SagaState enum."""

    def test_state_values(self):
        """Test that all expected state values exist."""
        assert SagaState.PENDING == "PENDING"
        assert SagaState.RUNNING == "RUNNING"
        assert SagaState.COMPLETED == "COMPLETED"
        assert SagaState.COMPENSATING == "COMPENSATING"
        assert SagaState.FAILED == "FAILED"


@pytest.mark.unit
class TestSagaEvent:
    """Tests for SagaEvent entity."""

    def test_create_saga_event(self, sample_datetime: datetime):
        """Test creating a saga event."""
        event = SagaEvent(
            event_type="TaskCompleted",
            event_data={"status": "SUCCESS"},
            task_id="test_task",
            dag_id="test_dag",
            occurred_at=sample_datetime
        )

        assert event.event_type == "TaskCompleted"
        assert event.event_data == {"status": "SUCCESS"}
        assert event.task_id == "test_task"
        assert event.dag_id == "test_dag"
        assert event.occurred_at == sample_datetime

    def test_saga_event_to_dict(self, sample_datetime: datetime):
        """Test converting saga event to dictionary."""
        event = SagaEvent(
            event_type="TaskCompleted",
            event_data={"status": "SUCCESS"},
            task_id="test_task",
            dag_id="test_dag",
            occurred_at=sample_datetime
        )

        result = event.to_dict()

        assert result["event_type"] == "TaskCompleted"
        assert result["event_data"] == {"status": "SUCCESS"}
        assert result["task_id"] == "test_task"
        assert result["dag_id"] == "test_dag"
        assert "occurred_at" in result


@pytest.mark.unit
class TestSaga:
    """Tests for Saga entity."""

    def test_create_saga(self, sample_saga: Saga):
        """Test creating a saga entity."""
        assert sample_saga.saga_id == 1
        assert sample_saga.exec_id == 1
        assert sample_saga.rpa_key_id == "rpa_protocolo_devolucao"
        assert sample_saga.current_state == SagaState.PENDING
        assert len(sample_saga.events) == 0

    def test_add_event_creates_new_instance(self, sample_saga: Saga, sample_saga_event: SagaEvent):
        """Test that add_event creates a new immutable instance."""
        original_events_count = len(sample_saga.events)
        new_saga = sample_saga.add_event(sample_saga_event)

        assert new_saga is not sample_saga
        assert len(sample_saga.events) == original_events_count
        assert len(new_saga.events) == original_events_count + 1
        assert new_saga.events[-1] == sample_saga_event

    def test_add_multiple_events(self, sample_saga: Saga, sample_datetime: datetime):
        """Test adding multiple events to saga."""
        event1 = SagaEvent(
            event_type="TaskStarted",
            event_data={},
            task_id="task1",
            dag_id="dag1",
            occurred_at=sample_datetime
        )
        event2 = SagaEvent(
            event_type="TaskCompleted",
            event_data={},
            task_id="task2",
            dag_id="dag2",
            occurred_at=sample_datetime
        )

        saga_with_one = sample_saga.add_event(event1)
        saga_with_two = saga_with_one.add_event(event2)

        assert len(saga_with_one.events) == 1
        assert len(saga_with_two.events) == 2
        assert saga_with_two.events[0] == event1
        assert saga_with_two.events[1] == event2

    def test_transition_to_creates_new_instance(self, sample_saga: Saga):
        """Test that transition_to creates a new immutable instance."""
        original_state = sample_saga.current_state
        new_saga = sample_saga.transition_to(SagaState.RUNNING)

        assert new_saga is not sample_saga
        assert sample_saga.current_state == original_state
        assert new_saga.current_state == SagaState.RUNNING

    def test_transition_to_preserves_events(self, sample_saga: Saga, sample_saga_event: SagaEvent):
        """Test that transition_to preserves events."""
        saga_with_event = sample_saga.add_event(sample_saga_event)
        new_saga = saga_with_event.transition_to(SagaState.RUNNING)

        assert len(new_saga.events) == len(saga_with_event.events)
        assert new_saga.events == saga_with_event.events

    def test_get_events_by_task(self, sample_saga: Saga, sample_datetime: datetime):
        """Test filtering events by task_id."""
        event1 = SagaEvent(
            event_type="TaskStarted",
            event_data={},
            task_id="task1",
            dag_id="dag1",
            occurred_at=sample_datetime
        )
        event2 = SagaEvent(
            event_type="TaskCompleted",
            event_data={},
            task_id="task1",
            dag_id="dag1",
            occurred_at=sample_datetime
        )
        event3 = SagaEvent(
            event_type="TaskStarted",
            event_data={},
            task_id="task2",
            dag_id="dag2",
            occurred_at=sample_datetime
        )

        saga = sample_saga.add_event(event1).add_event(event2).add_event(event3)
        task1_events = saga.get_events_by_task("task1")

        assert len(task1_events) == 2
        assert all(e.task_id == "task1" for e in task1_events)

    def test_get_events_by_task_empty_result(self, sample_saga: Saga):
        """Test get_events_by_task returns empty list when no matching events."""
        events = sample_saga.get_events_by_task("non_existent_task")
        assert len(events) == 0

    def test_saga_immutability(self, sample_saga: Saga):
        """Test that Saga entity is immutable."""
        with pytest.raises(Exception):
            sample_saga.saga_id = 999  # type: ignore

