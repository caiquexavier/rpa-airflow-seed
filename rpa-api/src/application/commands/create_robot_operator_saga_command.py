"""Create RobotOperatorSaga command."""
from dataclasses import dataclass
from typing import Dict, Any


@dataclass(frozen=True)
class CreateRobotOperatorSagaCommand:
    """Command to create a new RobotOperatorSaga."""
    saga_id: int
    robot_operator_id: str
    data: Dict[str, Any]

