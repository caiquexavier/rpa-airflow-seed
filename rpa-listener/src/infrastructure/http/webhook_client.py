"""Webhook client for Airflow task triggering."""
import logging
import os
from typing import Dict, Optional

import requests

logger = logging.getLogger(__name__)


def call_callback_webhook(
    callback_path: str,
    saga_id: Optional[int],
    robot_saga: Dict,
    status: str
) -> bool:
    """Call callback webhook to trigger next Airflow task."""
    webhook_url = _build_webhook_url(callback_path)
    payload = _build_webhook_payload(saga_id, robot_saga, status)
    logger.info(
        f"Dispatching callback webhook to {webhook_url}",
        extra={
            "callback_path": callback_path,
            "webhook_url": webhook_url,
            "status": status,
            "saga_id": saga_id,
        },
    )
    return _try_webhook_call(webhook_url, payload)


def _build_webhook_url(callback_path: str) -> str:
    """Build webhook URL from callback path."""
    api_base_url = os.getenv("AIRFLOW_API_BASE_URL", "http://localhost:8000")
    # Normalize URL - ensure no trailing slash before appending path
    if not api_base_url.endswith('/'):
        api_base_url = api_base_url.rstrip('/')
    # Ensure callback_path starts with /
    if not callback_path.startswith('/'):
        callback_path = '/' + callback_path
    return f"{api_base_url}{callback_path}"


def _build_webhook_payload(saga_id: Optional[int], robot_saga: Dict, status: str) -> Dict:
    """Build payload with status, SAGA, and RobotOperatorSaga."""
    return {
        "status": status.upper(),
        "robot_operator_saga": robot_saga,
        "saga_id": saga_id
    }


def _try_webhook_call(webhook_url: str, payload: Dict) -> bool:
    """Call webhook URL with payload. Returns True on success, False on failure."""
    try:
        logger.debug(f"Calling webhook URL: {webhook_url} with payload: {payload}")
        response = requests.post(webhook_url, json=payload, headers={"Content-Type": "application/json"}, timeout=30)
        if response.status_code in [200, 201, 202]:
            logger.info(
                "Callback webhook succeeded",
                extra={"url": webhook_url, "status_code": response.status_code},
            )
            return True
        else:
            error_msg = f"Callback webhook call failed: status_code={response.status_code}, response={response.text}, url={webhook_url}"
            logger.error(error_msg, extra={"url": webhook_url, "status_code": response.status_code, "response_text": response.text})
            return False
    except requests.exceptions.ConnectionError as e:
        error_msg = f"Callback webhook connection error to {webhook_url}: {e}"
        logger.error(error_msg)
        return False
    except Exception as e:
        error_msg = f"Callback webhook call exception to {webhook_url}: {type(e).__name__}: {e}"
        logger.exception(error_msg)
        return False

