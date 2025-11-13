"""Execution controller - CQRS pattern."""
import logging
from typing import Dict, Any

from ...application.use_cases.execution_use_cases import (
    update_execution, get_execution
)
from ...application.commands.create_execution_command import CreateExecutionCommand
from ...application.commands.update_execution_command import UpdateExecutionCommand
from ...application.queries.get_execution_query import GetExecutionQuery
from ...domain.entities.execution import ExecutionStatus
from ...infrastructure.repositories.execution_repository import (
    save_execution, get_execution as get_execution_repo, set_execution_running
)
from ...infrastructure.messaging.event_publisher import (
    publish_execution_created, publish_execution_started,
    publish_execution_completed, publish_execution_failed
)
from ...infrastructure.messaging.rabbitmq_publisher import publish_message
from ...infrastructure.saga.saga_orchestrator import SagaOrchestrator
from ...infrastructure.repositories.saga_repository import (
    save_saga, get_saga as get_saga_repo
)
from ...infrastructure.event_store.event_store import save_event
from ...infrastructure.messaging.event_publisher import publish_task_event
from ...infrastructure.adapters.callback_service import post_callback

logger = logging.getLogger(__name__)


# Initialize SAGA orchestrator
_saga_orchestrator = SagaOrchestrator(
    save_saga_fn=save_saga,
    get_saga_fn=get_saga_repo,
    save_event_fn=save_event,
    publish_event_fn=publish_task_event
)


def handle_request_rpa_exec(payload: Any) -> Dict[str, Any]:
    """
    Handle RPA execution request - CQRS Command.
    Receives SAGA from Airflow (first DAG step) and creates/updates it.
    
    Returns:
        Response dictionary with updated SAGA
    """
    try:
        # Convert Pydantic model to dict if needed
        if isinstance(payload, dict):
            payload_dict = payload
        elif hasattr(payload, 'model_dump'):
            payload_dict = payload.model_dump()
        elif hasattr(payload, 'dict') and not isinstance(payload, dict):
            payload_dict = payload.dict()
        else:
            payload_dict = payload
        
        # Extract SAGA from payload
        saga_data = payload_dict.get("saga", {})
        if not saga_data:
            raise ValueError("SAGA object is required in request")
        
        rpa_key_id = saga_data.get("rpa_key_id")
        rpa_request_object = saga_data.get("rpa_request_object") or saga_data.get("rpa_request") or {}
        saga_events = saga_data.get("events", [])
        current_state = saga_data.get("current_state", "PENDING")
        
        if not rpa_key_id:
            raise ValueError("rpa_key_id is required in SAGA")
        
        # Create command
        command = CreateExecutionCommand(
            rpa_key_id=rpa_key_id,
            callback_url=str(payload_dict.get("callback_url")) if payload_dict.get("callback_url") else None,
            rpa_request=rpa_request_object
        )
        
        # Create execution first to get exec_id
        from datetime import datetime
        from ...domain.entities.execution import Execution, ExecutionStatus
        
        now = datetime.utcnow()
        execution = Execution(
            exec_id=0,  # Will be set by save
            rpa_key_id=command.rpa_key_id,
            exec_status=ExecutionStatus.PENDING,
            rpa_request=command.rpa_request or {},
            rpa_response=None,
            error_message=None,
            callback_url=command.callback_url,
            created_at=now,
            updated_at=now,
            finished_at=None
        )
        
        exec_id = save_execution(execution)
        
        # Publish domain event
        from ...domain.events.execution_events import ExecutionCreated
        event = ExecutionCreated(
            exec_id=exec_id,
            rpa_key_id=command.rpa_key_id,
            rpa_request=command.rpa_request or {},
            occurred_at=now
        )
        _publish_execution_event(event)
        
        # Create SAGA BEFORE publishing to RabbitMQ (so it's included in message)
        saga_id = _saga_orchestrator.start_saga(
            exec_id=exec_id,
            rpa_key_id=rpa_key_id,
            rpa_request_object=rpa_request_object
        )
        logger.info(f"Created SAGA {saga_id} for execution {exec_id}")
        
        # Record all events from Airflow SAGA (including first step: convert_xls_to_json)
        for event_data in saga_events:
            if isinstance(event_data, dict):
                _saga_orchestrator.record_task_event(
                    saga_id=saga_id,
                    exec_id=exec_id,
                    task_id=event_data.get("task_id"),
                    dag_id=event_data.get("dag_id"),
                    event_type=event_data.get("event_type", "TaskEvent"),
                    event_data=event_data.get("event_data", {})
                )
        
        # Get updated SAGA for RabbitMQ message
        updated_saga = _saga_orchestrator.get_saga_by_exec_id(exec_id)
        saga_for_message = {
            "saga_id": updated_saga.saga_id,
            "rpa_key_id": updated_saga.rpa_key_id,
            "rpa_request_object": updated_saga.rpa_request_object,
            "current_state": updated_saga.current_state.value,
            "events": [e.to_dict() for e in updated_saga.events]
        } if updated_saga else {
            "rpa_key_id": rpa_key_id,
            "rpa_request_object": rpa_request_object,
            "current_state": "PENDING",
            "events": []
        }
        
        # Publish to RabbitMQ with SAGA
        message = {
            "exec_id": exec_id,
            "rpa_key_id": command.rpa_key_id,
            "callback_url": command.callback_url,
            "rpa_request": command.rpa_request,
            "saga": saga_for_message
        }
        published = publish_message(message)
        
        if not published:
            return {
                "exec_id": exec_id,
                "rpa_key_id": command.rpa_key_id,
                "status": "FAILED",
                "message": "Failed to publish to queue",
                "published": False
            }
        
        # Set execution to RUNNING
        set_execution_running(exec_id)
        
        # Use the SAGA we already have for response
        updated_saga_dict = saga_for_message
        
        return {
            "exec_id": exec_id,
            "rpa_key_id": command.rpa_key_id,
            "status": "ENQUEUED",
            "message": "Execution accepted",
            "published": True,
            "saga_id": saga_id,
            "saga": updated_saga_dict
        }
        
    except Exception as e:
        logger.error(f"Error in handle_request_rpa_exec: {e}")
        raise Exception(f"Failed to process execution request: {str(e)}")


