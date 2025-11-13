"""Create SAGA command."""
from dataclasses import dataclass
from typing import Dict, Any


@dataclass(frozen=True)
class CreateSagaCommand:
    """Command to create a new SAGA."""
    exec_id: int
    rpa_key_id: str
    rpa_request_object: Dict[str, Any]

