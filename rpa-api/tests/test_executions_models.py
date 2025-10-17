"""Unit tests for execution models."""
import pytest
from pydantic import ValidationError

from src.validations.executions_models import (
    RpaExecutionRequestModel, UpdateExecutionRequestModel, 
    ExecutionStatus, RabbitMQMessageModel
)


class TestRpaExecutionRequestModel:
    """Test RpaExecutionRequestModel validation."""
    
    def test_valid_request(self):
        """Test valid request model."""
        request = RpaExecutionRequestModel(
            rpa_key_id="job-001",
            callback_url="http://localhost:3000/callback",
            rpa_request={"nota_fiscal": "12345"}
        )
        assert request.rpa_key_id == "job-001"
        assert str(request.callback_url) == "http://localhost:3000/callback"
        assert request.rpa_request == {"nota_fiscal": "12345"}
    
    def test_minimal_request(self):
        """Test minimal request with only required fields."""
        request = RpaExecutionRequestModel(rpa_key_id="job-001")
        assert request.rpa_key_id == "job-001"
        assert request.callback_url is None
        assert request.rpa_request is None
    
    def test_empty_rpa_key_id_rejected(self):
        """Test that empty rpa_key_id is rejected."""
        with pytest.raises(ValidationError):
            RpaExecutionRequestModel(rpa_key_id="")
    
    def test_whitespace_only_rpa_key_id_rejected(self):
        """Test that whitespace-only rpa_key_id is rejected."""
        with pytest.raises(ValidationError):
            RpaExecutionRequestModel(rpa_key_id="   ")
    
    def test_invalid_callback_url_rejected(self):
        """Test that invalid callback URL is rejected."""
        with pytest.raises(ValidationError):
            RpaExecutionRequestModel(
                rpa_key_id="job-001",
                callback_url="not-a-url"
            )


class TestUpdateExecutionRequestModel:
    """Test UpdateExecutionRequestModel validation."""
    
    def test_valid_success_update(self):
        """Test valid success update."""
        update = UpdateExecutionRequestModel(
            exec_id=123,
            rpa_key_id="job-001",
            rpa_response={"files": ["pod.pdf"]},
            status=ExecutionStatus.SUCCESS
        )
        assert update.exec_id == 123
        assert update.rpa_key_id == "job-001"
        assert update.rpa_response == {"files": ["pod.pdf"]}
        assert update.status == ExecutionStatus.SUCCESS
        assert update.error_message is None
    
    def test_valid_fail_update_with_error(self):
        """Test valid fail update with error message."""
        update = UpdateExecutionRequestModel(
            exec_id=123,
            rpa_key_id="job-001",
            rpa_response={"trace": "..."},
            status=ExecutionStatus.FAIL,
            error_message="Selector not found"
        )
        assert update.status == ExecutionStatus.FAIL
        assert update.error_message == "Selector not found"
    
    def test_fail_without_error_message_rejected(self):
        """Test that FAIL status without error_message is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            UpdateExecutionRequestModel(
                exec_id=123,
                rpa_key_id="job-001",
                rpa_response={},
                status=ExecutionStatus.FAIL
            )
        assert "error_message is required when status is FAIL" in str(exc_info.value)
    
    def test_empty_rpa_response_allowed(self):
        """Test that empty rpa_response is allowed."""
        update = UpdateExecutionRequestModel(
            exec_id=123,
            rpa_key_id="job-001",
            rpa_response={},
            status=ExecutionStatus.SUCCESS
        )
        assert update.rpa_response == {}


class TestRabbitMQMessageModel:
    """Test RabbitMQMessageModel validation."""
    
    def test_valid_message(self):
        """Test valid RabbitMQ message."""
        message = RabbitMQMessageModel(
            exec_id=123,
            rpa_key_id="job-001",
            callback_url="http://localhost:3000/callback",
            rpa_request={"nota_fiscal": "12345"}
        )
        assert message.exec_id == 123
        assert message.rpa_key_id == "job-001"
        assert message.callback_url == "http://localhost:3000/callback"
        assert message.rpa_request == {"nota_fiscal": "12345"}
    
    def test_minimal_message(self):
        """Test minimal message with only required fields."""
        message = RabbitMQMessageModel(
            exec_id=123,
            rpa_key_id="job-001"
        )
        assert message.exec_id == 123
        assert message.rpa_key_id == "job-001"
        assert message.callback_url is None
        assert message.rpa_request is None
