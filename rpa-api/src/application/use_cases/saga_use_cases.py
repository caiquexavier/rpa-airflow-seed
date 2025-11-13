"""SAGA use cases - Functional programming style."""
from datetime import datetime
from typing import Optional, Callable

from ...domain.entities.saga import Saga, SagaState, SagaEvent
from ...domain.events.execution_events import TaskEvent
from ..commands.create_saga_command import CreateSagaCommand
from ..commands.add_saga_event_command import AddSagaEventCommand
from ..queries.get_saga_query import GetSagaQuery


def create_saga(
    command: CreateSagaCommand,
    save_saga: Callable[[Saga], int],
    publish_event: Callable[[TaskEvent], None]
) -> int:
    """
    Create SAGA use case - pure function.
    
    Returns:
        saga_id
    """
    now = datetime.utcnow()
    
    saga = Saga(
        saga_id=0,  # Will be set by repository
        exec_id=command.exec_id,
        rpa_key_id=command.rpa_key_id,
        rpa_request_object=command.rpa_request_object,
        current_state=SagaState.PENDING,
        events=[],
        created_at=now,
        updated_at=now
    )
    
    saga_id = save_saga(saga)
    
    # Publish initial event
    event = TaskEvent(
        exec_id=command.exec_id,
        saga_id=saga_id,
        task_id="saga_created",
        dag_id="",
        event_type="SagaCreated",
        event_data={"rpa_request_object": command.rpa_request_object},
        occurred_at=now
    )
    publish_event(event)
    
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
    
    if saga.exec_id != command.exec_id:
        raise ValueError(f"Execution ID mismatch for SAGA {command.saga_id}")
    
    now = datetime.utcnow()
    
    # Create new event
    saga_event = SagaEvent(
        event_type=command.event_type,
        event_data=command.event_data,
        task_id=command.task_id,
        dag_id=command.dag_id,
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
        exec_id=command.exec_id,
        saga_id=command.saga_id,
        task_id=command.task_id or "",
        dag_id=command.dag_id or "",
        event_type=command.event_type,
        event_data=command.event_data,
        occurred_at=now
    )
    save_event(task_event)
    
    return updated_saga


def get_saga(
    query: GetSagaQuery,
    get_saga_by_exec_id: Callable[[int], Optional[Saga]]
) -> Optional[Saga]:
    """
    Get SAGA by execution ID use case - pure function.
    
    Returns:
        Saga or None
    """
    return get_saga_by_exec_id(query.exec_id)


def _determine_saga_state(saga: Saga, event_type: str) -> SagaState:
    """Determine new SAGA state based on event type."""
    if event_type in ("TaskCompleted", "TaskSucceeded"):
        # Check if all expected tasks are completed
        # This is a simplified version - in real scenario, check against DAG definition
        return SagaState.RUNNING
    elif event_type in ("TaskFailed", "TaskError"):
        return SagaState.FAILED
    elif event_type == "SagaCompleted":
        return SagaState.COMPLETED
    elif event_type == "CompensationStarted":
        return SagaState.COMPENSATING
    else:
        return saga.current_state

