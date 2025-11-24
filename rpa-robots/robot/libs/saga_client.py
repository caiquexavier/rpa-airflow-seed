"""Saga client for Robot Framework - pure functions for saga lifecycle management."""
import json
import os
import logging
import sys
from pathlib import Path
from typing import Optional, Dict, Any
from urllib import request, error

# Import path configuration for centralized path handling
# Use absolute import to work with Robot Framework library loading
try:
    import path_config
except ImportError:
    # If direct import fails, add libs directory to path and try again
    libs_dir = Path(__file__).parent
    if str(libs_dir) not in sys.path:
        sys.path.insert(0, str(libs_dir))
    import path_config

logger = logging.getLogger(__name__)


def _get_api_base_url() -> str:
    """Get RPA API base URL from environment variable."""
    api_url = os.getenv("RPA_API_BASE_URL", "http://localhost:3000")
    if not api_url.endswith('/'):
        api_url = api_url.rstrip('/')
    return api_url


def _build_step_event_url(robot_operator_saga_id: int) -> str:
    """Build URL for step event endpoint."""
    base_url = _get_api_base_url()
    return f"{base_url}/api/v1/robot-operator-saga/{robot_operator_saga_id}/events/step"


def _build_saga_url(saga_id: str) -> str:
    """Build URL for saga retrieval endpoint."""
    base_url = _get_api_base_url()
    return f"{base_url}/api/v1/saga/{saga_id}"


def _make_api_request(url: str, payload: Dict[str, Any], timeout: int = 30) -> bool:
    """Make API request - pure function using urllib to avoid extra deps."""
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            status = resp.getcode()
            if status in (200, 201):
                logger.info("Saga API call succeeded: %s (status_code=%s)", url, status)
                return True
            error_body = resp.read().decode("utf-8", errors="ignore")
            logger.error("API call failed: status=%s, response=%s", status, error_body)
            return False
    except error.HTTPError as http_err:
        body = http_err.read().decode("utf-8", errors="ignore")
        logger.error("API call HTTPError to %s: status=%s, body=%s", url, http_err.code, body)
        return False
    except Exception as exc:
        logger.exception("API call exception to %s: %s: %s", url, type(exc).__name__, exc)
        return False


def saga_api_get_saga(saga_id: str, timeout: int = 30) -> Dict[str, Any]:
    """
    Retrieve saga details from rpa-api.
    
    Args:
        saga_id: Saga identifier
        timeout: HTTP timeout in seconds
        
    Returns:
        Dict with status_code and body (if JSON)
    """
    if not saga_id:
        raise ValueError("saga_id is required to fetch saga data")
    
    url = _build_saga_url(saga_id)
    req = request.Request(url, method="GET")
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            status = resp.getcode()
            body_bytes = resp.read()
            try:
                body = json.loads(body_bytes.decode("utf-8"))
            except ValueError:
                body = {}
            logger.info("Fetched saga %s from %s (status=%s)", saga_id, url, status)
            return {"status_code": status, "body": body}
    except error.HTTPError as http_err:
        body = http_err.read().decode("utf-8", errors="ignore")
        logger.error("Failed to fetch saga %s: HTTP %s %s", saga_id, http_err.code, body)
        return {"status_code": http_err.code, "body": {}, "error": body}
    except Exception as exc:
        logger.error("Failed to fetch saga %s: %s", saga_id, exc, exc_info=True)
        return {"status_code": 0, "body": {}, "error": str(exc)}


