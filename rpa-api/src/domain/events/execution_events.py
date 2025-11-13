"""Execution domain events."""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any


@dataclass(frozen=True)
class ExecutionCreated:
    """Event: Execution was created."""
    exec_id: int
    rpa_key_id: str
    rpa_request: Dict[str, Any]
    occurred_at: datetime


@dataclass(frozen=True)
class ExecutionStarted:
    """Event: Execution was started."""
    exec_id: int
    rpa_key_id: str
    occurred_at: datetime


@dataclass(frozen=True)
class ExecutionCompleted:
    """Event: Execution completed successfully."""
    exec_id: int
    rpa_key_id: str
    rpa_response: Dict[str, Any]
    occurred_at: datetime


@dataclass(frozen=True)
class ExecutionFailed:
    """Event: Execution failed."""
    exec_id: int
    rpa_key_id: str
    error_message: str
    rpa_response: Dict[str, Any]
    occurred_at: datetime


@dataclass(frozen=True)
class TaskEvent:
    """Event: Task in DAG completed or failed."""
    exec_id: int
    saga_id: int
    task_id: str
    dag_id: str
    event_type: str
    event_data: Dict[str, Any]
    occurred_at: datetime

