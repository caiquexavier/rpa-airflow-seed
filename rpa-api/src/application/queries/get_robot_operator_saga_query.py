"""Get RobotOperatorSaga query."""
from dataclasses import dataclass


@dataclass(frozen=True)
class GetRobotOperatorSagaQuery:
    """Query to get RobotOperatorSaga by saga ID."""
    robot_operator_saga_id: int

