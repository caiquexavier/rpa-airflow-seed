"""Get SAGA query."""
from dataclasses import dataclass


@dataclass(frozen=True)
class GetSagaQuery:
    """Query to get SAGA by saga ID."""
    saga_id: int

