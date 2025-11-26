"""SAGA service utilities for DAG tasks."""
import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional

import requests
from airflow.hooks.base import BaseHook

logger = logging.getLogger(__name__)


def build_saga_event(
    event_type: str,
    event_data: Dict[str, Any],
    context: Dict[str, Any],
    task_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Build a consistent Saga event with all DAG and operator context. Pure function.
    
    Args:
        event_type: Event type (e.g., "TaskCompleted", "TaskFailed")
        event_data: Event-specific data payload
        context: Airflow context dictionary
        task_id: Optional task ID (defaults to task_instance.task_id from context)
        
    Returns:
        Complete saga event dictionary with all required fields
    """
    dag = context.get('dag')
    dag_run = context.get('dag_run')
    task_instance = context.get('task_instance')
    
    # Use provided task_id or extract from context
    if not task_id and task_instance:
        task_id = task_instance.task_id
    
    event = {
        "event_type": event_type,
        "event_data": event_data,
        "task_id": task_id,
        "dag_id": dag.dag_id if dag else None,
        "dag_run_id": dag_run.run_id if dag_run else None,
        "execution_date": dag_run.execution_date.isoformat() if dag_run and dag_run.execution_date else None,
        "try_number": task_instance.try_number if task_instance else None,
        "operator_type": None,
        "operator_id": None,
        "operator_params": None,
        "occurred_at": datetime.utcnow().isoformat()
    }
    
    # Extract operator information
    if task_instance and task_instance.task:
        operator = task_instance.task
        event["operator_type"] = operator.__class__.__name__
        event["operator_id"] = operator.task_id
        
        # Extract minimal operator params (only what's already available)
        operator_params = {}
        if hasattr(operator, 'rpa_key_id'):
            operator_params["rpa_key_id"] = operator.rpa_key_id
        if hasattr(operator, 'rpa_api_conn_id'):
            operator_params["rpa_api_conn_id"] = operator.rpa_api_conn_id
        if hasattr(operator, 'robot_test_file'):
            operator_params["robot_test_file"] = operator.robot_test_file
        if hasattr(operator, 'callback_path'):
            operator_params["callback_path"] = operator.callback_path
        if operator_params:
            event["operator_params"] = operator_params
    
    return event


def get_saga_from_context(context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Get SAGA from XCom, trying multiple keys and upstream tasks.
    
    Pulls from upstream tasks (start_saga, read_input_xls, etc.) to get the saga.
    Always logs the saga when found.
    
    Returns:
        SAGA dict or None
    """
    ti = context.get('task_instance')
    if not ti:
        logger.warning("Task instance not found in context")
        return None
    
    dag = context.get('dag')
    task_id = ti.task_id
    
    # Get upstream task IDs (tasks that this task depends on)
    upstream_task_ids = []
    if dag and task_id in dag.task_dict:
        task = dag.task_dict[task_id]
        upstream_task_ids = [upstream.task_id for upstream in task.upstream_list]
    
    logger.info(f"[{task_id}] Looking for SAGA in XCom. Upstream tasks: {upstream_task_ids}")
    
    # Try to get SAGA from upstream tasks first (most recent)
    # Try from most recent upstream task (last in list) backwards
    for upstream_task_id in reversed(upstream_task_ids):
        # Try 'saga' key
        saga = ti.xcom_pull(task_ids=upstream_task_id, key='saga', default=None)
        if saga:
            logger.info(f"[{task_id}] Found SAGA in upstream task '{upstream_task_id}' with key 'saga'")
            # Validate saga_id immediately after retrieval
            if not isinstance(saga, dict):
                logger.error(f"[{task_id}] SAGA from '{upstream_task_id}' is not a dict: {type(saga)}")
                continue
            if "saga_id" not in saga or not saga.get("saga_id"):
                logger.error(
                    f"[{task_id}] SAGA from '{upstream_task_id}' MISSING saga_id! "
                    f"Saga keys: {list(saga.keys())}"
                )
                logger.error(f"[{task_id}] Full saga from '{upstream_task_id}': {json.dumps(saga, indent=2, ensure_ascii=False)}")
                # Continue to next upstream task instead of returning invalid saga
                continue
            log_saga(saga, task_id=task_id)
            return saga
        
        # Try 'rpa_payload' key (backward compatibility)
        rpa_payload = ti.xcom_pull(task_ids=upstream_task_id, key='rpa_payload', default=None)
        if rpa_payload and isinstance(rpa_payload, dict) and 'rpa_key_id' in rpa_payload:
            logger.info(f"[{task_id}] Found SAGA in upstream task '{upstream_task_id}' with key 'rpa_payload'")
            # Validate saga_id for rpa_payload too
            if "saga_id" not in rpa_payload or not rpa_payload.get("saga_id"):
                logger.error(
                    f"[{task_id}] rpa_payload from '{upstream_task_id}' MISSING saga_id! "
                    f"Keys: {list(rpa_payload.keys())}"
                )
                continue
            log_saga(rpa_payload, task_id=task_id)
            return rpa_payload
    
    # Fallback: Try to get from current task (in case saga was pushed in same task)
    saga = ti.xcom_pull(key='saga', default=None)
    if saga:
        logger.info(f"[{task_id}] Found SAGA in current task with key 'saga'")
        log_saga(saga, task_id=task_id)
        return saga
    
    # Try from rpa_payload in current task (backward compatibility)
    rpa_payload = ti.xcom_pull(key='rpa_payload', default=None)
    if rpa_payload and isinstance(rpa_payload, dict) and 'rpa_key_id' in rpa_payload:
        logger.info(f"[{task_id}] Found SAGA in current task with key 'rpa_payload'")
        log_saga(rpa_payload, task_id=task_id)
        return rpa_payload
    
    # Try from webhook_data
    webhook_data = ti.xcom_pull(key='webhook_data', default=None)
    if webhook_data and isinstance(webhook_data, dict):
        if 'saga' in webhook_data:
            logger.info(f"[{task_id}] Found SAGA in webhook_data")
            log_saga(webhook_data['saga'], task_id=task_id)
            return webhook_data['saga']
        # If webhook_data itself is a SAGA-like structure
        if 'rpa_key_id' in webhook_data and 'rpa_request' in webhook_data:
            logger.info(f"[{task_id}] Found SAGA-like structure in webhook_data")
            log_saga(webhook_data, task_id=task_id)
            return webhook_data
    
    logger.warning(f"[{task_id}] SAGA not found in XCom from upstream tasks: {upstream_task_ids}")
    return None


def log_saga(saga: Optional[Dict[str, Any]], task_id: str = None) -> None:
    """
    Log SAGA as INFO level with nested structure support.
    
    Args:
        saga: SAGA dictionary (can contain nested robot_sagas)
        task_id: Optional task ID for context
    """
    if saga:
        task_prefix = f"[{task_id}] " if task_id else ""
        
        # Log main saga
        saga_id = saga.get("saga_id", "N/A")
        rpa_key_id = saga.get("rpa_key_id", "N/A")
        current_state = saga.get("current_state", "UNKNOWN")
        events_count = len(saga.get("events", []))
        
        logger.info(
            f"{task_prefix}SAGA {saga_id} "
            f"(state={current_state}, rpa_key_id={rpa_key_id}, events={events_count})"
        )
        
        # Warn if saga_id is missing
        if saga_id == "N/A" or not saga_id:
            logger.error(
                f"{task_prefix}SAGA MISSING saga_id! Saga keys: {list(saga.keys())}"
            )
            logger.error(f"{task_prefix}Full saga structure: {json.dumps(saga, indent=2, ensure_ascii=False)}")
        
        # Log nested robot sagas if present
        robot_sagas = saga.get("robot_sagas", [])
        if robot_sagas:
            logger.info(f"{task_prefix}  Nested Robot Sagas ({len(robot_sagas)}):")
            for rs in robot_sagas:
                rs_id = rs.get("saga_id", "N/A")
                rs_state = rs.get("current_state", "UNKNOWN")
                rs_events = len(rs.get("events", []))
                logger.info(
                    f"{task_prefix}    Robot SAGA {rs_id} "
                    f"(state={rs_state}, events={rs_events})"
                )
        
        # Always log full SAGA structure at INFO level
        logger.info(f"{task_prefix}Full SAGA structure: {json.dumps(saga, indent=2, ensure_ascii=False)}")
    else:
        logger.warning(f"[{task_id}] SAGA not found for logging" if task_id else "SAGA not found for logging")


def get_saga_rpa_key_id(saga: Optional[Dict[str, Any]]) -> Optional[str]:
    """Get rpa_key_id from SAGA."""
    if saga and isinstance(saga, dict):
        return saga.get('rpa_key_id')
    return None


def get_saga_rpa_request(saga: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Get RPA request data from SAGA.
    
    Returns 'data' field (rpa_request_object was replaced by 'data').
    Falls back to 'rpa_request' for backward compatibility.
    """
    if saga and isinstance(saga, dict):
        # Use 'data' field (rpa_request_object was replaced)
        return saga.get('data') or saga.get('rpa_request')
    return None


def send_saga_event_to_api(
    saga: Dict[str, Any],
    event: Dict[str, Any],
    rpa_api_conn_id: str = "rpa_api",
    timeout: int = 30
) -> bool:
    """
    Send saga event to rpa-api for persistence. Pure function.
    
    Args:
        saga: Saga dictionary with saga_id
        event: Event dictionary (should be built with build_saga_event)
        rpa_api_conn_id: Airflow connection ID for rpa-api
        timeout: Request timeout in seconds
        
    Returns:
        True if successful, False otherwise
    """
    saga_id = saga.get("saga_id")
    if not saga_id:
        logger.error("Cannot send event: saga missing saga_id")
        return False


def update_saga_data_in_api(
    saga: Dict[str, Any],
    rpa_api_conn_id: str = "rpa_api",
    timeout: int = 30
) -> bool:
    """
    Update saga data payload in rpa-api.
    """
    saga_id = saga.get("saga_id")
    data = saga.get("data")

    if not saga_id:
        logger.error("Cannot update saga data: saga missing saga_id")
        return False

    if data is None:
        logger.warning("Saga has no data field to update in API")
        return False

    try:
        conn = BaseHook.get_connection(rpa_api_conn_id)
        schema = conn.schema or "http"
        host = conn.host
        port = conn.port or 3000
        api_url = f"{schema}://{host}:{port}/api/v1/saga/data"

        payload = {
            "saga_id": saga_id,
            "data": data,
        }

        response = requests.put(
            api_url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=timeout,
        )

        if response.status_code in [200]:
            logger.info("Successfully updated saga %s data in rpa-api", saga_id)
            return True

        logger.warning(
            "Failed to update saga data in rpa-api: status %s, response: %s",
            response.status_code,
            response.text,
        )
        return False
    except Exception as exc:
        logger.error("Error updating saga data in rpa-api: %s", exc)
        return False
    
    try:
        conn = BaseHook.get_connection(rpa_api_conn_id)
        schema = conn.schema or 'http'
        host = conn.host
        port = conn.port or 3000
        api_url = f"{schema}://{host}:{port}/api/v1/saga/event"
        
        payload = {
            "saga_id": saga_id,
            "event_type": event.get("event_type"),
            "event_data": event.get("event_data"),
            "task_id": event.get("task_id"),
            "dag_id": event.get("dag_id"),
            "dag_run_id": event.get("dag_run_id"),
            "execution_date": event.get("execution_date"),
            "try_number": event.get("try_number"),
            "operator_type": event.get("operator_type"),
            "operator_id": event.get("operator_id"),
            "operator_params": event.get("operator_params")
        }
        
        response = requests.post(
            api_url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=timeout
        )
        
        if response.status_code in [200, 201]:
            logger.info(f"Successfully sent event {event.get('event_type')} to rpa-api for saga {saga_id}")
            return True
        else:
            logger.warning(
                f"Failed to send event to rpa-api: status {response.status_code}, "
                f"response: {response.text}"
            )
            return False
    except Exception as e:
        logger.error(f"Error sending event to rpa-api: {e}")
        return False

