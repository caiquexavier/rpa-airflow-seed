"""SAGA use cases - Functional programming style."""
import logging
from datetime import datetime
from typing import Optional, Callable, List, Dict, Any

from ...domain.entities.saga import Saga, SagaState, SagaEvent
from ...domain.events.execution_events import TaskEvent
from ..commands.create_saga_command import CreateSagaCommand
from ..commands.add_saga_event_command import AddSagaEventCommand
from ..queries.get_saga_query import GetSagaQuery

logger = logging.getLogger(__name__)


def create_saga(
    command: CreateSagaCommand,
    save_saga: Callable[[Saga], int],
    save_event: Callable[[TaskEvent], None],
    publish_event: Callable[[TaskEvent], None],
    initial_events: Optional[List[SagaEvent]] = None,
    dag_context: Optional[Dict[str, Any]] = None
) -> int:
    """
    Create SAGA use case - pure function.
    
    Args:
        command: CreateSagaCommand
        save_saga: Function to save saga
        save_event: Function to save event to event store
        publish_event: Function to publish events
        initial_events: Optional list of initial events to add to saga
        dag_context: Optional DAG context (dag_id, dag_run_id, execution_date, task_id, operator_type, operator_id, operator_params)
        
    Returns:
        saga_id
    """
    now = datetime.utcnow()
    
    # Create StartSaga event as the first event
    dag_id = dag_context.get("dag_id") if dag_context else None
    dag_run_id = dag_context.get("dag_run_id") if dag_context else None
    execution_date_str = dag_context.get("execution_date") if dag_context else None
    execution_date = None
    if execution_date_str:
        if isinstance(execution_date_str, str):
            try:
                execution_date = datetime.fromisoformat(execution_date_str.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                # Fallback: try parsing with dateutil if available
                try:
                    from dateutil import parser
                    execution_date = parser.parse(execution_date_str)
                except ImportError:
                    logger.warning(f"Could not parse execution_date: {execution_date_str}")
                    execution_date = None
        else:
            execution_date = execution_date_str
    
    start_event = SagaEvent(
        event_type="StartSaga",
        event_data={
            "status": "INITIALIZED"
        },
        task_id=dag_context.get("task_id") if dag_context else None,
        dag_id=dag_id,
        dag_run_id=dag_run_id,
        execution_date=execution_date,
        operator_type=dag_context.get("operator_type") if dag_context else None,
        operator_id=dag_context.get("operator_id") if dag_context else None,
        operator_params=dag_context.get("operator_params") if dag_context else None,
        occurred_at=now
    )
    
    # Start with StartSaga event, then add initial events if provided
    events = [start_event]
    if initial_events:
        events.extend(initial_events)
    
    saga = Saga(
        saga_id=0,  # Will be set by repository
        rpa_key_id=command.rpa_key_id,
        data=command.data,
        current_state=SagaState.PENDING,
        events=events,
        created_at=now,
        updated_at=now
    )
    
    saga_id = save_saga(saga)
    
    # Save StartSaga event to event store
    task_event = TaskEvent(
        saga_id=saga_id,
        task_id=start_event.task_id or "",
        dag_id=start_event.dag_id or "",
        event_type="StartSaga",
        event_data=start_event.event_data,
        occurred_at=now,
        dag_run_id=start_event.dag_run_id,
        execution_date=start_event.execution_date,
        operator_type=start_event.operator_type,
        operator_id=start_event.operator_id,
        operator_params=start_event.operator_params
    )
    save_event(task_event)
    
    # Publish event for external systems
    publish_event(task_event)
    
    return saga_id


def add_saga_event(
    command: AddSagaEventCommand,
    get_saga: Callable[[int], Optional[Saga]],
    save_saga: Callable[[Saga], None],
    save_event: Callable[[TaskEvent], None]
) -> Saga:
    """
    Add event to SAGA use case - pure function.
    
    Returns:
        Updated saga
    """
    saga = get_saga(command.saga_id)
    
    if not saga:
        raise ValueError(f"SAGA {command.saga_id} not found")
    
    now = datetime.utcnow()
    
    # Create new event
    saga_event = SagaEvent(
        event_type=command.event_type,
        event_data=command.event_data,
        task_id=command.task_id,
        dag_id=command.dag_id,
        dag_run_id=command.dag_run_id,
        execution_date=command.execution_date,
        try_number=command.try_number,
        operator_type=command.operator_type,
        operator_id=command.operator_id,
        operator_params=command.operator_params,
        occurred_at=now
    )
    
    # Add event to saga (immutable update)
    updated_saga = saga.add_event(saga_event)
    
    # Update state based on event type
    new_state = _determine_saga_state(updated_saga, command.event_type)
    if new_state != updated_saga.current_state:
        updated_saga = updated_saga.transition_to(new_state)
    
    save_saga(updated_saga)
    
    # Save event to event store
    task_event = TaskEvent(
        saga_id=command.saga_id,
        task_id=command.task_id or "",
        dag_id=command.dag_id or "",
        event_type=command.event_type,
        event_data=command.event_data,
        occurred_at=now,
        dag_run_id=command.dag_run_id,
        execution_date=command.execution_date,
        try_number=command.try_number,
        operator_type=command.operator_type,
        operator_id=command.operator_id,
        operator_params=command.operator_params
    )
    save_event(task_event)
    
    return updated_saga


def get_saga(
    query: GetSagaQuery,
    get_saga: Callable[[int], Optional[Saga]]
) -> Optional[Saga]:
    """
    Get SAGA by saga ID use case - pure function.
    
    Returns:
        Saga or None
    """
    return get_saga(query.saga_id)


def _determine_saga_state(saga: Saga, event_type: str) -> SagaState:
    """Determine new SAGA state based on event type."""
    if event_type in ("TaskCompleted", "TaskSucceeded"):
        return SagaState.RUNNING
    elif event_type in ("TaskFailed", "TaskError"):
        return SagaState.FAILED
    elif event_type == "SagaCompleted":
        return SagaState.COMPLETED
    elif event_type == "CompensationStarted":
        return SagaState.COMPENSATING
    else:
        return saga.current_state

