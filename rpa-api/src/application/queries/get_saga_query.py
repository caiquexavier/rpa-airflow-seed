"""Get SAGA query."""
from dataclasses import dataclass


@dataclass(frozen=True)
class GetSagaQuery:
    """Query to get SAGA by execution ID."""
    exec_id: int

