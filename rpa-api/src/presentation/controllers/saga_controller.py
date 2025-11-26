"""Saga controller - Handles saga operations."""
import logging
import os
from datetime import datetime
from typing import Dict, Any, List

from ...application.use_cases.saga_use_cases import create_saga, add_saga_event
from ...application.commands.create_saga_command import CreateSagaCommand
from ...application.commands.add_saga_event_command import AddSagaEventCommand
from ...application.services.saga_structure_builder import build_complete_saga_structure
from ...infrastructure.repositories.saga_repository import save_saga, get_saga as get_saga_repo, get_all_sagas as get_all_sagas_repo
from ...domain.entities.saga import Saga
from ...infrastructure.event_store.event_store import save_event
from ...infrastructure.messaging.event_publisher import publish_task_event
from ..dtos.saga_models import CreateSagaRequest, UpdateSagaEventRequest, SagaResponse, UpdateSagaDataRequest
# from ..dtos.saga_models import RequestRobotExecutionRequest  # TODO: Re-enable after refactoring finishes
# from ...infrastructure.adapters.rabbitmq_service import publish_execution_message  # TODO: Re-enable after refactoring finishes

logger = logging.getLogger(__name__)


def handle_create_saga(payload: CreateSagaRequest) -> Dict[str, Any]:
    """
    Handle Saga creation - pure function.
    
    Creates a Saga with complete structure from DAG configuration if provided,
    or records initial events from Airflow (legacy mode).
    """
    logger.info(f"Creating saga with rpa_key_id={payload.rpa_key_id}")
    
    # Build complete SAGA structure if DAG config is provided
    initial_events = []
    if payload.dag_config:
        # Convert Pydantic model to dict for parser
        dag_config_dict = {
            "dag_id": payload.dag_config.dag_id,
            "tasks": [
                {
                    "task_id": task.task_id,
                    "task_type": task.task_type,
                    "operator_class": task.operator_class,
                    "dependencies": task.dependencies or [],
                    "robot_test_file": task.robot_test_file,
                    "rpa_key_id": task.rpa_key_id or payload.rpa_key_id
                }
                for task in payload.dag_config.tasks
            ]
        }
        
        # Determine robots base path (relative to workspace root)
        robots_base_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "rpa-robots")
        if not os.path.exists(robots_base_path):
            # Try alternative path
            robots_base_path = "rpa-robots"
        
        try:
            initial_events = build_complete_saga_structure(
                dag_config=dag_config_dict,
                rpa_key_id=payload.rpa_key_id,
                robots_base_path=robots_base_path
            )
            logger.info(f"Built complete SAGA structure with {len(initial_events)} events from DAG config")
        except Exception as e:
            logger.error(f"Error building SAGA structure from DAG config: {e}")
            # Fall back to legacy mode
            initial_events = []
    
    # Create saga command
    command = CreateSagaCommand(
        rpa_key_id=payload.rpa_key_id,
        data=payload.data
    )
    
    # Build DAG context from payload
    dag_context = None
    if payload.dag_id or payload.dag_run_id or payload.task_id:
        dag_context = {
            "dag_id": payload.dag_id,
            "dag_run_id": payload.dag_run_id,
            "execution_date": payload.execution_date,
            "task_id": payload.task_id,
            "operator_type": payload.operator_type,
            "operator_id": payload.operator_id,
            "operator_params": payload.operator_params
        }
    
    # Create saga with initial events and DAG context
    saga_id = create_saga(
        command=command,
        save_saga=save_saga,
        save_event=save_event,
        publish_event=publish_task_event,
        initial_events=initial_events if initial_events else None,
        dag_context=dag_context
    )
    
    logger.info(f"Created SAGA {saga_id} with {len(initial_events)} initial events")
    
    # Legacy mode: Record initial events from Airflow if provided and no DAG config
    if not payload.dag_config and payload.initial_events:
        for event_model in payload.initial_events:
            execution_date = None
            if event_model.execution_date:
                if isinstance(event_model.execution_date, str):
                    try:
                        from datetime import datetime
                        execution_date = datetime.fromisoformat(event_model.execution_date.replace('Z', '+00:00'))
                    except (ValueError, AttributeError):
                        try:
                            from dateutil import parser
                            execution_date = parser.parse(event_model.execution_date)
                        except ImportError:
                            logger.warning(f"Could not parse execution_date: {event_model.execution_date}")
                            execution_date = None
                else:
                    execution_date = event_model.execution_date
            
            event_command = AddSagaEventCommand(
                saga_id=saga_id,
                event_type=event_model.event_type,
                event_data=event_model.event_data,
                task_id=event_model.task_id,
                dag_id=event_model.dag_id,
                dag_run_id=event_model.dag_run_id,
                execution_date=execution_date,
                try_number=event_model.try_number,
                operator_type=event_model.operator_type,
                operator_id=event_model.operator_id,
                operator_params=event_model.operator_params
            )
            
            add_saga_event(
                command=event_command,
                get_saga=get_saga_repo,
                save_saga=save_saga,
                save_event=save_event
            )
    
    # Get updated saga with full data
    saga = get_saga_repo(saga_id)
    
    if not saga:
        raise ValueError(f"Saga {saga_id} not found after creation")
    
    # Return full saga object as dictionary (rpa-api creates and returns complete saga)
    return {
        "saga_id": saga.saga_id,
        "rpa_key_id": saga.rpa_key_id,
        "data": saga.data,
        "current_state": saga.current_state.value,
        "events": [e.to_dict() for e in saga.events],
        "events_count": len(saga.events),
        "created_at": saga.created_at.isoformat() if saga.created_at else None,
        "updated_at": saga.updated_at.isoformat() if saga.updated_at else None
    }


