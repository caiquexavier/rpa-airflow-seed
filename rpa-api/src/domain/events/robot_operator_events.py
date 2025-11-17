"""RobotOperatorSaga domain events."""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any


@dataclass(frozen=True)
class RobotOperatorStepEvent:
    """Event: Robot Operator step event for event store."""
    robot_operator_saga_id: int
    step_id: Optional[str]
    robot_operator_id: str
    event_type: str
    event_data: Dict[str, Any]
    occurred_at: datetime

