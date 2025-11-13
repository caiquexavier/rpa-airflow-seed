"""Event store - Persist domain events."""
import json
import logging
from datetime import datetime
from typing import Optional

from ...domain.events.execution_events import TaskEvent
from ..adapters.postgres import execute_insert, execute_query

logger = logging.getLogger(__name__)


def save_event(event: TaskEvent) -> int:
    """
    Save event to event store.
    
    Returns:
        event_id
    """
    # Get current version for this saga
    version_sql = """
        SELECT COALESCE(MAX(version), 0) + 1 as next_version
        FROM event_store
        WHERE saga_id = %s
    """
    version_result = execute_query(version_sql, (event.saga_id,))
    next_version = version_result[0]["next_version"] if version_result else 1
    
    sql = """
        INSERT INTO event_store
        (saga_id, exec_id, event_type, event_data, task_id, dag_id, occurred_at, version)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING event_id
    """
    params = (
        event.saga_id,
        event.exec_id,
        event.event_type,
        json.dumps(event.event_data),
        event.task_id,
        event.dag_id,
        event.occurred_at,
        next_version
    )
    event_id = execute_insert(sql, params)
    return event_id if event_id else 0


def get_events_by_saga(saga_id: int) -> list[TaskEvent]:
    """
    Get all events for a saga.
    
    Returns:
        List of TaskEvent
    """
    sql = """
        SELECT event_id, saga_id, exec_id, event_type, event_data, task_id, dag_id, occurred_at, version
        FROM event_store
        WHERE saga_id = %s
        ORDER BY version ASC
    """
    result = execute_query(sql, (saga_id,))
    
    events = []
    for row in result:
        event_data = row.get("event_data")
        if isinstance(event_data, str):
            event_data = json.loads(event_data)
        
        events.append(TaskEvent(
            exec_id=row["exec_id"],
            saga_id=row["saga_id"],
            task_id=row.get("task_id") or "",
            dag_id=row.get("dag_id") or "",
            event_type=row["event_type"],
            event_data=event_data,
            occurred_at=row["occurred_at"]
        ))
    
    return events


def get_events_by_task(saga_id: int, task_id: str) -> list[TaskEvent]:
    """
    Get all events for a specific task in a saga.
    
    Returns:
        List of TaskEvent
    """
    sql = """
        SELECT event_id, saga_id, exec_id, event_type, event_data, task_id, dag_id, occurred_at, version
        FROM event_store
        WHERE saga_id = %s AND task_id = %s
        ORDER BY version ASC
    """
    result = execute_query(sql, (saga_id, task_id))
    
    events = []
    for row in result:
        event_data = row.get("event_data")
        if isinstance(event_data, str):
            event_data = json.loads(event_data)
        
        events.append(TaskEvent(
            exec_id=row["exec_id"],
            saga_id=row["saga_id"],
            task_id=row.get("task_id") or "",
            dag_id=row.get("dag_id") or "",
            event_type=row["event_type"],
            event_data=event_data,
            occurred_at=row["occurred_at"]
        ))
    
    return events

