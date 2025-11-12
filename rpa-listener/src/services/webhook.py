# Webhook service for reporting execution status to API and updating rpa_execution
from typing import Dict, Optional
import os
import requests


def call_webhook(exec_id: int, rpa_key_id: str, status: str, rpa_response: Dict, error_message: Optional[str] = None) -> bool:
    # Call the webhook API endpoint to update rpa_execution status
    webhook_url = os.getenv("RPA_API_WEBHOOK_URL", "http://localhost:3000/updateRpaExecution")
    status_upper = status.upper()
    if status_upper == "SUCCESS":
        payload = {"exec_id": exec_id, "rpa_key_id": rpa_key_id, "status": "SUCCESS", "rpa_response": rpa_response, "error_message": None}
    else:
        error_text = rpa_response.get("error") if isinstance(rpa_response, dict) else None
        if not error_text:
            error_text = error_message or "Robot execution failed"
        payload = {"exec_id": exec_id, "rpa_key_id": rpa_key_id, "status": "FAIL", "rpa_response": {"error": error_text}, "error_message": error_text}
    try:
        response = requests.post(webhook_url, json=payload, headers={"Content-Type": "application/json"}, timeout=30)
        return response.status_code == 200
    except Exception:
        return False