def handle_update_saga_event(payload: UpdateSagaEventRequest) -> Dict[str, Any]:
    """
    Handle Saga event update - pure function.
    
    Records a new event in the Saga.
    """
    execution_date = None
    if payload.execution_date:
        if isinstance(payload.execution_date, str):
            try:
                execution_date = datetime.fromisoformat(payload.execution_date.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                try:
                    from dateutil import parser
                    execution_date = parser.parse(payload.execution_date)
                except ImportError:
                    logger.warning(f"Could not parse execution_date: {payload.execution_date}")
                    execution_date = None
        else:
            execution_date = payload.execution_date
    
    command = AddSagaEventCommand(
        saga_id=payload.saga_id,
        event_type=payload.event_type,
        event_data=payload.event_data,
        task_id=payload.task_id,
        dag_id=payload.dag_id,
        dag_run_id=payload.dag_run_id,
        execution_date=execution_date,
        try_number=payload.try_number,
        operator_type=payload.operator_type,
        operator_id=payload.operator_id,
        operator_params=payload.operator_params
    )
    
    updated_saga = add_saga_event(
        command=command,
        get_saga=get_saga_repo,
        save_saga=save_saga,
        save_event=save_event
    )
    
    logger.info(f"Updated SAGA {payload.saga_id} with event {payload.event_type}")
    
    return SagaResponse(
        saga_id=updated_saga.saga_id,
        current_state=updated_saga.current_state.value,
        events_count=len(updated_saga.events),
        message="Saga event recorded successfully"
    ).model_dump()


def handle_list_sagas(limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
    """
    Handle listing all SAGAs - pure function.
    
    Args:
        limit: Maximum number of SAGAs to return
        offset: Number of SAGAs to skip
        
    Returns:
        List of saga dictionaries
    """
    sagas = get_all_sagas_repo(limit=limit, offset=offset)
    
    return [
        {
            "saga_id": saga.saga_id,
            "rpa_key_id": saga.rpa_key_id,
            "data": saga.data,
            "current_state": saga.current_state.value,
            "events": [e.to_dict() for e in saga.events],
            "events_count": len(saga.events),
            "created_at": saga.created_at.isoformat() if saga.created_at else None,
            "updated_at": saga.updated_at.isoformat() if saga.updated_at else None
        }
        for saga in sagas
    ]


def handle_get_saga_by_id(saga_id: int) -> Dict[str, Any]:
    """
    Retrieve a single saga.
    """
    saga = get_saga_repo(saga_id)
    if not saga:
        raise ValueError(f"Saga {saga_id} not found")
    
    return {
        "saga_id": saga.saga_id,
        "rpa_key_id": saga.rpa_key_id,
        "data": saga.data,
        "current_state": saga.current_state.value if saga.current_state else None,
        "events": [e.to_dict() for e in saga.events],
        "events_count": len(saga.events),
        "created_at": saga.created_at.isoformat() if saga.created_at else None,
        "updated_at": saga.updated_at.isoformat() if saga.updated_at else None
    }


def handle_update_saga_data(payload: UpdateSagaDataRequest) -> Dict[str, Any]:
    """
    Update Saga data payload (command side).
    """
    saga = get_saga_repo(payload.saga_id)
    if not saga:
        raise ValueError(f"Saga {payload.saga_id} not found")

    # Create updated Saga with new data, preserving other fields
    updated_saga = Saga(
        saga_id=saga.saga_id,
        rpa_key_id=saga.rpa_key_id,
        data=payload.data,
        current_state=saga.current_state,
        events=saga.events,
        created_at=saga.created_at,
        updated_at=datetime.utcnow(),
    )

    save_saga(updated_saga)

    logger.info(f"Updated data for SAGA {payload.saga_id}")

    return {
        "saga_id": updated_saga.saga_id,
        "rpa_key_id": updated_saga.rpa_key_id,
        "data": updated_saga.data,
        "current_state": updated_saga.current_state.value if updated_saga.current_state else None,
        "events_count": len(updated_saga.events),
        "updated_at": updated_saga.updated_at.isoformat() if updated_saga.updated_at else None,
    }


# TODO: Re-enable after refactoring finishes - Robot execution endpoint needs to be fully implemented
# def handle_request_robot_execution(payload: RequestRobotExecutionRequest) -> Dict[str, Any]:
#     """
#     Handle robot execution request - pure function.
#     
#     Publishes saga to RabbitMQ queue for robot execution.
#     """
#     saga_id = payload.saga_id
#     
#     # Get saga from database
#     saga = get_saga_repo(saga_id)
#     if not saga:
#         raise ValueError(f"Saga {saga_id} not found")
#     
#     # Use provided saga or convert domain saga to dict
#     saga_dict = payload.saga if payload.saga else {
#         "saga_id": saga.saga_id,
#         "rpa_key_id": saga.rpa_key_id,
#         "data": saga.data,
#         "current_state": saga.current_state.value,
#         "events": [e.to_dict() for e in saga.events]
#     }
#     
#     # Build RabbitMQ payload
#     rabbitmq_payload = {
#         "saga_id": saga_id,
#         "rpa_key_id": saga.rpa_key_id,
#         "callback_path": payload.callback_path,
#         "rpa_request": saga.data,  # Use 'data' field
#         "saga": saga_dict
#     }
#     
#     # Publish to RabbitMQ
#     published = publish_execution_message(rabbitmq_payload)
#     
#     if not published:
#         raise ValueError("Failed to publish message to RabbitMQ")
#     
#     logger.info(f"Published robot execution request for saga_id={saga_id}")
#     
#     return {
#         "saga_id": saga_id,
#         "rpa_key_id": saga.rpa_key_id,
#         "status": "ENQUEUED",
#         "message": "Execution request created and published to queue",
#         "published": True,
#         "saga": saga_dict
#     }

