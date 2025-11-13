"""Execution use cases - Functional programming style."""
from datetime import datetime
from typing import Optional, Callable, Union

from ...domain.entities.execution import Execution, ExecutionStatus
from ...domain.events.execution_events import (
    ExecutionCreated, ExecutionStarted, ExecutionCompleted, ExecutionFailed
)
from ..commands.create_execution_command import CreateExecutionCommand
from ..commands.update_execution_command import UpdateExecutionCommand
from ..queries.get_execution_query import GetExecutionQuery


def create_execution(
    command: CreateExecutionCommand,
    save_execution: Callable[[Execution], int],
    publish_event: Callable[[ExecutionCreated], None],
    publish_message: Callable[[dict], bool]
) -> tuple[int, bool]:
    """
    Create execution use case - pure function.
    
    Returns:
        Tuple of (exec_id, published)
    """
    now = datetime.utcnow()
    
    execution = Execution(
        exec_id=0,  # Will be set by repository
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
    event = ExecutionCreated(
        exec_id=exec_id,
        rpa_key_id=command.rpa_key_id,
        rpa_request=command.rpa_request or {},
        occurred_at=now
    )
    publish_event(event)
    
    # Publish to RabbitMQ with SAGA
    # Get SAGA from repository to include in message
    from ...infrastructure.repositories.saga_repository import get_saga_by_exec_id
    saga = get_saga_by_exec_id(exec_id)
    
    message = {
        "exec_id": exec_id,
        "rpa_key_id": command.rpa_key_id,
        "callback_url": command.callback_url,
        "rpa_request": command.rpa_request,
        "saga": {
            "saga_id": saga.saga_id if saga else None,
            "rpa_key_id": command.rpa_key_id,
            "rpa_request_object": command.rpa_request or {},
            "current_state": saga.current_state.value if saga else "PENDING",
            "events": [e.to_dict() for e in (saga.events if saga else [])]
        } if saga else {
            "rpa_key_id": command.rpa_key_id,
            "rpa_request_object": command.rpa_request or {},
            "current_state": "PENDING",
            "events": []
        }
    }
    published = publish_message(message)
    
    return exec_id, published


def update_execution(
    command: UpdateExecutionCommand,
    get_execution: Callable[[int], Optional[Execution]],
    save_execution: Callable[[Execution], None],
    publish_event: Callable[[Union[ExecutionCompleted, ExecutionFailed]], None]
) -> Execution:
    """
    Update execution use case - pure function.
    
    Returns:
        Updated execution
    """
    execution = get_execution(command.exec_id)
    
    if not execution:
        raise ValueError(f"Execution {command.exec_id} not found")
    
    if execution.rpa_key_id != command.rpa_key_id:
        raise ValueError(f"RPA key ID mismatch for execution {command.exec_id}")
    
    if not execution.can_transition_to(command.status):
        if execution.is_terminal() and execution.exec_status == command.status:
            # Idempotent update
            return execution
        raise ValueError(
            f"Execution {command.exec_id} is already in terminal state: {execution.exec_status}"
        )
    
    now = datetime.utcnow()
    
    updated_execution = Execution(
        exec_id=execution.exec_id,
        rpa_key_id=execution.rpa_key_id,
        exec_status=command.status,
        rpa_request=execution.rpa_request,
        rpa_response=command.rpa_response,
        error_message=command.error_message,
        callback_url=execution.callback_url,
        created_at=execution.created_at,
        updated_at=now,
        finished_at=now if command.status in (ExecutionStatus.SUCCESS, ExecutionStatus.FAIL) else None
    )
    
    save_execution(updated_execution)
    
    # Publish domain event
    if command.status == ExecutionStatus.SUCCESS:
        event = ExecutionCompleted(
            exec_id=updated_execution.exec_id,
            rpa_key_id=updated_execution.rpa_key_id,
            rpa_response=command.rpa_response,
            occurred_at=now
        )
    else:
        event = ExecutionFailed(
            exec_id=updated_execution.exec_id,
            rpa_key_id=updated_execution.rpa_key_id,
            error_message=command.error_message or "",
            rpa_response=command.rpa_response,
            occurred_at=now
        )
    publish_event(event)
    
    return updated_execution


def get_execution(
    query: GetExecutionQuery,
    get_execution: Callable[[int], Optional[Execution]]
) -> Optional[Execution]:
    """
    Get execution use case - pure function.
    
    Returns:
        Execution or None
    """
    return get_execution(query.exec_id)

