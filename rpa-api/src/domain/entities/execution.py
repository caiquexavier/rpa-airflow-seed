"""Execution entity - Domain model for RPA execution."""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum


class ExecutionStatus(str, Enum):
    """Execution status enumeration."""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAIL = "FAIL"


@dataclass(frozen=True)
class Execution:
    """Execution entity - immutable domain model."""
    exec_id: int
    rpa_key_id: str
    exec_status: ExecutionStatus
    rpa_request: Optional[Dict[str, Any]]
    rpa_response: Optional[Dict[str, Any]]
    error_message: Optional[str]
    callback_url: Optional[str]
    created_at: datetime
    updated_at: datetime
    finished_at: Optional[datetime]

    def is_terminal(self) -> bool:
        """Check if execution is in terminal state."""
        return self.exec_status in (ExecutionStatus.SUCCESS, ExecutionStatus.FAIL)

    def can_transition_to(self, new_status: ExecutionStatus) -> bool:
        """Check if status transition is allowed."""
        if self.is_terminal():
            return new_status == self.exec_status  # Allow idempotent updates
        return True

