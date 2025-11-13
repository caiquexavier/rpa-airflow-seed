# Webhook service for reporting execution status to API and updating rpa_execution
from typing import Dict, Optional
import os
import sys
import requests
import json


def call_webhook(exec_id: int, rpa_key_id: str, status: str, rpa_response: Dict, error_message: Optional[str] = None, saga: Optional[Dict] = None) -> bool:
    # Call the webhook API endpoint to update rpa_execution status with updated SAGA
    # Default to localhost (for listener running outside Docker), but allow override via env var
    webhook_url = os.getenv("RPA_API_WEBHOOK_URL", "http://localhost:3000/updateRpaExecution")
    status_upper = status.upper()
    
    if status_upper == "SUCCESS":
        payload = {"exec_id": exec_id, "rpa_key_id": rpa_key_id, "status": "SUCCESS", "rpa_response": rpa_response, "error_message": None}
    else:
        error_text = rpa_response.get("error") if isinstance(rpa_response, dict) else None
        if not error_text:
            error_text = error_message or "Robot execution failed"
        payload = {"exec_id": exec_id, "rpa_key_id": rpa_key_id, "status": "FAIL", "rpa_response": {"error": error_text}, "error_message": error_text}
    
    # Include updated SAGA in payload
    if saga:
        payload["saga"] = saga
    
    print(f"INFO: Calling webhook: {webhook_url}", file=sys.stdout)
    print(f"INFO: Webhook payload: exec_id={exec_id}, rpa_key_id={rpa_key_id}, status={status_upper}", file=sys.stdout)
    
    # Try webhook URL, with fallback if it fails
    urls_to_try = [webhook_url]
    # If using localhost and it fails, try Docker service name as fallback
    if "localhost:3000" in webhook_url:
        urls_to_try.append(webhook_url.replace("localhost:3000", "rpa-api:3000"))
    # If using Docker service name and it fails, try localhost as fallback
    elif "rpa-api:3000" in webhook_url:
        urls_to_try.append(webhook_url.replace("rpa-api:3000", "localhost:3000"))
    
    last_error = None
    for url in urls_to_try:
        try:
            print(f"INFO: Attempting webhook call to: {url}", file=sys.stdout)
            response = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=30)
            print(f"INFO: Webhook response: status_code={response.status_code}", file=sys.stdout)
            
            if response.status_code == 200:
                print(f"INFO: Webhook call successful for exec_id={exec_id}", file=sys.stdout)
                try:
                    response_data = response.json()
                    print(f"INFO: Webhook response data: {json.dumps(response_data, indent=2, ensure_ascii=False)}", file=sys.stdout)
                except:
                    pass
                return True
            else:
                error_msg = f"Webhook call failed for exec_id={exec_id}: status_code={response.status_code}, response={response.text}"
                print(f"ERROR: {error_msg}", file=sys.stderr)
                last_error = error_msg
                # Don't try next URL if we got a response (even if error) - server is reachable
                break
        except requests.exceptions.ConnectionError as e:
            error_msg = f"Webhook connection error for exec_id={exec_id} to {url}: {e}"
            print(f"ERROR: {error_msg}", file=sys.stderr)
            last_error = error_msg
            # Try next URL if available
            continue
        except requests.exceptions.Timeout as e:
            error_msg = f"Webhook timeout for exec_id={exec_id} to {url}: {e}"
            print(f"ERROR: {error_msg}", file=sys.stderr)
            last_error = error_msg
            # Try next URL if available
            continue
        except Exception as e:
            error_msg = f"Webhook call exception for exec_id={exec_id} to {url}: {type(e).__name__}: {e}"
            print(f"ERROR: {error_msg}", file=sys.stderr)
            import traceback
            print(f"ERROR: Traceback: {traceback.format_exc()}", file=sys.stderr)
            last_error = error_msg
            # Try next URL if available
            continue
    
    # All URLs failed
    print(f"ERROR: All webhook attempts failed. Last error: {last_error}", file=sys.stderr)
    return False


