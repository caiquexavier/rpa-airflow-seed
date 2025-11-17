"""Unit tests for execution DTOs."""
import pytest
from pydantic import ValidationError

from src.domain.entities.execution import ExecutionStatus
from src.presentation.dtos.executions_models import (
    SagaEventModel, SagaModel, RpaExecutionRequestModel,
    UpdateExecutionRequestModel, UpdateExecutionResponseModel
)


@pytest.mark.unit
class TestSagaEventModel:
    """Tests for SagaEventModel."""

    def test_create_saga_event_model(self):
        """Test creating valid SagaEventModel."""
        model = SagaEventModel(
            event_type="TaskCompleted",
            event_data={"status": "SUCCESS"},
            task_id="test_task",
            dag_id="test_dag"
        )

        assert model.event_type == "TaskCompleted"
        assert model.event_data == {"status": "SUCCESS"}
        assert model.task_id == "test_task"
        assert model.dag_id == "test_dag"


@pytest.mark.unit
class TestSagaModel:
    """Tests for SagaModel."""

    def test_create_saga_model(self, sample_rpa_request: dict):
        """Test creating valid SagaModel."""
        model = SagaModel(
            rpa_key_id="test_rpa",
            rpa_request_object=sample_rpa_request,
            events=[],
            current_state="PENDING"
        )

        assert model.rpa_key_id == "test_rpa"
        assert model.rpa_request_object == sample_rpa_request
        assert model.current_state == "PENDING"

    def test_saga_model_strips_whitespace(self, sample_rpa_request: dict):
        """Test that rpa_key_id is stripped."""
        model = SagaModel(
            rpa_key_id="  test_rpa  ",
            rpa_request_object=sample_rpa_request
        )

        assert model.rpa_key_id == "test_rpa"

    def test_saga_model_min_length_validation(self, sample_rpa_request: dict):
        """Test that empty rpa_key_id is rejected."""
        with pytest.raises(ValidationError):
            SagaModel(
                rpa_key_id="",
                rpa_request_object=sample_rpa_request
            )


@pytest.mark.unit
class TestRpaExecutionRequestModel:
    """Tests for RpaExecutionRequestModel."""

    def test_create_rpa_execution_request_model(self, sample_rpa_request: dict):
        """Test creating valid RpaExecutionRequestModel."""
        saga = SagaModel(
            rpa_key_id="test_rpa",
            rpa_request_object=sample_rpa_request
        )
        model = RpaExecutionRequestModel(
            saga=saga,
            callback_url="http://example.com/callback"
        )

        assert model.saga.rpa_key_id == "test_rpa"
        assert str(model.callback_url) == "http://example.com/callback"


@pytest.mark.unit
class TestUpdateExecutionRequestModel:
    """Tests for UpdateExecutionRequestModel."""

    def test_create_update_execution_request_success(self):
        """Test creating valid UpdateExecutionRequestModel for SUCCESS."""
        model = UpdateExecutionRequestModel(
            exec_id=1,
            rpa_key_id="test_rpa",
            status=ExecutionStatus.SUCCESS,
            rpa_response={"notas_fiscais": [{"nota_fiscal": "NF001", "status": "success"}]},
            error_message=None
        )

        assert model.exec_id == 1
        assert model.status == ExecutionStatus.SUCCESS
        assert "notas_fiscais" in model.rpa_response

    def test_create_update_execution_request_fail(self):
        """Test creating valid UpdateExecutionRequestModel for FAIL."""
        model = UpdateExecutionRequestModel(
            exec_id=1,
            rpa_key_id="test_rpa",
            status=ExecutionStatus.FAIL,
            rpa_response={"error": "Test error"},
            error_message="Test error"
        )

        assert model.status == ExecutionStatus.FAIL
        assert model.error_message == "Test error"
        assert model.rpa_response["error"] == "Test error"

    def test_update_execution_request_requires_error_message_for_fail(self):
        """Test that error_message is required for FAIL status."""
        with pytest.raises(ValidationError, match="error_message is required"):
            UpdateExecutionRequestModel(
                exec_id=1,
                rpa_key_id="test_rpa",
                status=ExecutionStatus.FAIL,
                rpa_response={"error": "Test error"},
                error_message=None
            )

    def test_update_execution_request_rejects_error_message_for_success(self):
        """Test that error_message must be null for SUCCESS."""
        with pytest.raises(ValidationError, match="error_message must be null"):
            UpdateExecutionRequestModel(
                exec_id=1,
                rpa_key_id="test_rpa",
                status=ExecutionStatus.SUCCESS,
                rpa_response={"notas_fiscais": []},
                error_message="Should not be here"
            )

    def test_update_execution_request_requires_notas_fiscais_for_success(self):
        """Test that rpa_response must have notas_fiscais for SUCCESS."""
        with pytest.raises(ValidationError, match="notas_fiscais"):
            UpdateExecutionRequestModel(
                exec_id=1,
                rpa_key_id="test_rpa",
                status=ExecutionStatus.SUCCESS,
                rpa_response={},
                error_message=None
            )

    def test_update_execution_request_requires_error_format_for_fail(self):
        """Test that rpa_response must be {"error": "..."} for FAIL."""
        with pytest.raises(ValidationError, match=r'rpa_response must be \{"error"'):
            UpdateExecutionRequestModel(
                exec_id=1,
                rpa_key_id="test_rpa",
                status=ExecutionStatus.FAIL,
                rpa_response={"wrong": "format"},
                error_message="Test error"
            )

    def test_update_execution_request_error_message_must_match(self):
        """Test that error_message must equal rpa_response.error."""
        with pytest.raises(ValidationError, match="error_message must equal"):
            UpdateExecutionRequestModel(
                exec_id=1,
                rpa_key_id="test_rpa",
                status=ExecutionStatus.FAIL,
                rpa_response={"error": "Error in response"},
                error_message="Different error message"
            )

    def test_update_execution_request_forbids_extra_fields(self):
        """Test that extra fields are forbidden."""
        with pytest.raises(ValidationError):
            UpdateExecutionRequestModel(
                exec_id=1,
                rpa_key_id="test_rpa",
                status=ExecutionStatus.SUCCESS,
                rpa_response={"notas_fiscais": []},
                error_message=None,
                extra_field="not allowed"  # type: ignore
            )


@pytest.mark.unit
class TestUpdateExecutionResponseModel:
    """Tests for UpdateExecutionResponseModel."""

    def test_create_update_execution_response_model(self):
        """Test creating UpdateExecutionResponseModel."""
        model = UpdateExecutionResponseModel(
            exec_id=1,
            rpa_key_id="test_rpa",
            status="SUCCESS",
            rpa_response={"notas_fiscais": []},
            error_message=None,
            updated=True
        )

        assert model.exec_id == 1
        assert model.status == "SUCCESS"
        assert model.updated is True

