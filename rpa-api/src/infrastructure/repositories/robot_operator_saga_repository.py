"""RobotOperatorSaga repository - Database implementation."""
import json
import logging
from typing import Optional, List
from datetime import datetime

from ...domain.entities.robot_operator_saga import RobotOperatorSaga, RobotOperatorSagaState, RobotOperatorSagaEvent
from ..adapters.postgres import execute_insert, execute_query, execute_update

logger = logging.getLogger(__name__)


def save_robot_operator_saga(saga: RobotOperatorSaga) -> int:
    """
    Save RobotOperatorSaga to database (Command side).
    
    Returns:
        robot_operator_saga_id
    """
    if saga.robot_operator_saga_id == 0:
        # Insert new saga
        sql = """
            INSERT INTO robot_operator_saga 
            (saga_id, robot_operator_id, data, current_state, events, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING robot_operator_saga_id
        """
        events_json = json.dumps([e.to_dict() for e in saga.events])
        params = (
            saga.saga_id,
            saga.robot_operator_id,
            json.dumps(saga.data),
            saga.current_state.value,
            events_json,
            saga.created_at,
            saga.updated_at
        )
        result = execute_insert(sql, params)
        # execute_insert returns the first value from RETURNING clause
        if result:
            if isinstance(result, dict):
                return result.get("robot_operator_saga_id") or next(iter(result.values()))
            return result
        return 0
    else:
        # Update existing saga
        sql = """
            UPDATE robot_operator_saga 
            SET current_state = %s,
                events = %s,
                updated_at = %s
            WHERE robot_operator_saga_id = %s
        """
        events_json = json.dumps([e.to_dict() for e in saga.events])
        params = (
            saga.current_state.value,
            events_json,
            saga.updated_at,
            saga.robot_operator_saga_id
        )
        execute_update(sql, params)
        return saga.robot_operator_saga_id


def get_robot_operator_saga(robot_operator_saga_id: int) -> Optional[RobotOperatorSaga]:
    """
    Get RobotOperatorSaga by ID from database (Command side).
    
    Returns:
        RobotOperatorSaga or None
    """
    sql = """
        SELECT robot_operator_saga_id, saga_id, robot_operator_id, data, current_state,
               events, created_at, updated_at
        FROM robot_operator_saga
        WHERE robot_operator_saga_id = %s
    """
    result = execute_query(sql, (robot_operator_saga_id,))
    
    if not result:
        return None
    
    return _row_to_robot_operator_saga(result[0])


def get_robot_operator_sagas_by_saga_id(saga_id: int) -> List[RobotOperatorSaga]:
    """
    Get all RobotOperatorSaga instances by parent saga_id.
    
    Returns:
        List of RobotOperatorSaga
    """
    sql = """
        SELECT robot_operator_saga_id, saga_id, robot_operator_id, data, current_state,
               events, created_at, updated_at
        FROM robot_operator_saga
        WHERE saga_id = %s
        ORDER BY created_at ASC
    """
    result = execute_query(sql, (saga_id,))
    
    return [_row_to_robot_operator_saga(row) for row in result]


def _row_to_robot_operator_saga(row: dict) -> RobotOperatorSaga:
    """Convert database row to RobotOperatorSaga entity."""
    # Parse JSON fields
    data = row.get("data")
    if isinstance(data, str):
        data = json.loads(data)
    
    events_data = row.get("events")
    if isinstance(events_data, str):
        events_data = json.loads(events_data)
    elif events_data is None:
        events_data = []
    
    # Convert events list to RobotOperatorSagaEvent objects
    events = []
    for event_dict in events_data:
        occurred_at = None
        if event_dict.get("occurred_at"):
            if isinstance(event_dict["occurred_at"], str):
                occurred_at = datetime.fromisoformat(event_dict["occurred_at"].replace('Z', '+00:00'))
            else:
                occurred_at = event_dict["occurred_at"]
        
        events.append(RobotOperatorSagaEvent(
            event_type=event_dict["event_type"],
            event_data=event_dict["event_data"],
            step_id=event_dict.get("step_id"),
            robot_operator_id=event_dict.get("robot_operator_id"),
            occurred_at=occurred_at
        ))
    
    return RobotOperatorSaga(
        robot_operator_saga_id=row["robot_operator_saga_id"],
        saga_id=row["saga_id"],
        robot_operator_id=row["robot_operator_id"],
        data=data,
        current_state=RobotOperatorSagaState(row["current_state"]),
        events=events,
        created_at=row["created_at"],
        updated_at=row["updated_at"]
    )

