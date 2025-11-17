"""RobotOperatorSaga use cases - Functional programming style."""
import logging
from datetime import datetime
from typing import Optional, Callable

from ...domain.entities.robot_operator_saga import RobotOperatorSaga, RobotOperatorSagaState, RobotOperatorSagaEvent
from ...domain.events.robot_operator_events import RobotOperatorStepEvent
from ..commands.create_robot_operator_saga_command import CreateRobotOperatorSagaCommand
from ..commands.add_robot_operator_saga_event_command import AddRobotOperatorSagaEventCommand
from ..queries.get_robot_operator_saga_query import GetRobotOperatorSagaQuery

logger = logging.getLogger(__name__)


def create_robot_operator_saga(
    command: CreateRobotOperatorSagaCommand,
    save_saga: Callable[[RobotOperatorSaga], int],
    save_event: Callable[[RobotOperatorStepEvent], None],
    publish_event: Callable[[RobotOperatorStepEvent], None]
) -> int:
    """
    Create RobotOperatorSaga use case - pure function.
    
    Args:
        command: CreateRobotOperatorSagaCommand
        save_saga: Function to save saga
        save_event: Function to save event to event store
        publish_event: Function to publish events
        
    Returns:
        robot_operator_saga_id
    """
    now = datetime.utcnow()
    
    # Create RobotOperatorSagaStarted event as the first event
    start_event = RobotOperatorSagaEvent(
        event_type="RobotOperatorSagaStarted",
        event_data={
            "status": "INITIALIZED"
        },
        robot_operator_id=command.robot_operator_id,
        occurred_at=now
    )
    
    saga = RobotOperatorSaga(
        robot_operator_saga_id=0,  # Will be set by repository
        saga_id=command.saga_id,
        robot_operator_id=command.robot_operator_id,
        data=command.data,
        current_state=RobotOperatorSagaState.PENDING,
        events=[start_event],
        created_at=now,
        updated_at=now
    )
    
    saga_id = save_saga(saga)
    
    # Save RobotOperatorSagaStarted event to event store
    step_event = RobotOperatorStepEvent(
        robot_operator_saga_id=saga_id,
        step_id=None,
        robot_operator_id=command.robot_operator_id,
        event_type="RobotOperatorSagaStarted",
        event_data=start_event.event_data,
        occurred_at=now
    )
    save_event(step_event)
    
    # Publish event for external systems
    publish_event(step_event)
    
    return saga_id


def add_robot_operator_saga_event(
    command: AddRobotOperatorSagaEventCommand,
    get_saga: Callable[[int], Optional[RobotOperatorSaga]],
    save_saga: Callable[[RobotOperatorSaga], None],
    save_event: Callable[[RobotOperatorStepEvent], None]
) -> RobotOperatorSaga:
    """
    Add event to RobotOperatorSaga use case - pure function.
    
    Returns:
        Updated saga
    """
    saga = get_saga(command.robot_operator_saga_id)
    
    if not saga:
        raise ValueError(f"RobotOperatorSaga {command.robot_operator_saga_id} not found")
    
    now = datetime.utcnow()
    
    # Create new event
    saga_event = RobotOperatorSagaEvent(
        event_type=command.event_type,
        event_data=command.event_data,
        step_id=command.step_id,
        robot_operator_id=command.robot_operator_id or saga.robot_operator_id,
        occurred_at=now
    )
    
    # Add event to saga (immutable update)
    updated_saga = saga.add_event(saga_event)
    
    # Update state based on event type
    new_state = _determine_robot_operator_saga_state(updated_saga, command.event_type)
    if new_state != updated_saga.current_state:
        updated_saga = updated_saga.transition_to(new_state)
    
    save_saga(updated_saga)
    
    # Save event to event store
    step_event = RobotOperatorStepEvent(
        robot_operator_saga_id=command.robot_operator_saga_id,
        step_id=command.step_id,
        robot_operator_id=command.robot_operator_id or saga.robot_operator_id,
        event_type=command.event_type,
        event_data=command.event_data,
        occurred_at=now
    )
    save_event(step_event)
    
    return updated_saga


def get_robot_operator_saga(
    query: GetRobotOperatorSagaQuery,
    get_saga: Callable[[int], Optional[RobotOperatorSaga]]
) -> Optional[RobotOperatorSaga]:
    """
    Get RobotOperatorSaga by saga ID use case - pure function.
    
    Returns:
        RobotOperatorSaga or None
    """
    return get_saga(query.robot_operator_saga_id)


def _determine_robot_operator_saga_state(saga: RobotOperatorSaga, event_type: str) -> RobotOperatorSagaState:
    """Determine new RobotOperatorSaga state based on event type - pure function."""
    if event_type == "RobotOperatorSagaPublishedToQueue":
        # Saga published to queue, now running
        return RobotOperatorSagaState.RUNNING
    elif event_type in ("RobotOperatorStepCompleted", "RobotOperatorStepSucceeded"):
        return RobotOperatorSagaState.RUNNING
    elif event_type in ("RobotOperatorStepFailed", "RobotOperatorStepError", "RobotOperatorSagaPublishFailed", "RobotOperatorSagaFailed"):
        return RobotOperatorSagaState.FAILED
    elif event_type == "RobotOperatorSagaCompleted":
        return RobotOperatorSagaState.COMPLETED
    else:
        return saga.current_state

