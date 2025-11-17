"""Unit tests for execution controller."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from src.domain.entities.execution import Execution, ExecutionStatus
from src.presentation.dtos.executions_models import (
    UpdateExecutionRequestModel
)
from src.presentation.controllers.execution_controller import (
    handle_request_rpa_exec, handle_update_rpa_execution, _payload_to_dict
)


@pytest.mark.unit
class TestHandleRequestRpaExec:
    """Tests for handle_request_rpa_exec function."""

    @patch('src.presentation.controllers.execution_controller.save_execution')
    @patch('src.presentation.controllers.execution_controller.publish_message')
    @patch('src.presentation.controllers.execution_controller._saga_orchestrator')
    @patch('src.presentation.controllers.execution_controller.set_execution_running')
    def test_handle_request_rpa_exec_success(
        self,
        mock_set_running,
        mock_saga_orchestrator,
        mock_publish_message,
        mock_save_execution,
        sample_rpa_request: dict
    ):
        """Test successful RPA execution request."""
        mock_save_execution.return_value = 1
        mock_publish_message.return_value = True
        mock_set_running.return_value = True
        
        mock_saga = Mock()
        mock_saga.saga_id = 1
        mock_saga.rpa_key_id = "test_rpa"
        mock_saga.rpa_request_object = sample_rpa_request
        mock_saga.current_state.value = "PENDING"
        mock_saga.events = []
        
        mock_saga_orchestrator.start_saga.return_value = 1
        mock_saga_orchestrator.get_saga_by_exec_id.return_value = mock_saga
        mock_saga_orchestrator.record_task_event.return_value = None

        # Use dict payload as controller normalizes it
        payload = {
            "rpa_key_id": "test_rpa",
            "callback_url": "http://example.com/callback",
            "rpa_request": sample_rpa_request,
            "saga": {
                "rpa_key_id": "test_rpa",
                "rpa_request_object": sample_rpa_request,
                "events": [],
                "current_state": "PENDING"
            }
        }

        result = handle_request_rpa_exec(payload)

        assert result["exec_id"] == 1
        assert result["rpa_key_id"] == "test_rpa"
        assert result["status"] == "ENQUEUED"
        assert result["published"] is True
        assert "saga" in result

    @patch('src.presentation.controllers.execution_controller.save_execution')
    @patch('src.presentation.controllers.execution_controller.publish_message')
    @patch('src.presentation.controllers.execution_controller._saga_orchestrator')
    def test_handle_request_rpa_exec_missing_saga(
        self,
        mock_saga_orchestrator,
        mock_publish_message,
        mock_save_execution,
        sample_rpa_request: dict
    ):
        """Test request without saga raises error."""
        payload = {
            "rpa_key_id": "test_rpa",
            "callback_url": None,
            "rpa_request": sample_rpa_request,
            "saga": None
        }

        with pytest.raises(ValueError, match="SAGA object is required"):
            handle_request_rpa_exec(payload)

    @patch('src.presentation.controllers.execution_controller.save_execution')
    @patch('src.presentation.controllers.execution_controller.publish_message')
    @patch('src.presentation.controllers.execution_controller._saga_orchestrator')
    def test_handle_request_rpa_exec_publish_failure(
        self,
        mock_saga_orchestrator,
        mock_publish_message,
        mock_save_execution,
        sample_rpa_request: dict
    ):
        """Test request when message publishing fails."""
        mock_save_execution.return_value = 1
        mock_publish_message.return_value = False
        
        mock_saga = Mock()
        mock_saga.saga_id = 1
        mock_saga.rpa_key_id = "test_rpa"
        mock_saga.rpa_request_object = sample_rpa_request
        mock_saga.current_state.value = "PENDING"
        mock_saga.events = []
        
        mock_saga_orchestrator.start_saga.return_value = 1
        mock_saga_orchestrator.get_saga_by_exec_id.return_value = mock_saga

        payload = {
            "rpa_key_id": "test_rpa",
            "callback_url": None,
            "rpa_request": sample_rpa_request,
            "saga": {
                "rpa_key_id": "test_rpa",
                "rpa_request_object": sample_rpa_request,
                "events": [],
                "current_state": "PENDING"
            }
        }

        result = handle_request_rpa_exec(payload)

        assert result["status"] == "FAILED"
        assert result["published"] is False


@pytest.mark.unit
class TestHandleUpdateRpaExecution:
    """Tests for handle_update_rpa_execution function."""

    @patch('src.presentation.controllers.execution_controller.get_execution')
    @patch('src.presentation.controllers.execution_controller.update_execution')
    @patch('src.presentation.controllers.execution_controller.post_callback')
    @patch('src.presentation.controllers.execution_controller._saga_orchestrator')
    def test_handle_update_rpa_execution_success(
        self,
        mock_saga_orchestrator,
        mock_post_callback,
        mock_update_execution,
        mock_get_execution,
        sample_execution: Execution
    ):
        """Test successful execution update."""
        updated_execution = Execution(
            exec_id=sample_execution.exec_id,
            rpa_key_id=sample_execution.rpa_key_id,
            exec_status=ExecutionStatus.SUCCESS,
            rpa_request=sample_execution.rpa_request,
            rpa_response={"result": "ok"},
            error_message=None,
            callback_url=sample_execution.callback_url,
            created_at=sample_execution.created_at,
            updated_at=datetime.utcnow(),
            finished_at=datetime.utcnow()
        )

        mock_get_execution.return_value = sample_execution
        mock_update_execution.return_value = updated_execution
        mock_saga_orchestrator.get_saga_by_exec_id.return_value = None

        payload = UpdateExecutionRequestModel(
            exec_id=sample_execution.exec_id,
            rpa_key_id=sample_execution.rpa_key_id,
            status="SUCCESS",
            rpa_response={"result": "ok"},
            error_message=None
        )

        result = handle_update_rpa_execution(payload)

        assert result["exec_id"] == sample_execution.exec_id
        assert result["status"] == "SUCCESS"
        assert result["updated"] is True

    @patch('src.presentation.controllers.execution_controller.get_execution')
    def test_handle_update_rpa_execution_not_found(
        self,
        mock_get_execution
    ):
        """Test update when execution not found."""
        mock_get_execution.return_value = None

        payload = UpdateExecutionRequestModel(
            exec_id=999,
            rpa_key_id="test_rpa",
            status="SUCCESS",
            rpa_response={},
            error_message=None
        )

        with pytest.raises(ValueError, match="Execution 999 not found"):
            handle_update_rpa_execution(payload)

    @patch('src.presentation.controllers.execution_controller.get_execution')
    def test_handle_update_rpa_execution_idempotent(
        self,
        mock_get_execution,
        sample_execution: Execution
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

        mock_get_execution.return_value = success_execution

        payload = UpdateExecutionRequestModel(
            exec_id=success_execution.exec_id,
            rpa_key_id=success_execution.rpa_key_id,
            status="SUCCESS",
            rpa_response={"result": "ok"},
            error_message=None
        )

        result = handle_update_rpa_execution(payload)

        assert result["status"] == "SUCCESS"
        assert result["updated"] is True

