"""Extended unit tests for execution controller - additional scenarios."""
import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from src.domain.entities.execution import Execution, ExecutionStatus
from src.presentation.controllers.execution_controller import (
    handle_request_rpa_exec, handle_update_rpa_execution, _publish_execution_event
)
from src.domain.events.execution_events import (
    ExecutionCreated, ExecutionStarted, ExecutionCompleted, ExecutionFailed
)


@pytest.mark.unit
class TestHandleRequestRpaExecExtended:
    """Extended tests for handle_request_rpa_exec function."""

    @patch('src.presentation.controllers.execution_controller.save_execution')
    @patch('src.presentation.controllers.execution_controller.publish_message')
    @patch('src.presentation.controllers.execution_controller._saga_orchestrator')
    @patch('src.presentation.controllers.execution_controller.set_execution_running')
    def test_handle_request_rpa_exec_with_saga_events(
        self,
        mock_set_running,
        mock_saga_orchestrator,
        mock_publish_message,
        mock_save_execution,
        sample_rpa_request: dict
    ):
        """Test request with saga events from Airflow."""
        mock_save_execution.return_value = 1
        mock_publish_message.return_value = True
        mock_set_running.return_value = True
        
        mock_saga = Mock()
        mock_saga.saga_id = 1
        mock_saga.rpa_key_id = "test_rpa"
        mock_saga.rpa_request_object = sample_rpa_request
        mock_saga.current_state.value = "RUNNING"
        mock_saga.events = []
        
        mock_saga_orchestrator.start_saga.return_value = 1
        mock_saga_orchestrator.get_saga_by_exec_id.return_value = mock_saga
        mock_saga_orchestrator.record_task_event.return_value = None

        payload = {
            "rpa_key_id": "test_rpa",
            "callback_url": "http://example.com/callback",
            "rpa_request": sample_rpa_request,
            "saga": {
                "rpa_key_id": "test_rpa",
                "rpa_request_object": sample_rpa_request,
                "events": [
                    {
                        "task_id": "task1",
                        "dag_id": "dag1",
                        "event_type": "TaskCompleted",
                        "event_data": {"status": "SUCCESS"}
                    }
                ],
                "current_state": "RUNNING"
            }
        }

        result = handle_request_rpa_exec(payload)

        assert result["exec_id"] == 1
        assert result["status"] == "ENQUEUED"
        # Verify saga events were recorded
        assert mock_saga_orchestrator.record_task_event.called

    @patch('src.presentation.controllers.execution_controller.save_execution')
    @patch('src.presentation.controllers.execution_controller.publish_message')
    @patch('src.presentation.controllers.execution_controller._saga_orchestrator')
    def test_handle_request_rpa_exec_missing_rpa_key_id(
        self,
        mock_saga_orchestrator,
        mock_publish_message,
        mock_save_execution,
        sample_rpa_request: dict
    ):
        """Test request with missing rpa_key_id in saga."""
        payload = {
            "rpa_key_id": "test_rpa",
            "saga": {
                "rpa_request_object": sample_rpa_request,
                "events": []
            }
        }

        with pytest.raises(ValueError, match="rpa_key_id is required"):
            handle_request_rpa_exec(payload)

    @patch('src.presentation.controllers.execution_controller.save_execution')
    @patch('src.presentation.controllers.execution_controller.publish_message')
    @patch('src.presentation.controllers.execution_controller._saga_orchestrator')
    def test_handle_request_rpa_exec_with_rpa_request_fallback(
        self,
        mock_saga_orchestrator,
        mock_publish_message,
        mock_save_execution,
        sample_rpa_request: dict
    ):
        """Test request using rpa_request as fallback for rpa_request_object."""
        mock_save_execution.return_value = 1
        mock_publish_message.return_value = True
        
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
            "saga": {
                "rpa_key_id": "test_rpa",
                "rpa_request": sample_rpa_request,  # Using rpa_request instead of rpa_request_object
                "events": []
            }
        }

        result = handle_request_rpa_exec(payload)

        assert result["exec_id"] == 1


