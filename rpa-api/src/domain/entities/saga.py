"""SAGA entity - Domain model for SAGA orchestration."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional
from enum import Enum


class SagaState(str, Enum):
    """SAGA state enumeration."""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    COMPENSATING = "COMPENSATING"
    FAILED = "FAILED"


@dataclass(frozen=True)
class SagaEvent:
    """SAGA event - immutable event representation."""
    event_type: str
    event_data: Dict[str, Any]
    task_id: Optional[str] = None
    dag_id: Optional[str] = None
    occurred_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary."""
        return {
            "event_type": self.event_type,
            "event_data": self.event_data,
            "task_id": self.task_id,
            "dag_id": self.dag_id,
            "occurred_at": self.occurred_at.isoformat() if self.occurred_at else datetime.utcnow().isoformat()
        }


@dataclass(frozen=True)
class Saga:
    """SAGA entity - immutable domain model."""
    saga_id: int
    exec_id: int
    rpa_key_id: str
    rpa_request_object: Dict[str, Any]
    current_state: SagaState
    events: List[SagaEvent] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def add_event(self, event: SagaEvent) -> "Saga":
        """Create new Saga instance with added event (immutable)."""
        new_events = list(self.events) + [event]
        return Saga(
            saga_id=self.saga_id,
            exec_id=self.exec_id,
            rpa_key_id=self.rpa_key_id,
            rpa_request_object=self.rpa_request_object,
            current_state=self.current_state,
            events=new_events,
            created_at=self.created_at,
            updated_at=datetime.utcnow()
        )

    def transition_to(self, new_state: SagaState) -> "Saga":
        """Create new Saga instance with new state (immutable)."""
        return Saga(
            saga_id=self.saga_id,
            exec_id=self.exec_id,
            rpa_key_id=self.rpa_key_id,
            rpa_request_object=self.rpa_request_object,
            current_state=new_state,
            events=self.events,
            created_at=self.created_at,
            updated_at=datetime.utcnow()
        )

    def get_events_by_task(self, task_id: str) -> List[SagaEvent]:
        """Get all events for a specific task."""
        return [e for e in self.events if e.task_id == task_id]

