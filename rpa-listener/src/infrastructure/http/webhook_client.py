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
    urls_to_try = _build_fallback_urls(webhook_url)
    logger.info(
        "Dispatching callback webhook",
        extra={
            "callback_path": callback_path,
            "attempts": len(urls_to_try),
            "status": status,
            "saga_id": saga_id,
        },
    )
    return _try_webhook_call(urls_to_try, payload)


def _build_webhook_url(callback_path: str) -> str:
    """Build webhook URL from callback path."""
    api_base_url = os.getenv("AIRFLOW_API_BASE_URL", "http://localhost:8000")
    if not api_base_url.endswith('/'):
        api_base_url = api_base_url.rstrip('/')
    return f"{api_base_url}{callback_path}"


def _build_webhook_payload(saga_id: Optional[int], robot_saga: Dict, status: str) -> Dict:
    """Build payload with status, SAGA, and RobotOperatorSaga."""
    return {
        "status": status.upper(),
        "robot_operator_saga": robot_saga,
        "saga_id": saga_id
    }


def _build_fallback_urls(webhook_url: str) -> list:
    """Build list of URLs to try with fallback."""
    urls_to_try = [webhook_url]
    if "localhost:8000" in webhook_url:
        urls_to_try.append(webhook_url.replace("localhost:8000", "airflow-webserver:8000"))
    elif "airflow-webserver:8000" in webhook_url:
        urls_to_try.append(webhook_url.replace("airflow-webserver:8000", "localhost:8000"))
    return urls_to_try


def _try_webhook_call(urls_to_try: list, payload: Dict) -> bool:
    """Try webhook call with fallback URLs."""
    last_error = None
    for url in urls_to_try:
        try:
            response = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=30)
            if response.status_code in [200, 201, 202]:
                logger.info(
                    "Callback webhook succeeded",
                    extra={"url": url, "status_code": response.status_code},
                )
                return True
            else:
                error_msg = f"Callback webhook call failed: status_code={response.status_code}, response={response.text}"
                logger.warning(error_msg, extra={"url": url, "status_code": response.status_code})
                last_error = error_msg
                continue
        except requests.exceptions.ConnectionError as e:
            error_msg = f"Callback webhook connection error to {url}: {e}"
            last_error = error_msg
            logger.warning(error_msg)
            continue
        except Exception as e:
            error_msg = f"Callback webhook call exception to {url}: {type(e).__name__}: {e}"
            last_error = error_msg
            logger.exception(error_msg)
            continue
    
    if last_error:
        logger.error("All callback webhook attempts failed. Last error: %s", last_error)
    return False

