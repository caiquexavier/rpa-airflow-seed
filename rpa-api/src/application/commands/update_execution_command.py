"""Update execution command."""
from dataclasses import dataclass
from typing import Optional, Dict, Any

from ...domain.entities.execution import ExecutionStatus


@dataclass(frozen=True)
class UpdateExecutionCommand:
    """Command to update execution status."""
    exec_id: int
    rpa_key_id: str
    status: ExecutionStatus
    rpa_response: Dict[str, Any]
    error_message: Optional[str]

