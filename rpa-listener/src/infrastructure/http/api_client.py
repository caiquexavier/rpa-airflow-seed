"""RPA API client for RobotOperatorSaga updates."""
import logging
from typing import Dict, Optional

import requests

from ...core.config.env import get_required_env

logger = logging.getLogger(__name__)


def update_robot_operator_saga(
    robot_operator_saga_id: int,
    status: str,
    rpa_response: Dict,
    error_message: Optional[str],
    robot_saga: Dict,
    *,
    event_type_override: Optional[str] = None,
    event_data_override: Optional[Dict] = None,
    step_id_override: Optional[str] = None,
) -> bool:
    """Update RobotOperatorSaga via API."""
    api_url = _build_api_url(robot_operator_saga_id)
    payload = _build_saga_payload(
        robot_operator_saga_id,
        status,
        rpa_response,
        error_message,
        robot_saga,
        event_type_override=event_type_override,
        event_data_override=event_data_override,
        step_id_override=step_id_override,
    )
    logger.info(
        "Updating RobotOperatorSaga via API",
        extra={
            "robot_operator_saga_id": robot_operator_saga_id,
            "status": status,
            "api_url": api_url,
        },
    )
    return _make_api_request(api_url, payload)


def _build_api_url(robot_operator_saga_id: int) -> str:
    """Build API URL for RobotOperatorSaga event update."""
    api_base_url = get_required_env("RPA_API_BASE_URL")
    if not api_base_url.endswith('/'):
        api_base_url = api_base_url.rstrip('/')
    return f"{api_base_url}/api/v1/robot-operator-saga/{robot_operator_saga_id}/events/step"


def _build_saga_payload(
    robot_operator_saga_id: int,
    status: str,
    rpa_response: Dict,
    error_message: Optional[str],
    robot_saga: Dict,
    *,
    event_type_override: Optional[str] = None,
    event_data_override: Optional[Dict] = None,
    step_id_override: Optional[str] = None,
) -> Dict:
    """Build payload for RobotOperatorSaga event update."""
    normalized_status = (status or "UNKNOWN").upper()
    event_type = event_type_override or (
        "RobotOperatorSagaCompleted" if normalized_status == "SUCCESS" else "RobotOperatorSagaFailed"
    )
    event_data = event_data_override or {
        "status": normalized_status,
        "rpa_response": rpa_response,
        "error_message": error_message
    }
    return {
        "robot_operator_saga_id": robot_operator_saga_id,
        "event_type": event_type,
        "event_data": event_data,
        "step_id": step_id_override or robot_saga.get("robot_operator_id"),
        "robot_operator_id": robot_saga.get("robot_operator_id")
    }


def _make_api_request(api_url: str, payload: Dict) -> bool:
    """Make API request to update RobotOperatorSaga."""
    try:
        response = requests.post(
            api_url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        if response.status_code in [200, 201]:
            logger.info("RobotOperatorSaga API call succeeded", extra={"api_url": api_url, "status_code": response.status_code})
            return True
        else:
            error_msg = f"API call failed: status_code={response.status_code}, response={response.text}"
            logger.error(error_msg, extra={"api_url": api_url, "status_code": response.status_code})
            return False
    except requests.exceptions.ConnectionError as e:
        error_msg = f"API connection error to {api_url}: {e}"
        logger.error(error_msg)
        return False
    except Exception as e:
        error_msg = f"API call exception to {api_url}: {type(e).__name__}: {e}"
        logger.exception(error_msg)
        return False

