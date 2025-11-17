"""Add RobotOperatorSaga event command."""
from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass(frozen=True)
class AddRobotOperatorSagaEventCommand:
    """Command to add an event to RobotOperatorSaga."""
    robot_operator_saga_id: int
    event_type: str
    event_data: Dict[str, Any]
    step_id: Optional[str] = None
    robot_operator_id: Optional[str] = None

