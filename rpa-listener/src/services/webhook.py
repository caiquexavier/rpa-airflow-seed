"""Webhook service for reporting execution status."""
from typing import Dict, Optional
import os
import requests


def call_webhook(exec_id: int, rpa_key_id: str, status: str, rpa_response: Dict, error_message: Optional[str] = None) -> bool:
    """Call the webhook to report execution status."""
    webhook_url = os.getenv("RPA_API_WEBHOOK_URL", "http://localhost:3000/updateRpaExecution")
    if status == "SUCCESS":
        payload = {
            "exec_id": exec_id,
            "rpa_key_id": rpa_key_id,
            "status": "SUCCESS",
            "rpa_response": rpa_response,
            "error_message": None
        }
    else:
        error_text = None
        if isinstance(rpa_response, dict):
            error_text = rpa_response.get("error")
        if not error_text:
            error_text = error_message or "Robot execution failed"
        payload = {
            "exec_id": exec_id,
            "rpa_key_id": rpa_key_id,
            "status": "FAIL",
            "rpa_response": {"error": error_text},
            "error_message": error_text
        }
    response = requests.post(
        webhook_url,
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=30
    )
    return response.status_code == 200