@pytest.mark.unit
class TestHandleUpdateRpaExecutionExtended:
    """Extended tests for handle_update_rpa_execution function."""

    @patch('src.presentation.controllers.execution_controller.get_execution')
    @patch('src.presentation.controllers.execution_controller.update_execution')
    @patch('src.presentation.controllers.execution_controller.post_callback')
    @patch('src.presentation.controllers.execution_controller._saga_orchestrator')
    def test_handle_update_with_incoming_saga(
        self,
        mock_saga_orchestrator,
        mock_post_callback,
        mock_update_execution,
        mock_get_execution,
        sample_execution: Execution
    ):
        """Test update with incoming saga from listener."""
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
        
        mock_saga = Mock()
        mock_saga.saga_id = 1
        mock_saga_orchestrator.get_saga_by_exec_id.return_value = mock_saga

        payload = {
            "exec_id": sample_execution.exec_id,
            "rpa_key_id": sample_execution.rpa_key_id,
            "status": "SUCCESS",
            "rpa_response": {"notas_fiscais": []},
            "error_message": None,
            "saga": {
                "saga_id": 1,
                "events": [
                    {
                        "task_id": "robot_execution",
                        "dag_id": "rpa_protocolo_devolucao",
                        "event_type": "RobotCompleted",
                        "event_data": {}
                    }
                ]
            }
        }

        result = handle_update_rpa_execution(payload)

        assert result["exec_id"] == sample_execution.exec_id
        assert result["status"] == "SUCCESS"
        # Verify saga events were recorded
        assert mock_saga_orchestrator.record_task_event.called

    @patch('src.presentation.controllers.execution_controller.get_execution')
    @patch('src.presentation.controllers.execution_controller.update_execution')
    @patch('src.presentation.controllers.execution_controller.post_callback')
    @patch('src.presentation.controllers.execution_controller._saga_orchestrator')
    def test_handle_update_with_saga_record_event(
        self,
        mock_saga_orchestrator,
        mock_post_callback,
        mock_update_execution,
        mock_get_execution,
        sample_execution: Execution
    ):
        """Test update with saga recording new event."""
        updated_execution = Execution(
            exec_id=sample_execution.exec_id,
            rpa_key_id=sample_execution.rpa_key_id,
            exec_status=ExecutionStatus.SUCCESS,
            rpa_request=sample_execution.rpa_request,
            rpa_response={"notas_fiscais": []},
            error_message=None,
            callback_url=sample_execution.callback_url,
            created_at=sample_execution.created_at,
            updated_at=datetime.utcnow(),
            finished_at=datetime.utcnow()
        )

        mock_get_execution.return_value = sample_execution
        mock_update_execution.return_value = updated_execution
        
        mock_saga = Mock()
        mock_saga.saga_id = 1
        mock_updated_saga = Mock()
        mock_updated_saga.saga_id = 1
        mock_updated_saga.rpa_key_id = "test_rpa"
        mock_updated_saga.rpa_request_object = {}
        mock_updated_saga.current_state.value = "COMPLETED"
        mock_updated_saga.events = []
        
        mock_saga_orchestrator.get_saga_by_exec_id.return_value = mock_saga
        mock_saga_orchestrator.record_task_event.return_value = mock_updated_saga

        payload = {
            "exec_id": sample_execution.exec_id,
            "rpa_key_id": sample_execution.rpa_key_id,
            "status": "SUCCESS",
            "rpa_response": {"notas_fiscais": []},
            "error_message": None
        }

        result = handle_update_rpa_execution(payload)

        assert result["exec_id"] == sample_execution.exec_id
        assert result["status"] == "SUCCESS"
        # Verify saga event was recorded
        mock_saga_orchestrator.record_task_event.assert_called_once()

    @patch('src.presentation.controllers.execution_controller.get_execution')
    @patch('src.presentation.controllers.execution_controller.update_execution')
    @patch('src.presentation.controllers.execution_controller.post_callback')
    @patch('src.presentation.controllers.execution_controller._saga_orchestrator')
    def test_handle_update_with_callback_error(
        self,
        mock_saga_orchestrator,
        mock_post_callback,
        mock_update_execution,
        mock_get_execution,
        sample_execution: Execution
    ):
        """Test update when callback fails (should not fail the update)."""
        updated_execution = Execution(
            exec_id=sample_execution.exec_id,
            rpa_key_id=sample_execution.rpa_key_id,
            exec_status=ExecutionStatus.SUCCESS,
            rpa_request=sample_execution.rpa_request,
            rpa_response={"notas_fiscais": []},
            error_message=None,
            callback_url="http://example.com/callback",
            created_at=sample_execution.created_at,
            updated_at=datetime.utcnow(),
            finished_at=datetime.utcnow()
        )

        mock_get_execution.return_value = sample_execution
        mock_update_execution.return_value = updated_execution
        mock_post_callback.side_effect = Exception("Callback failed")
        mock_saga_orchestrator.get_saga_by_exec_id.return_value = None

        payload = {
            "exec_id": sample_execution.exec_id,
            "rpa_key_id": sample_execution.rpa_key_id,
            "status": "SUCCESS",
            "rpa_response": {"notas_fiscais": []},
            "error_message": None
        }

        # Should not raise exception even if callback fails
        result = handle_update_rpa_execution(payload)

        assert result["exec_id"] == sample_execution.exec_id
        assert result["status"] == "SUCCESS"


@pytest.mark.unit
class TestPublishExecutionEvent:
    """Tests for _publish_execution_event helper function."""

    @patch('src.presentation.controllers.execution_controller.publish_execution_created')
    def test_publish_execution_created(self, mock_publish):
        """Test publishing ExecutionCreated event."""
        event = ExecutionCreated(
            exec_id=1,
            rpa_key_id="test_rpa",
            rpa_request={},
            occurred_at=datetime.utcnow()
        )

        _publish_execution_event(event)

        mock_publish.assert_called_once_with(event)

    @patch('src.presentation.controllers.execution_controller.publish_execution_started')
    def test_publish_execution_started(self, mock_publish):
        """Test publishing ExecutionStarted event."""
        from src.domain.events.execution_events import ExecutionStarted
        event = ExecutionStarted(
            exec_id=1,
            rpa_key_id="test_rpa",
            occurred_at=datetime.utcnow()
        )

        _publish_execution_event(event)

        mock_publish.assert_called_once_with(event)

    @patch('src.presentation.controllers.execution_controller.publish_execution_completed')
    def test_publish_execution_completed(self, mock_publish):
        """Test publishing ExecutionCompleted event."""
        event = ExecutionCompleted(
            exec_id=1,
            rpa_key_id="test_rpa",
            rpa_response={"result": "ok"},
            occurred_at=datetime.utcnow()
        )

        _publish_execution_event(event)

        mock_publish.assert_called_once_with(event)

    @patch('src.presentation.controllers.execution_controller.publish_execution_failed')
    def test_publish_execution_failed(self, mock_publish):
        """Test publishing ExecutionFailed event."""
        event = ExecutionFailed(
            exec_id=1,
            rpa_key_id="test_rpa",
            error_message="Test error",
            rpa_response={"error": "Test error"},
            occurred_at=datetime.utcnow()
        )

        _publish_execution_event(event)

        mock_publish.assert_called_once_with(event)

