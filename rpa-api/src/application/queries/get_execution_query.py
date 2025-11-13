"""Get execution query."""
from dataclasses import dataclass


@dataclass(frozen=True)
class GetExecutionQuery:
    """Query to get execution by ID."""
    exec_id: int

