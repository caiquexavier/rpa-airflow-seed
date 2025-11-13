"""Add SAGA event command."""
from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass(frozen=True)
class AddSagaEventCommand:
    """Command to add an event to SAGA."""
    saga_id: int
    exec_id: int
    event_type: str
    event_data: Dict[str, Any]
    task_id: Optional[str]
    dag_id: Optional[str]

