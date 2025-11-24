"""SAGA repository - Database implementation."""
import json
import logging
from typing import Optional, List
from datetime import datetime

from ...domain.entities.saga import Saga, SagaState, SagaEvent
from ..adapters.postgres import execute_insert, execute_query, execute_update

logger = logging.getLogger(__name__)


def save_saga(saga: Saga) -> int:
    """
    Save SAGA to database (Command side).
    
    Returns:
        saga_id
    """
    if saga.saga_id == 0:
        # Insert new saga
        sql = """
            INSERT INTO saga 
            (rpa_key_id, data, current_state, events, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING saga_id
        """
        events_json = json.dumps([e.to_dict() for e in saga.events])
        params = (
            saga.rpa_key_id,
            json.dumps(saga.data),
            saga.current_state.value,
            events_json,
            saga.created_at,
            saga.updated_at
        )
        saga_id = execute_insert(sql, params)
        return saga_id if saga_id else 0
    else:
        # Update existing saga
        sql = """
            UPDATE saga 
            SET current_state = %s,
                events = %s,
                updated_at = %s
            WHERE saga_id = %s
        """
        events_json = json.dumps([e.to_dict() for e in saga.events])
        params = (
            saga.current_state.value,
            events_json,
            saga.updated_at,
            saga.saga_id
        )
        execute_update(sql, params)
        return saga.saga_id


def get_saga(saga_id: int) -> Optional[Saga]:
    """
    Get SAGA by ID from database (Command side - uses saga table).
    
    Returns:
        Saga or None
    """
    sql = """
        SELECT saga_id, rpa_key_id, data, current_state,
               events, created_at, updated_at
        FROM saga
        WHERE saga_id = %s
    """
    result = execute_query(sql, (saga_id,))
    
    if not result:
        return None
    
    return _row_to_saga(result[0])


def get_all_sagas(limit: Optional[int] = None, offset: Optional[int] = None) -> List[Saga]:
    """
    Get all SAGAs from database.
    
    Args:
        limit: Maximum number of SAGAs to return
        offset: Number of SAGAs to skip
        
    Returns:
        List of Saga entities
    """
    sql = """
        SELECT saga_id, rpa_key_id, data, current_state,
               events, created_at, updated_at
        FROM saga
        ORDER BY created_at DESC
    """
    
    params = []
    if limit is not None:
        sql += " LIMIT %s"
        params.append(limit)
    if offset is not None:
        sql += " OFFSET %s"
        params.append(offset)
    
    result = execute_query(sql, tuple(params) if params else None)
    
    if not result:
        return []
    
    return [_row_to_saga(row) for row in result]


def _row_to_saga(row: dict) -> Saga:
    """Convert database row to Saga entity."""
    # Parse JSON fields
    data = row.get("data")
    if isinstance(data, str):
        data = json.loads(data)
    
    events_data = row.get("events")
    if isinstance(events_data, str):
        events_data = json.loads(events_data)
    elif events_data is None:
        events_data = []
    
    # Convert events list to SagaEvent objects
    events = []
    for event_dict in events_data:
        occurred_at = None
        if event_dict.get("occurred_at"):
            if isinstance(event_dict["occurred_at"], str):
                occurred_at = datetime.fromisoformat(event_dict["occurred_at"].replace('Z', '+00:00'))
            else:
                occurred_at = event_dict["occurred_at"]
        
        execution_date = None
        if event_dict.get("execution_date"):
            if isinstance(event_dict["execution_date"], str):
                execution_date = datetime.fromisoformat(event_dict["execution_date"].replace('Z', '+00:00'))
            else:
                execution_date = event_dict["execution_date"]
        
        events.append(SagaEvent(
            event_type=event_dict["event_type"],
            event_data=event_dict["event_data"],
            task_id=event_dict.get("task_id"),
            dag_id=event_dict.get("dag_id"),
            dag_run_id=event_dict.get("dag_run_id"),
            execution_date=execution_date,
            try_number=event_dict.get("try_number"),
            operator_type=event_dict.get("operator_type"),
            operator_id=event_dict.get("operator_id"),
            operator_params=event_dict.get("operator_params"),
            occurred_at=occurred_at
        ))
    
    return Saga(
        saga_id=row["saga_id"],
        rpa_key_id=row["rpa_key_id"],
        data=data,
        current_state=SagaState(row["current_state"]),
        events=events,
        created_at=row["created_at"],
        updated_at=row["updated_at"]
    )

