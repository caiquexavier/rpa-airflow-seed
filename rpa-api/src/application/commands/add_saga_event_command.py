"""Add SAGA event command."""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any


@dataclass(frozen=True)
class AddSagaEventCommand:
    """Command to add an event to SAGA."""
    saga_id: int
    event_type: str
    event_data: Dict[str, Any]
    task_id: Optional[str] = None
    dag_id: Optional[str] = None
    dag_run_id: Optional[str] = None
    execution_date: Optional[datetime] = None
    try_number: Optional[int] = None
    operator_type: Optional[str] = None
    operator_id: Optional[str] = None
    operator_params: Optional[Dict[str, Any]] = None

