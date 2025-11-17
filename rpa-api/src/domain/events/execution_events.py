"""Saga domain events."""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any


@dataclass(frozen=True)
class TaskEvent:
    """Event: Task in DAG completed or failed."""
    saga_id: int
    task_id: str
    dag_id: str
    event_type: str
    event_data: Dict[str, Any]
    occurred_at: datetime
    dag_run_id: Optional[str] = None
    execution_date: Optional[datetime] = None
    try_number: Optional[int] = None
    operator_type: Optional[str] = None
    operator_id: Optional[str] = None
    operator_params: Optional[Dict[str, Any]] = None

