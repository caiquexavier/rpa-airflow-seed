"""Create execution command."""
from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass(frozen=True)
class CreateExecutionCommand:
    """Command to create a new execution."""
    rpa_key_id: str
    callback_url: Optional[str]
    rpa_request: Optional[Dict[str, Any]]