def start_step(
    exec_id: Optional[int],
    step_name: str,
    step_id: Optional[str] = None,
    step_data: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Start a saga step.
    
    Args:
        exec_id: Execution ID (robot_operator_saga_id)
        step_name: Name of the step
        step_id: Optional step ID
        step_data: Optional step data
        
    Returns:
        True if successful, False otherwise
    """
    if exec_id is None:
        logger.warning("Cannot start step: exec_id is None")
        return False
    
    url = _build_step_event_url(exec_id)
    payload = {
        "robot_operator_saga_id": exec_id,
        "event_type": "RobotOperatorStepStarted",
        "event_data": {
            "step_name": step_name,
            "step_id": step_id,
            "step_data": step_data or {}
        },
        "step_id": step_id
    }
    
    return _make_api_request(url, payload)


def get_downloads_dir(curdir: Optional[str] = None) -> str:
    """
    Get the shared/downloads directory path using centralized path configuration.
    
    Args:
        curdir: Ignored - kept for backward compatibility.
                Uses path_config to find project root automatically.
        
    Returns:
        Absolute path to the shared/downloads directory.
    """
    return path_config.get_downloads_dir()


def list_pdf_files(download_dir: str) -> set:
    """
    List all PDF files in the download directory.
    
    Args:
        download_dir: Path to the download directory.
        
    Returns:
        Set of PDF filenames.
    """
    normalized_dir = os.path.normpath(download_dir)
    return set([f for f in os.listdir(normalized_dir) if f.endswith('.pdf')])


def get_latest_file(download_dir: str, new_files: list) -> str:
    """
    Get the latest file from a list of new files in the download directory.
    
    Args:
        download_dir: Path to the download directory.
        new_files: List of new filenames.
        
    Returns:
        Path to the latest file.
    """
    normalized_dir = os.path.normpath(download_dir)
    file_paths = [os.path.join(normalized_dir, f) for f in new_files]
    return max(file_paths, key=lambda p: os.path.getmtime(p))


def get_file_size(file_path: str) -> int:
    """
    Get the size of a file.
    
    Args:
        file_path: Path to the file.
        
    Returns:
        File size in bytes.
    """
    normalized_path = os.path.normpath(file_path)
    return os.path.getsize(normalized_path)


def mark_step_success(
    exec_id: Optional[int],
    step_name: str,
    step_id: Optional[str] = None,
    step_data: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Mark a saga step as successful.
    
    Args:
        exec_id: Execution ID (robot_operator_saga_id)
        step_name: Name of the step
        step_id: Optional step ID
        step_data: Optional step data
        
    Returns:
        True if successful, False otherwise
    """
    if exec_id is None:
        logger.warning("Cannot mark step success: exec_id is None")
        return False
    
    url = _build_step_event_url(exec_id)
    payload = {
        "robot_operator_saga_id": exec_id,
        "event_type": "RobotOperatorStepCompleted",
        "event_data": {
            "step_name": step_name,
            "step_id": step_id,
            "status": "SUCCESS",
            "step_data": step_data or {}
        },
        "step_id": step_id
    }
    
    return _make_api_request(url, payload)


def mark_step_fail(
    exec_id: Optional[int],
    step_name: str,
    step_id: Optional[str] = None,
    error_message: str = "",
    step_data: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Mark a saga step as failed.
    
    Args:
        exec_id: Execution ID (robot_operator_saga_id)
        step_name: Name of the step
        step_id: Optional step ID
        error_message: Error message
        step_data: Optional step data
        
    Returns:
        True if successful, False otherwise
    """
    if exec_id is None:
        logger.warning("Cannot mark step fail: exec_id is None")
        return False
    
    url = _build_step_event_url(exec_id)
    payload = {
        "robot_operator_saga_id": exec_id,
        "event_type": "RobotOperatorStepFailed",
        "event_data": {
            "step_name": step_name,
            "step_id": step_id,
            "status": "FAIL",
            "error_message": error_message,
            "step_data": step_data or {}
        },
        "step_id": step_id
    }
    
    return _make_api_request(url, payload)


def finish_execution_success(
    exec_id: Optional[int],
    execution_data: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Finish execution as successful.
    
    Args:
        exec_id: Execution ID (robot_operator_saga_id)
        execution_data: Optional execution data
        
    Returns:
        True if successful, False otherwise
    """
    if exec_id is None:
        logger.warning("Cannot finish execution: exec_id is None")
        return False
    
    url = _build_step_event_url(exec_id)
    payload = {
        "robot_operator_saga_id": exec_id,
        "event_type": "RobotOperatorSagaCompleted",
        "event_data": {
            "status": "SUCCESS",
            "execution_data": execution_data or {}
        }
    }
    
    return _make_api_request(url, payload)


def finish_execution_fail(
    exec_id: Optional[int],
    error_message: str,
    execution_data: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Finish execution as failed.
    
    Args:
        exec_id: Execution ID (robot_operator_saga_id)
        error_message: Error message
        execution_data: Optional execution data
        
    Returns:
        True if successful, False otherwise
    """
    if exec_id is None:
        logger.warning("Cannot finish execution: exec_id is None")
        return False
    
    url = _build_step_event_url(exec_id)
    payload = {
        "robot_operator_saga_id": exec_id,
        "event_type": "RobotOperatorSagaFailed",
        "event_data": {
            "status": "FAIL",
            "error_message": error_message,
            "execution_data": execution_data or {}
        }
    }
    
    return _make_api_request(url, payload)

