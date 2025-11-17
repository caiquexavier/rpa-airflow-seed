"""RobotOperatorSaga event store - Persist domain events."""
import json
import logging
from datetime import datetime
from typing import Optional, List

from ...domain.events.robot_operator_events import RobotOperatorStepEvent
from ..adapters.postgres import execute_insert, execute_query

logger = logging.getLogger(__name__)


def save_robot_operator_event(event: RobotOperatorStepEvent) -> int:
    """
    Save event to robot operator saga event store.
    
    Returns:
        event_id
    """
    # Get current version for this saga
    version_sql = """
        SELECT COALESCE(MAX(version), 0) + 1 as next_version
        FROM robot_operator_saga_event_store
        WHERE robot_operator_saga_id = %s
    """
    version_result = execute_query(version_sql, (event.robot_operator_saga_id,))
    next_version = version_result[0]["next_version"] if version_result else 1
    
    sql = """
        INSERT INTO robot_operator_saga_event_store
        (robot_operator_saga_id, event_type, event_data, step_id, robot_operator_id, occurred_at, version)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING event_id
    """
    params = (
        event.robot_operator_saga_id,
        event.event_type,
        json.dumps(event.event_data),
        event.step_id,
        event.robot_operator_id,
        event.occurred_at,
        next_version
    )
    result = execute_insert(sql, params)
    # execute_insert returns the first value from RETURNING clause
    if result:
        if isinstance(result, dict):
            return result.get("event_id") or next(iter(result.values()))
        return result
    return 0


def get_events_by_robot_operator_saga(robot_operator_saga_id: int) -> List[RobotOperatorStepEvent]:
    """
    Get all events for a robot operator saga.
    
    Returns:
        List of RobotOperatorStepEvent
    """
    sql = """
        SELECT event_id, robot_operator_saga_id, event_type, event_data, step_id,
               robot_operator_id, occurred_at, version
        FROM robot_operator_saga_event_store
        WHERE robot_operator_saga_id = %s
        ORDER BY version ASC
    """
    result = execute_query(sql, (robot_operator_saga_id,))
    
    events = []
    for row in result:
        event_data = row.get("event_data")
        if isinstance(event_data, str):
            event_data = json.loads(event_data)
        
        events.append(RobotOperatorStepEvent(
            robot_operator_saga_id=row["robot_operator_saga_id"],
            step_id=row.get("step_id"),
            robot_operator_id=row.get("robot_operator_id") or "",
            event_type=row["event_type"],
            event_data=event_data,
            occurred_at=row["occurred_at"]
        ))
    
    return events


def get_events_by_step(robot_operator_saga_id: int, step_id: str) -> List[RobotOperatorStepEvent]:
    """
    Get all events for a specific step in a robot operator saga.
    
    Returns:
        List of RobotOperatorStepEvent
    """
    sql = """
        SELECT event_id, robot_operator_saga_id, event_type, event_data, step_id,
               robot_operator_id, occurred_at, version
        FROM robot_operator_saga_event_store
        WHERE robot_operator_saga_id = %s AND step_id = %s
        ORDER BY version ASC
    """
    result = execute_query(sql, (robot_operator_saga_id, step_id))
    
    events = []
    for row in result:
        event_data = row.get("event_data")
        if isinstance(event_data, str):
            event_data = json.loads(event_data)
        
        events.append(RobotOperatorStepEvent(
            robot_operator_saga_id=row["robot_operator_saga_id"],
            step_id=row.get("step_id"),
            robot_operator_id=row.get("robot_operator_id") or "",
            event_type=row["event_type"],
            event_data=event_data,
            occurred_at=row["occurred_at"]
        ))
    
    return events

