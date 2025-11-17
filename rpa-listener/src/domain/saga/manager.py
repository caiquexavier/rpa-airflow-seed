"""Saga event management service."""
from datetime import datetime
from typing import Dict, Optional


def create_robot_event(
    robot_operator_id: str,
    success: bool,
    status: str,
    rpa_response: Dict,
    error_message: Optional[str]
) -> Dict:
    """Create robot execution event for saga."""
    event_type = "RobotOperatorSagaCompleted" if success else "RobotOperatorSagaFailed"
    return {
        "event_type": event_type,
        "event_data": {
            "status": status,
            "rpa_response": rpa_response,
            "error_message": error_message
        },
        "step_id": robot_operator_id,
        "robot_operator_id": robot_operator_id,
        "occurred_at": datetime.utcnow().isoformat()
    }


def create_error_event(robot_operator_id: str, error_message: str) -> Dict:
    """Create error event for saga."""
    return {
        "event_type": "RobotOperatorStepError",
        "event_data": {
            "error": error_message
        },
        "step_id": robot_operator_id,
        "robot_operator_id": robot_operator_id,
        "occurred_at": datetime.utcnow().isoformat()
    }


def ensure_saga_structure(saga: Dict) -> Dict:
    """Ensure saga has required structure with events and current_state."""
    if not isinstance(saga, dict):
        saga = {}
    if "events" not in saga:
        saga["events"] = []
    if "current_state" not in saga:
        saga["current_state"] = "PENDING"
    return saga


def add_event_to_saga(saga: Dict, event: Dict, new_state: str) -> Dict:
    """Add event to saga and update state."""
    saga = ensure_saga_structure(saga)
    saga["events"].append(event)
    saga["current_state"] = new_state
    return saga


