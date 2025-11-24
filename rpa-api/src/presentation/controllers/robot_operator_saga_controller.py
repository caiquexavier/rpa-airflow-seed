"""RobotOperatorSaga controller - Handles robot operator saga operations."""
import logging
from typing import Dict, Any

from ...application.use_cases.robot_operator_saga_use_cases import (
    create_robot_operator_saga,
    add_robot_operator_saga_event
)
from ...application.commands.create_robot_operator_saga_command import CreateRobotOperatorSagaCommand
from ...application.commands.add_robot_operator_saga_event_command import AddRobotOperatorSagaEventCommand
from ...infrastructure.repositories.robot_operator_saga_repository import (
    save_robot_operator_saga,
    get_robot_operator_saga as get_robot_operator_saga_repo
)
from ...infrastructure.event_store.robot_operator_saga_event_store import save_robot_operator_event
from ...infrastructure.messaging.event_publisher import publish_task_event
from ...infrastructure.adapters.rabbitmq_service import publish_execution_message
from ...config.config import get_rabbitmq_config
from ..dtos.robot_operator_saga_models import (
    CreateRobotOperatorSagaRequest,
    UpdateRobotOperatorSagaEventRequest,
    RobotOperatorSagaResponse
)

logger = logging.getLogger(__name__)


