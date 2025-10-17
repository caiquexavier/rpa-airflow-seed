"""Message handler that triggers Robot Framework runs."""
from pathlib import Path
from typing import Dict
import subprocess
import json
import requests
import os
import xml.etree.ElementTree as ET
import re


def run_robot_tests(project_path: Path, robot_exe: Path, tests_path: Path, results_dir: Path) -> bool:
    results_dir.mkdir(exist_ok=True)
    result = subprocess.run([
        str(robot_exe),
        "--outputdir", str(results_dir),
        str(tests_path)
    ], capture_output=True, text=True)
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr)
    return result.returncode == 0


def call_webhook(exec_id: int, rpa_key_id: str, status: str, rpa_response: Dict, error_message: str = None):
    """Call the webhook to report execution status."""
    try:
        # Get webhook URL from environment or use default
        webhook_url = os.getenv("RPA_API_WEBHOOK_URL", "http://localhost:3000/updateRpaExecution")
        
        # Enforce exact payload contract expected by the API
        if status == "SUCCESS":
            payload = {
                "exec_id": exec_id,
                "rpa_key_id": rpa_key_id,
                "status": "SUCCESS",
                "rpa_response": {"success": "OK"},
                "error_message": None
            }
        else:
            # status == FAIL
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
        
        if response.status_code == 200:
            print(f"Successfully reported status for exec_id={exec_id}: {status}")
            return True
        else:
            print(f"Webhook call failed for exec_id={exec_id}: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"Error calling webhook for exec_id={exec_id}: {e}")
        return False


def _extract_error_detail_from_output(results_dir: Path) -> str:
    """Extract a concise error detail string from Robot Framework output.xml."""
    try:
        output_xml = results_dir / 'output.xml'
        if not output_xml.exists():
            return "Robot execution failed"
        tree = ET.parse(str(output_xml))
        root = tree.getroot()
        # Prefer a FAIL status with detailed multiline content to parse selector and timeout
        for status in root.iter('status'):
            if status.get('status') == 'FAIL' and (status.text and status.text.strip()):
                text = status.text.strip()
                # Try to extract TimeoutError details
                # Example lines:
                # TimeoutError: locator.waitFor: Timeout 15000ms exceeded.
                # Call log:
                #   - waiting for locator('#email') to be visible
                ms_match = re.search(r"Timeout\s+(\d+)ms", text)
                locator_match = re.search(r"waiting for locator\('([^']+)'\) to be ([^\n\r]+)", text)
                if ms_match and locator_match:
                    ms = int(ms_match.group(1))
                    seconds = max(1, round(ms / 1000))
                    selector = locator_match.group(1)
                    condition = locator_match.group(2).strip()
                    return f"Element {selector} not {condition} within {seconds}s"
                # Generic first line fallback
                return text.splitlines()[0][:300]
        # Fallback: first FAIL message line
        for msg in root.iter('msg'):
            if msg.get('level') == 'FAIL' and (msg.text and msg.text.strip()):
                return msg.text.strip().splitlines()[0][:300]
    except Exception:
        pass
    return "Robot execution failed"


def handle_message(message: Dict, project_path: Path, robot_exe: Path, tests_path: Path, results_dir: Path) -> bool:
    """Handle RPA execution message and report back via webhook."""
    exec_id = message.get('exec_id')
    rpa_key_id = message.get('rpa_key_id')
    
    if not exec_id or not rpa_key_id:
        print("Error: Message missing 'exec_id' or 'rpa_key_id' field")
        return False
    
    print(f"Processing execution: exec_id={exec_id}, rpa_key_id={rpa_key_id}")
    
    # Run robot tests
    success = run_robot_tests(project_path, robot_exe, tests_path, results_dir)
    
    # Prepare simplified response data (text only)
    if success:
        rpa_response = {"success": "OK"}
    else:
        error_detail = _extract_error_detail_from_output(results_dir)
        rpa_response = {"error": error_detail}
    
    # Report status via webhook
    status = "SUCCESS" if success else "FAIL"
    error_message = None if success else rpa_response.get("error") or "Robot execution failed"
    
    webhook_success = call_webhook(exec_id, rpa_key_id, status, rpa_response, error_message)
    
    if not webhook_success:
        print(f"Warning: Failed to report status for exec_id={exec_id}")
    
    return success


