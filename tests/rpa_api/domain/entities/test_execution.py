"""Unit tests for Execution entity."""
import pytest
from datetime import datetime

from src.domain.entities.execution import Execution, ExecutionStatus


@pytest.mark.unit
class TestExecutionStatus:
    """Tests for ExecutionStatus enum."""

    def test_status_values(self):
        """Test that all expected status values exist."""
        assert ExecutionStatus.PENDING == "PENDING"
        assert ExecutionStatus.RUNNING == "RUNNING"
        assert ExecutionStatus.SUCCESS == "SUCCESS"
        assert ExecutionStatus.FAIL == "FAIL"


@pytest.mark.unit
class TestExecution:
    """Tests for Execution entity."""

    def test_create_execution(self, sample_datetime: datetime):
        """Test creating an execution entity."""
        execution = Execution(
            exec_id=1,
            rpa_key_id="test_rpa",
            exec_status=ExecutionStatus.PENDING,
            rpa_request={"key": "value"},
            rpa_response=None,
            error_message=None,
            callback_url="http://example.com",
            created_at=sample_datetime,
            updated_at=sample_datetime,
            finished_at=None
        )

        assert execution.exec_id == 1
        assert execution.rpa_key_id == "test_rpa"
        assert execution.exec_status == ExecutionStatus.PENDING
        assert execution.rpa_request == {"key": "value"}

    def test_is_terminal_with_success(self, sample_execution: Execution):
        """Test is_terminal returns True for SUCCESS status."""
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

        assert success_execution.is_terminal() is True

    def test_is_terminal_with_fail(self, sample_execution: Execution):
        """Test is_terminal returns True for FAIL status."""
        fail_execution = Execution(
            exec_id=sample_execution.exec_id,
            rpa_key_id=sample_execution.rpa_key_id,
            exec_status=ExecutionStatus.FAIL,
            rpa_request=sample_execution.rpa_request,
            rpa_response=None,
            error_message="Error occurred",
            callback_url=sample_execution.callback_url,
            created_at=sample_execution.created_at,
            updated_at=sample_execution.updated_at,
            finished_at=datetime.utcnow()
        )

        assert fail_execution.is_terminal() is True

    def test_is_terminal_with_pending(self, sample_execution: Execution):
        """Test is_terminal returns False for PENDING status."""
        assert sample_execution.is_terminal() is False

    def test_is_terminal_with_running(self, sample_execution: Execution):
        """Test is_terminal returns False for RUNNING status."""
        running_execution = Execution(
            exec_id=sample_execution.exec_id,
            rpa_key_id=sample_execution.rpa_key_id,
            exec_status=ExecutionStatus.RUNNING,
            rpa_request=sample_execution.rpa_request,
            rpa_response=None,
            error_message=None,
            callback_url=sample_execution.callback_url,
            created_at=sample_execution.created_at,
            updated_at=sample_execution.updated_at,
            finished_at=None
        )

        assert running_execution.is_terminal() is False

    def test_can_transition_from_pending_to_running(self, sample_execution: Execution):
        """Test transition from PENDING to RUNNING is allowed."""
        assert sample_execution.can_transition_to(ExecutionStatus.RUNNING) is True

    def test_can_transition_from_pending_to_success(self, sample_execution: Execution):
        """Test transition from PENDING to SUCCESS is allowed."""
        assert sample_execution.can_transition_to(ExecutionStatus.SUCCESS) is True

    def test_can_transition_from_pending_to_fail(self, sample_execution: Execution):
        """Test transition from PENDING to FAIL is allowed."""
        assert sample_execution.can_transition_to(ExecutionStatus.FAIL) is True

    def test_can_transition_from_terminal_to_same_status(self, sample_execution: Execution):
        """Test idempotent transition from terminal to same status."""
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

        assert success_execution.can_transition_to(ExecutionStatus.SUCCESS) is True

    def test_can_transition_from_terminal_to_different_status(self, sample_execution: Execution):
        """Test transition from terminal to different status is not allowed."""
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

        assert success_execution.can_transition_to(ExecutionStatus.FAIL) is False

    def test_execution_immutability(self, sample_execution: Execution):
        """Test that Execution entity is immutable."""
        with pytest.raises(Exception):
            sample_execution.exec_id = 999  # type: ignore