def handle_update_rpa_execution(payload: Any) -> Dict[str, Any]:
    """
    Handle RPA execution status update - CQRS Command.
    
    Returns:
        Response dictionary
    """
    try:
        # Convert Pydantic model to dict if needed
        if isinstance(payload, dict):
            payload_dict = payload
        elif hasattr(payload, 'model_dump'):
            payload_dict = payload.model_dump()
        elif hasattr(payload, 'dict') and not isinstance(payload, dict):
            payload_dict = payload.dict()
        else:
            payload_dict = payload
        
        # Get current execution (Query)
        query = GetExecutionQuery(exec_id=payload_dict["exec_id"])
        execution = get_execution(
            query=query,
            get_execution=get_execution_repo
        )
        
        if not execution:
            raise ValueError(f"Execution {payload_dict['exec_id']} not found")
        
        if execution.rpa_key_id != payload_dict["rpa_key_id"]:
            raise ValueError(f"RPA key ID mismatch for execution {payload_dict['exec_id']}")
        
        # Check if already in terminal state
        if execution.is_terminal():
            if execution.exec_status.value == payload_dict["status"]:
                # Idempotent update
                return {
                    "exec_id": execution.exec_id,
                    "rpa_key_id": execution.rpa_key_id,
                    "status": execution.exec_status.value,
                    "rpa_response": payload_dict.get("rpa_response", {}),
                    "error_message": payload_dict.get("error_message"),
                    "updated": True
                }
            else:
                raise ValueError(
                    f"Execution {payload_dict['exec_id']} is already in terminal state: {execution.exec_status.value}"
                )
        
        # Create command
        command = UpdateExecutionCommand(
            exec_id=payload_dict["exec_id"],
            rpa_key_id=payload_dict["rpa_key_id"],
            status=ExecutionStatus(payload_dict["status"]),
            rpa_response=payload_dict.get("rpa_response", {}),
            error_message=payload_dict.get("error_message")
        )
        
        # Execute use case
        updated_execution = update_execution(
            command=command,
            get_execution=get_execution_repo,
            save_execution=save_execution,
            publish_event=_publish_execution_event
        )
        
        # Record SAGA event and update SAGA
        # Check if SAGA is provided in payload (from listener)
        incoming_saga = payload_dict.get("saga")
        saga = _saga_orchestrator.get_saga_by_exec_id(execution.exec_id)
        
        if incoming_saga and isinstance(incoming_saga, dict):
            # SAGA was updated by listener, record events from it
            events = incoming_saga.get("events", [])
            for event in events:
                if isinstance(event, dict):
                    _saga_orchestrator.record_task_event(
                        saga_id=saga.saga_id if saga else 0,
                        exec_id=execution.exec_id,
                        task_id=event.get("task_id", "robot_execution"),
                        dag_id=event.get("dag_id", "rpa_protocolo_devolucao"),
                        event_type=event.get("event_type", "TaskEvent"),
                        event_data=event.get("event_data", {})
                    )
            # Use incoming SAGA as updated SAGA
            updated_saga_dict = incoming_saga
        elif saga:
            # Record new event from command
            event_type = "TaskCompleted" if command.status == ExecutionStatus.SUCCESS else "TaskFailed"
            updated_saga = _saga_orchestrator.record_task_event(
                saga_id=saga.saga_id,
                exec_id=execution.exec_id,
                task_id=payload_dict.get("task_id", "robot_execution"),
                dag_id=payload_dict.get("dag_id", "rpa_protocolo_devolucao"),
                event_type=event_type,
                event_data={
                    "status": command.status.value,
                    "rpa_response": command.rpa_response,
                    "error_message": command.error_message
                }
            )
            
            # Build updated SAGA for callback
            updated_saga_dict = {
                "saga_id": updated_saga.saga_id,
                "rpa_key_id": updated_saga.rpa_key_id,
                "rpa_request_object": updated_saga.rpa_request_object,
                "current_state": updated_saga.current_state.value,
                "events": [e.to_dict() for e in updated_saga.events]
            }
        else:
            updated_saga_dict = None
        
        # Post callback with updated SAGA
        if execution.callback_url:
            try:
                post_callback(
                    callback_url=execution.callback_url,
                    exec_id=updated_execution.exec_id,
                    rpa_key_id=updated_execution.rpa_key_id,
                    status=updated_execution.exec_status.value,
                    rpa_response=updated_execution.rpa_response or {},
                    error_message=updated_execution.error_message,
                    saga=updated_saga_dict
                )
            except Exception as callback_error:
                logger.warning(
                    f"Failed to post callback for exec_id={updated_execution.exec_id}: {callback_error}"
                )
        
        return {
            "exec_id": updated_execution.exec_id,
            "rpa_key_id": updated_execution.rpa_key_id,
            "status": updated_execution.exec_status.value,
            "rpa_response": updated_execution.rpa_response or {},
            "error_message": updated_execution.error_message,
            "updated": True
        }
        
    except ValueError as e:
        logger.warning(f"Validation error in handle_update_rpa_execution: {e}")
        raise
    except Exception as e:
        logger.error(f"Error in handle_update_rpa_execution: {e}")
        raise Exception(f"Failed to update execution: {str(e)}")


def _publish_execution_event(event: Any) -> None:
    """Publish execution event based on type."""
    from ...domain.events.execution_events import (
        ExecutionCreated, ExecutionStarted, ExecutionCompleted, ExecutionFailed
    )
    
    if isinstance(event, ExecutionCreated):
        publish_execution_created(event)
    elif isinstance(event, ExecutionStarted):
        publish_execution_started(event)
    elif isinstance(event, ExecutionCompleted):
        publish_execution_completed(event)
    elif isinstance(event, ExecutionFailed):
        publish_execution_failed(event)