def _build_rabbitmq_payload(saga, robot_saga_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build RabbitMQ payload from RobotOperatorSaga - pure function.
    
    Args:
        saga: RobotOperatorSaga domain entity
        robot_saga_dict: RobotOperatorSaga as dictionary
        
    Returns:
        Dictionary ready for RabbitMQ publishing
    """
    # Extract robot test file from robot_operator_id or data
    robot_test_file = saga.data.get("robot_test_file") or f"{saga.robot_operator_id}.robot"
    
    # Build payload for listener
    # Pass data directly (no rpa_request wrapper) - robot expects data object with doc_transportes_list
    payload = {
        "robot_operator_saga_id": saga.robot_operator_saga_id,
        "saga_id": saga.saga_id,
        "robot_operator_id": saga.robot_operator_id,
        "robot_test_file": robot_test_file,
        "callback_path": saga.data.get("callback_path"),
        "data": saga.data,  # Pass data directly for robot to access
        "robot_saga": robot_saga_dict
    }
    
    return payload


def _publish_robot_operator_event(event):
    """Publish robot operator event - adapter to reuse existing publisher."""
    # Convert RobotOperatorStepEvent to TaskEvent-like structure for publishing
    # This is a simple adapter - in production you might want a dedicated publisher
    from ...domain.events.execution_events import TaskEvent
    task_event = TaskEvent(
        saga_id=event.robot_operator_saga_id,
        task_id=event.step_id or "",
        dag_id="",
        event_type=event.event_type,
        event_data=event.event_data,
        occurred_at=event.occurred_at
    )
    publish_task_event(task_event)


def handle_create_robot_operator_saga(payload: CreateRobotOperatorSagaRequest) -> Dict[str, Any]:
    """
    Handle RobotOperatorSaga creation - pure function.
    
    Creates a new RobotOperatorSaga with saga data merged from parent saga.
    """
    logger.info(f"Creating robot operator saga with robot_operator_id={payload.robot_operator_id} for saga_id={payload.saga_id}")
    
    # Merge callback_path into data if provided
    robot_saga_data = payload.data.copy() if payload.data else {}
    if payload.callback_path:
        robot_saga_data["callback_path"] = payload.callback_path
    
    # Create saga command
    command = CreateRobotOperatorSagaCommand(
        saga_id=payload.saga_id,
        robot_operator_id=payload.robot_operator_id,
        data=robot_saga_data
    )
    
    # Create saga
    saga_id = create_robot_operator_saga(
        command=command,
        save_saga=save_robot_operator_saga,
        save_event=save_robot_operator_event,
        publish_event=_publish_robot_operator_event
    )
    
    logger.info(f"Created RobotOperatorSaga {saga_id}")
    
    # Get updated saga with full data
    saga = get_robot_operator_saga_repo(saga_id)
    
    if not saga:
        raise ValueError(f"RobotOperatorSaga {saga_id} not found after creation")
    
    # Publish RobotOperatorSaga to RabbitMQ
    robot_saga_dict = {
        "robot_operator_saga_id": saga.robot_operator_saga_id,
        "saga_id": saga.saga_id,
        "robot_operator_id": saga.robot_operator_id,
        "data": saga.data,
        "current_state": saga.current_state.value,
        "events": [e.to_dict() for e in saga.events],
        "created_at": saga.created_at.isoformat() if saga.created_at else None,
        "updated_at": saga.updated_at.isoformat() if saga.updated_at else None
    }
    
    rabbitmq_payload = _build_rabbitmq_payload(saga, robot_saga_dict)
    published = publish_execution_message(rabbitmq_payload)
    
    # Get queue name from config
    rabbitmq_config = get_rabbitmq_config()
    queue_name = rabbitmq_config["RABBITMQ_ROUTING_KEY"]
    
    # Record publishing to RabbitMQ as a RobotOperatorSaga event
    if published:
        logger.info(f"Published RobotOperatorSaga {saga_id} to {queue_name}")
        
        # Add event for successful queue publishing
        publish_event_command = AddRobotOperatorSagaEventCommand(
            robot_operator_saga_id=saga_id,
            event_type="RobotOperatorSagaPublishedToQueue",
            event_data={
                "queue": queue_name,
                "status": "published",
                "payload_size": len(str(rabbitmq_payload))
            },
            step_id=None,
            robot_operator_id=saga.robot_operator_id
        )
        
        updated_saga = add_robot_operator_saga_event(
            command=publish_event_command,
            get_saga=get_robot_operator_saga_repo,
            save_saga=save_robot_operator_saga,
            save_event=save_robot_operator_event
        )
        
        # Update robot_saga_dict with new event
        robot_saga_dict["events"] = [e.to_dict() for e in updated_saga.events]
        robot_saga_dict["current_state"] = updated_saga.current_state.value
        robot_saga_dict["updated_at"] = updated_saga.updated_at.isoformat() if updated_saga.updated_at else None
        
        logger.info(f"Recorded RobotOperatorSagaPublishedToQueue event for saga {saga_id}")
    else:
        logger.warning(f"Failed to publish RobotOperatorSaga {saga_id} to RabbitMQ")
        
        # Add event for failed queue publishing
        publish_failed_event_command = AddRobotOperatorSagaEventCommand(
            robot_operator_saga_id=saga_id,
            event_type="RobotOperatorSagaPublishFailed",
            event_data={
                "queue": queue_name,
                "status": "failed",
                "error": "Failed to publish to RabbitMQ queue"
            },
            step_id=None,
            robot_operator_id=saga.robot_operator_id
        )
        
        updated_saga = add_robot_operator_saga_event(
            command=publish_failed_event_command,
            get_saga=get_robot_operator_saga_repo,
            save_saga=save_robot_operator_saga,
            save_event=save_robot_operator_event
        )
        
        # Update robot_saga_dict with new event
        robot_saga_dict["events"] = [e.to_dict() for e in updated_saga.events]
        robot_saga_dict["current_state"] = updated_saga.current_state.value
        robot_saga_dict["updated_at"] = updated_saga.updated_at.isoformat() if updated_saga.updated_at else None
        
        logger.warning(f"Recorded RobotOperatorSagaPublishFailed event for saga {saga_id}")
    
    # Return full saga object as dictionary
    return robot_saga_dict


def handle_update_robot_operator_saga_event(payload: UpdateRobotOperatorSagaEventRequest) -> Dict[str, Any]:
    """
    Handle RobotOperatorSaga event update - pure function.
    
    Records a new event in the RobotOperatorSaga.
    """
    command = AddRobotOperatorSagaEventCommand(
        robot_operator_saga_id=payload.robot_operator_saga_id,
        event_type=payload.event_type,
        event_data=payload.event_data,
        step_id=payload.step_id,
        robot_operator_id=payload.robot_operator_id
    )
    
    updated_saga = add_robot_operator_saga_event(
        command=command,
        get_saga=get_robot_operator_saga_repo,
        save_saga=save_robot_operator_saga,
        save_event=save_robot_operator_event
    )
    
    logger.info(f"Updated RobotOperatorSaga {payload.robot_operator_saga_id} with event {payload.event_type}")
    
    return RobotOperatorSagaResponse(
        robot_operator_saga_id=updated_saga.robot_operator_saga_id,
        saga_id=updated_saga.saga_id,
        current_state=updated_saga.current_state.value,
        events_count=len(updated_saga.events),
        message="Robot operator saga event recorded successfully"
    ).model_dump()

