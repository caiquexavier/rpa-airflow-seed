"""Pure functions for RPA robot execution business logic."""
from typing import Any, Dict, Optional

import requests


def validate_saga(saga: Optional[Dict[str, Any]]) -> None:
    """
    Validate that saga exists and has required fields.
    
    Raises:
        ValueError: If saga is missing or missing required fields
    """
    if not saga:
        raise ValueError("SAGA object is required from previous task")
    
    # Validate required fields
    if not isinstance(saga, dict):
        raise ValueError("SAGA must be a dictionary")
    
    if "saga_id" not in saga:
        raise ValueError(
            "SAGA must have saga_id. "
            f"Received saga keys: {list(saga.keys())}"
        )
    
    if not saga.get("saga_id"):
        raise ValueError("SAGA saga_id cannot be empty or zero")


def build_callback_url(api_base_url: str, callback_path: str) -> Optional[str]:
    """Build callback URL from base URL and path."""
    if not api_base_url:
        return None
    api_base_url = api_base_url.rstrip('/')
    return f"{api_base_url}{callback_path}" if api_base_url else None


def build_request_payload(
    saga: Dict[str, Any],
    callback_path: Optional[str],
    robot_operator_id: Optional[str] = None,
    robot_test_file: Optional[str] = None
) -> Dict[str, Any]:
    """
    Build API request payload for RobotOperatorSaga endpoint - pure function.
    
    Args:
        saga: Parent saga dictionary
        callback_path: Optional callback path for webhook
        robot_operator_id: Optional robot operator identifier
        robot_test_file: Optional robot test file name
        
    Returns:
        Payload dictionary for RobotOperatorSaga creation
    """
    # Extract saga_id from saga (required by endpoint)
    saga_id = saga.get("saga_id")
    if not saga_id:
        raise ValueError(
            f"SAGA must have saga_id to build request payload. "
            f"Received saga keys: {list(saga.keys())}"
        )
    
    # Extract saga data (rpa_request_object was replaced by 'data')
    saga_data = saga.get("data") or saga.get("rpa_request") or {}
    
    # Normalize saga_data to dictionary shape for downstream consumers
    if isinstance(saga_data, list):
        saga_data = {"data": saga_data}
    
    if not isinstance(saga_data, dict):
        raise ValueError(
            "SAGA data must be a dict or list convertible to dict. "
            f"Received type: {type(saga_data).__name__}"
        )
    
    # Include robot_test_file in saga data if provided
    if robot_test_file:
        saga_data = saga_data.copy()
        saga_data["robot_test_file"] = robot_test_file
    
    # Build payload for RobotOperatorSaga endpoint
    payload = {
        "saga_id": saga_id,
        "robot_operator_id": robot_operator_id or saga.get("rpa_key_id", "unknown"),
        "data": saga_data,
    }
    
    if callback_path:
        payload["callback_path"] = callback_path
    
    return payload


def build_api_url(schema: Optional[str], host: str, port: Optional[int], endpoint: str) -> str:
    """Build API URL from connection details."""
    schema = schema or 'http'
    port = port or 3000
    return f"{schema}://{host}:{port}{endpoint}"


def call_rpa_api(
    api_url: str,
    payload: Dict[str, Any],
    timeout: int = 30
) -> requests.Response:
    """Make HTTP POST request to RPA API."""
    response = requests.post(
        api_url,
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=timeout
    )
    return response


def validate_rpa_api_response(response: requests.Response) -> None:
    """Validate RPA API response status code."""
    # RobotOperatorSaga endpoint returns 201 (created) instead of 202 (accepted)
    if response.status_code not in [200, 201, 202]:
        raise Exception(f"API request failed with status {response.status_code}: {response.text}")


def parse_rpa_api_response(response: requests.Response) -> Dict[str, Any]:
    """Parse RPA API response JSON."""
    return response.json()


def execute_robot_business_flow(
    saga: Dict[str, Any],
    api_url: str,
    callback_url: Optional[str] = None,  # Deprecated: use callback_path instead
    callback_path: Optional[str] = None,
    robot_operator_id: Optional[str] = None,
    robot_test_file: Optional[str] = None,
    timeout: int = 30
) -> Dict[str, Any]:
    """
    Execute complete robot business flow using pure functions.
    
    Args:
        saga: Saga dictionary
        api_url: API endpoint URL
        callback_url: Deprecated - use callback_path instead
        callback_path: Callback path (e.g., '/trigger/upload_nf_files_to_s3')
        robot_operator_id: Robot operator identifier (e.g., task_id or robot_test_file)
        robot_test_file: Robot test file name (e.g., 'protocolo_devolucao_main.robot')
        timeout: Request timeout
    """
    validate_saga(saga)
    # Use callback_path if provided, otherwise extract from callback_url (backward compatibility)
    if callback_path:
        path = callback_path
    elif callback_url:
        # Extract path from URL for backward compatibility
        from urllib.parse import urlparse
        parsed = urlparse(callback_url)
        path = parsed.path
    else:
        path = None
    
    payload = build_request_payload(saga, path, robot_operator_id, robot_test_file)
    response = call_rpa_api(api_url, payload, timeout)
    validate_rpa_api_response(response)
    return parse_rpa_api_response(response)

