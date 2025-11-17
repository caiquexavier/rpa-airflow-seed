"""Create SAGA command."""
from dataclasses import dataclass
from typing import Dict, Any


@dataclass(frozen=True)
class CreateSagaCommand:
    """Command to create a new SAGA."""
    rpa_key_id: str
    data: Dict[str, Any]

