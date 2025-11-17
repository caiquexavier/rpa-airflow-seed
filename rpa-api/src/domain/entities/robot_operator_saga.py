"""RobotOperatorSaga entity - Domain model for Robot Operator Saga orchestration."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional
from enum import Enum


class RobotOperatorSagaState(str, Enum):
    """RobotOperatorSaga state enumeration."""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class RobotOperatorSagaEvent:
    """RobotOperatorSaga event - immutable event representation."""
    event_type: str
    event_data: Dict[str, Any]
    step_id: Optional[str] = None
    robot_operator_id: Optional[str] = None
    occurred_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary."""
        return {
            "event_type": self.event_type,
            "event_data": self.event_data,
            "step_id": self.step_id,
            "robot_operator_id": self.robot_operator_id,
            "occurred_at": self.occurred_at.isoformat() if self.occurred_at else datetime.utcnow().isoformat()
        }


@dataclass(frozen=True)
class RobotOperatorSaga:
    """RobotOperatorSaga entity - immutable domain model."""
    robot_operator_saga_id: int
    saga_id: int
    robot_operator_id: str
    data: Dict[str, Any]
    current_state: RobotOperatorSagaState
    events: List[RobotOperatorSagaEvent] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def add_event(self, event: RobotOperatorSagaEvent) -> "RobotOperatorSaga":
        """Create new RobotOperatorSaga instance with added event (immutable)."""
        new_events = list(self.events) + [event]
        return RobotOperatorSaga(
            robot_operator_saga_id=self.robot_operator_saga_id,
            saga_id=self.saga_id,
            robot_operator_id=self.robot_operator_id,
            data=self.data,
            current_state=self.current_state,
            events=new_events,
            created_at=self.created_at,
            updated_at=datetime.utcnow()
        )

    def transition_to(self, new_state: RobotOperatorSagaState) -> "RobotOperatorSaga":
        """Create new RobotOperatorSaga instance with new state (immutable)."""
        return RobotOperatorSaga(
            robot_operator_saga_id=self.robot_operator_saga_id,
            saga_id=self.saga_id,
            robot_operator_id=self.robot_operator_id,
            data=self.data,
            current_state=new_state,
            events=self.events,
            created_at=self.created_at,
            updated_at=datetime.utcnow()
        )

    def get_events_by_step(self, step_id: str) -> List[RobotOperatorSagaEvent]:
        """Get all events for a specific step."""
        return [e for e in self.events if e.step_id == step_id]

