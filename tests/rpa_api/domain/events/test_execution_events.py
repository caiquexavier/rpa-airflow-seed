"""Unit tests for execution domain events."""
import pytest
from datetime import datetime

from src.domain.events.execution_events import (
    ExecutionCreated, ExecutionStarted, ExecutionCompleted,
    ExecutionFailed, TaskEvent
)


@pytest.mark.unit
class TestExecutionCreated:
    """Tests for ExecutionCreated event."""

    def test_create_execution_created(self, sample_datetime: datetime, sample_rpa_request: dict):
        """Test creating ExecutionCreated event."""
        event = ExecutionCreated(
            exec_id=1,
            rpa_key_id="test_rpa",
            rpa_request=sample_rpa_request,
            occurred_at=sample_datetime
        )

        assert event.exec_id == 1
        assert event.rpa_key_id == "test_rpa"
        assert event.rpa_request == sample_rpa_request
        assert event.occurred_at == sample_datetime

    def test_execution_created_immutability(self, sample_datetime: datetime, sample_rpa_request: dict):
        """Test that ExecutionCreated is immutable."""
        event = ExecutionCreated(
            exec_id=1,
            rpa_key_id="test_rpa",
            rpa_request=sample_rpa_request,
            occurred_at=sample_datetime
        )

        with pytest.raises(Exception):
            event.exec_id = 999  # type: ignore


@pytest.mark.unit
class TestExecutionStarted:
    """Tests for ExecutionStarted event."""

    def test_create_execution_started(self, sample_datetime: datetime):
        """Test creating ExecutionStarted event."""
        event = ExecutionStarted(
            exec_id=1,
            rpa_key_id="test_rpa",
            occurred_at=sample_datetime
        )

        assert event.exec_id == 1
        assert event.rpa_key_id == "test_rpa"
        assert event.occurred_at == sample_datetime


@pytest.mark.unit
class TestExecutionCompleted:
    """Tests for ExecutionCompleted event."""

    def test_create_execution_completed(self, sample_datetime: datetime):
        """Test creating ExecutionCompleted event."""
        event = ExecutionCompleted(
            exec_id=1,
            rpa_key_id="test_rpa",
            rpa_response={"result": "ok"},
            occurred_at=sample_datetime
        )

        assert event.exec_id == 1
        assert event.rpa_key_id == "test_rpa"
        assert event.rpa_response == {"result": "ok"}
        assert event.occurred_at == sample_datetime


@pytest.mark.unit
class TestExecutionFailed:
    """Tests for ExecutionFailed event."""

    def test_create_execution_failed(self, sample_datetime: datetime):
        """Test creating ExecutionFailed event."""
        event = ExecutionFailed(
            exec_id=1,
            rpa_key_id="test_rpa",
            error_message="Test error",
            rpa_response={"error": "Test error"},
            occurred_at=sample_datetime
        )

        assert event.exec_id == 1
        assert event.rpa_key_id == "test_rpa"
        assert event.error_message == "Test error"
        assert event.rpa_response == {"error": "Test error"}
        assert event.occurred_at == sample_datetime


@pytest.mark.unit
class TestTaskEvent:
    """Tests for TaskEvent."""

    def test_create_task_event(self, sample_datetime: datetime):
        """Test creating TaskEvent."""
        event = TaskEvent(
            exec_id=1,
            saga_id=1,
            task_id="test_task",
            dag_id="test_dag",
            event_type="TaskCompleted",
            event_data={"status": "SUCCESS"},
            occurred_at=sample_datetime
        )

        assert event.exec_id == 1
        assert event.saga_id == 1
        assert event.task_id == "test_task"
        assert event.dag_id == "test_dag"
        assert event.event_type == "TaskCompleted"
        assert event.event_data == {"status": "SUCCESS"}
        assert event.occurred_at == sample_datetime

