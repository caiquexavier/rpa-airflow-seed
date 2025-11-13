# Listener controller to execute Robot Framework tests from queue messages and call webhook
from pathlib import Path
from typing import Dict, Optional, Tuple
import subprocess
import json
import os
import sys
import re
import time
import xml.etree.ElementTree as ET
from ..services.webhook import call_webhook


def run_robot_tests(project_path: Path, robot_exe: Path, tests_path: Path, results_dir: Path, message_data: Optional[Dict] = None, timeout_seconds: int = 7200) -> Tuple[bool, Optional[str]]:
    # Run Robot Framework tests with optional variable file built from message_data
    # Returns (success: bool, error_message: Optional[str])
    # timeout_seconds: Maximum execution time (default 2 hours)
    process = None
    try:
        results_dir.mkdir(exist_ok=True)
        variable_file = None
        if message_data:
            variable_file = results_dir / "input_variables.json"
            with open(variable_file, 'w', encoding='utf-8') as f:
                json.dump(message_data, f, ensure_ascii=False, indent=2)
        cmd = [str(robot_exe), "--outputdir", str(results_dir)]
        if variable_file:
            cmd.extend(["--variablefile", str(variable_file)])
        cmd.append(str(tests_path))
        env = os.environ.copy()
        env['PYTHONUNBUFFERED'] = '1'
        env['PYTHONIOENCODING'] = 'utf-8'
        sys.stdout.flush()
        
        # Start process
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env, bufsize=1, universal_newlines=True, cwd=str(project_path))
        assert process.stdout is not None
        
        # Capture output for error extraction and real-time monitoring
        captured_output = []
        retry_loop_detected = False
        retry_count = 0
        last_retry_time = 0
        start_time = time.time()
        
        # Read output line by line with timeout detection
        # Use a thread-safe queue or polling approach for Windows compatibility
        last_output_time = start_time
        no_output_timeout = 300  # 5 minutes without output = likely stuck
        
        while True:
            # Check for overall timeout
            elapsed = time.time() - start_time
            if elapsed > timeout_seconds:
                error_msg = f"Robot execution timeout after {timeout_seconds // 60} minutes"
                print(f"ERROR: {error_msg}", file=sys.stderr)
                _terminate_process(process)
                return (False, error_msg)
            
            # Check if process has terminated (non-blocking check)
            if process.poll() is not None:
                # Process terminated, read any remaining output
                remaining = process.stdout.read()
                if remaining:
                    for line in remaining.splitlines():
                        line_stripped = line.rstrip()
                        if line_stripped:
                            print(line_stripped)
                            sys.stdout.flush()
                            captured_output.append(line_stripped)
                break
            
            # Try to read a line (this may block, but we check timeout above)
            # On Windows, readline() can block, so we check timeout frequently
            line = None
            try:
                # For non-blocking read on Windows, we'd need select or threading
                # For now, readline() will block, but we check timeout in loop
                line = process.stdout.readline()
            except Exception as e:
                print(f"WARNING: Error reading output: {e}", file=sys.stderr)
                break
            
            if not line:
                # No line available, check if we've had no output for too long
                current_time = time.time()
                if current_time - last_output_time > no_output_timeout:
                    error_msg = f"Robot execution stalled (no output for {no_output_timeout // 60} minutes)"
                    print(f"ERROR: {error_msg}", file=sys.stderr)
                    _terminate_process(process)
                    return (False, error_msg)
                # Wait a bit before checking again
                time.sleep(0.5)
                continue
            
            # Got a line, update last output time
            last_output_time = time.time()
            line_stripped = line.rstrip()
            print(line_stripped)
            sys.stdout.flush()
            captured_output.append(line_stripped)
            
            # Detect retry loop patterns in real-time
            if _is_retry_loop_line(line_stripped):
                current_time = time.time()
                if current_time - last_retry_time < 10:  # Multiple retries within 10 seconds
                    retry_count += 1
                else:
                    retry_count = 1
                last_retry_time = current_time
                
                # If we see 2+ retries (more aggressive), terminate immediately
                # This prevents the listener from being blocked by retry loops
                if retry_count >= 2:
                    retry_loop_detected = True
                    error_msg = _extract_retry_error_from_line(line_stripped)
                    print(f"ERROR: Retry loop detected (count: {retry_count}) - {error_msg}", file=sys.stderr)
                    _terminate_process(process)
                    # Wait a moment for process to terminate
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        pass
                    return (False, error_msg)
        
        process.stdout.close()
        exit_code = process.wait()
        
        # Check for connection errors or other critical errors in output
        output_text = '\n'.join(captured_output)
        error_msg = _extract_error_from_output_text(output_text)
        
        if exit_code != 0 or retry_loop_detected:
            return (False, error_msg or "Robot execution failed")
        return (True, None)
        
    except subprocess.SubprocessError as e:
        error_msg = f"Subprocess error: {str(e)}"
        print(f"ERROR: {error_msg}", file=sys.stderr)
        if process:
            _terminate_process(process)
        return (False, error_msg)
    except Exception as e:
        error_msg = f"Robot execution error: {str(e)}"
        print(f"ERROR: {error_msg}", file=sys.stderr)
        if process:
            _terminate_process(process)
        return (False, error_msg)


def _terminate_process(process: subprocess.Popen) -> None:
    # Terminate process gracefully, then force kill if needed
    try:
        if process.poll() is None:  # Process still running
            if sys.platform == 'win32':
                # Windows: use taskkill or terminate
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
            else:
                # Unix: send SIGTERM, then SIGKILL
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
    except Exception as e:
        print(f"WARNING: Error terminating process: {e}", file=sys.stderr)


def _is_retry_loop_line(line: str) -> bool:
    # Check if line indicates a retry loop pattern
    # Match the specific error pattern: "[ WARN ] Retrying (Retry(...)) after connection broken by 'NewConnectionError(...)': /session/..."
    retry_patterns = [
        r'\[ WARN \].*Retrying.*after connection broken',
        r'\[ WARN \].*Retrying.*Retry\(total=',
        r'Retrying.*after connection broken by.*NewConnectionError',
        r'NewConnectionError.*Failed to establish.*\[WinError',
        r'Connection.*refused.*retrying',
        r'Failed to establish.*Nenhuma liga',
    ]
    for pattern in retry_patterns:
        if re.search(pattern, line, re.IGNORECASE):
            return True
    return False


def _extract_retry_error_from_line(line: str) -> str:
    # Extract meaningful error from retry line
    # Example: "[ WARN ] Retrying (Retry(total=0, ...)) after connection broken by 'NewConnectionError(...)': /session/..."
    # Format: [ WARN ] Retrying (...) after connection broken by 'NewConnectionError(...)': /session/...
    if 'NewConnectionError' in line:
        # Try to extract WinError details: [WinError 10061] Nenhuma liga...
        match = re.search(r'\[WinError\s+(\d+)\]([^\']*)', line, re.IGNORECASE | re.DOTALL)
        if match:
            error_code = match.group(1)
            error_msg = match.group(2).strip()[:150]
            return f"Connection failed: WinError {error_code} - {error_msg}"
        
        # Try to extract "Failed to establish" message
        match = re.search(r"Failed to establish[^']*(\[WinError[^\]]+\][^']*)", line, re.IGNORECASE | re.DOTALL)
        if match:
            error_detail = match.group(1).strip()[:200]
            return f"Connection failed: {error_detail}"
        
        # Fallback: extract session path if available
        match = re.search(r":\s*(/session/[^'\s]+)", line)
        if match:
            return f"Connection failed to {match.group(1)}"
    
    # If it's a retry line but no NewConnectionError, extract the key part
    if 'Retrying' in line and 'connection broken' in line:
        # Extract the endpoint/path if available
        match = re.search(r":\s*(/session/[^'\s]+)", line)
        if match:
            return f"Retry loop: Connection broken to {match.group(1)}"
    
    # Default: return first 300 chars of the line
    return line.strip()[:300]


def handle_message(message: Dict, project_path: Path, robot_exe: Path, tests_path: Path, results_dir: Path) -> bool:
    # Handle message by executing Robot Framework tests, then posting to API to update rpa_execution with SAGA
    # Always ensures webhook is called on failure, even if exceptions occur
    exec_id = message.get('exec_id')
    rpa_key_id = message.get('rpa_key_id')
    saga = message.get('saga', {})
    success = False
    rpa_response = {}
    error_message = None
    
    # Log SAGA at start
    print(f"INFO SAGA: {json.dumps(saga, indent=2, ensure_ascii=False)}", file=sys.stdout)
    
    try:
        # Run robot tests - now returns (success, error_message)
        success, execution_error = run_robot_tests(project_path, robot_exe, tests_path, results_dir, message)
        
        # Build response - wrap in try/except to handle XML parsing errors
        try:
            rpa_response = _build_rpa_response(message, results_dir, success)
        except Exception as e:
            print(f"WARNING: Error building RPA response: {e}", file=sys.stderr)
            rpa_response = {"error": str(e)} if not success else {}
        
        # Determine error message
        if not success:
            error_message = execution_error or rpa_response.get("error") or "Robot execution failed"
            status = "FAIL"
        else:
            status = "SUCCESS"
        
        # Update SAGA with robot execution event
        if not isinstance(saga, dict):
            saga = {}
        
        # Ensure SAGA has required fields
        if "events" not in saga:
            saga["events"] = []
        if "current_state" not in saga:
            saga["current_state"] = "PENDING"
        
        # Add robot execution event to SAGA
        from datetime import datetime
        robot_event = {
            "event_type": "RobotCompleted" if success else "RobotFailed",
            "event_data": {
                "status": status,
                "rpa_response": rpa_response,
                "error_message": error_message
            },
            "task_id": "robot_execution",
            "dag_id": saga.get("rpa_key_id", rpa_key_id),
            "occurred_at": datetime.utcnow().isoformat()
        }
        saga["events"].append(robot_event)
        saga["current_state"] = "COMPLETED" if success else "FAILED"
        
        # Log updated SAGA
        print(f"INFO SAGA: {json.dumps(saga, indent=2, ensure_ascii=False)}", file=sys.stdout)
            
    except Exception as e:
        # Catch any exception during execution or response building
        success = False
        status = "FAIL"
        error_message = f"Execution error: {str(e)}"
        rpa_response = {"error": error_message}
        print(f"ERROR in handle_message: {error_message}", file=sys.stderr)
        
        # Update SAGA with error event
        if not isinstance(saga, dict):
            saga = {}
        if "events" not in saga:
            saga["events"] = []
        from datetime import datetime
        error_event = {
            "event_type": "RobotError",
            "event_data": {
                "error": error_message
            },
            "task_id": "robot_execution",
            "dag_id": saga.get("rpa_key_id", rpa_key_id),
            "occurred_at": datetime.utcnow().isoformat()
        }
        saga["events"].append(error_event)
        saga["current_state"] = "FAILED"
        print(f"INFO SAGA: {json.dumps(saga, indent=2, ensure_ascii=False)}", file=sys.stdout)
    
    # Always attempt to call webhook if we have exec_id and rpa_key_id, passing updated SAGA
    if exec_id and rpa_key_id:
        print(f"INFO: Attempting to call webhook for exec_id={exec_id}, rpa_key_id={rpa_key_id}, status={status}", file=sys.stdout)
        webhook_success = call_webhook(exec_id, rpa_key_id, status, rpa_response, error_message, saga)
        if webhook_success:
            print(f"INFO: Webhook called successfully for exec_id={exec_id}", file=sys.stdout)
        else:
            print(f"WARNING: Webhook call failed for exec_id={exec_id}", file=sys.stderr)
            # Don't fail the message processing if webhook fails, but log it
    else:
        print(f"WARNING: Cannot call webhook - missing exec_id or rpa_key_id. exec_id={exec_id}, rpa_key_id={rpa_key_id}", file=sys.stderr)
    
    return success


def _extract_error_from_output_text(output_text: str) -> Optional[str]:
    # Extract error messages from robot output text (stdout/stderr)
    # Handles connection errors, subprocess errors, retry loops, and other runtime errors
    if not output_text:
        return None
    
    # Check for retry loop patterns first (highest priority)
    retry_patterns = [
        r'\[ WARN \].*Retrying.*after connection broken.*NewConnectionError',
        r'Retrying.*after connection broken by.*NewConnectionError.*Failed to establish',
        r'NewConnectionError.*Failed to establish.*\[WinError \d+\]',
    ]
    for pattern in retry_patterns:
        match = re.search(pattern, output_text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
        if match:
            # Extract the full error line with context
            lines = output_text.split('\n')
            for i, line in enumerate(lines):
                if re.search(pattern, line, re.IGNORECASE | re.DOTALL):
                    error_msg = _extract_retry_error_from_line(line)
                    return error_msg
    
    # Check for HTTPConnectionPool errors (like the screenshot capture error)
    connection_error_patterns = [
        r'HTTPConnectionPool.*Max retries exceeded',
        r'Failed to establish a new connection',
        r'Connection refused',
        r'ConnectionError',
        r'NewConnectionError',
    ]
    for pattern in connection_error_patterns:
        match = re.search(pattern, output_text, re.IGNORECASE | re.MULTILINE)
        if match:
            # Extract the full error line
            lines = output_text.split('\n')
            for i, line in enumerate(lines):
                if re.search(pattern, line, re.IGNORECASE):
                    # Try to get context (next few lines if available)
                    context = line.strip()
                    if i + 1 < len(lines) and lines[i + 1].strip():
                        context += f": {lines[i + 1].strip()[:200]}"
                    return context[:300]
    
    # Check for WARN/ERROR keywords in Robot Framework output
    warn_error_patterns = [
        r'\[ WARN \].*could not be run on failure:.*',
        r'\[ WARN \].*Retrying.*',
        r'\[ ERROR \].*',
        r'FAIL:.*',
    ]
    for pattern in warn_error_patterns:
        match = re.search(pattern, output_text, re.IGNORECASE | re.MULTILINE)
        if match:
            error_line = match.group(0).strip()
            return error_line[:300]
    
    # Check for common exception patterns
    exception_patterns = [
        r'Exception:\s*(.+?)(?:\n|$)',
        r'Error:\s*(.+?)(?:\n|$)',
        r'Traceback.*?\n\s*(\w+Error[^\n]*)',
    ]
    for pattern in exception_patterns:
        match = re.search(pattern, output_text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
        if match:
            error_msg = match.group(1) if match.lastindex >= 1 else match.group(0)
            return error_msg.strip()[:300]
    
    return None


def _extract_error_detail_from_output(results_dir: Path) -> str:
    # Extract error detail string from Robot Framework output.xml
    try:
        output_xml = results_dir / 'output.xml'
        if not output_xml.exists():
            return "Robot execution failed"
        tree = ET.parse(str(output_xml))
        root = tree.getroot()
        
        # Collect all error messages
        error_messages = []
        
        for status in root.iter('status'):
            if status.get('status') == 'FAIL' and (status.text and status.text.strip()):
                text = status.text.strip()
                # Check for connection errors in status text
                if re.search(r'HTTPConnectionPool|Connection.*refused|Failed to establish', text, re.IGNORECASE):
                    return text.splitlines()[0][:300]
                # Check for timeout/locator errors
                ms_match = re.search(r"Timeout\s+(\d+)ms", text)
                locator_match = re.search(r"waiting for locator\('([^']+)'\) to be ([^\n\r]+)", text)
                if ms_match and locator_match:
                    ms = int(ms_match.group(1))
                    seconds = max(1, round(ms / 1000))
                    selector = locator_match.group(1)
                    condition = locator_match.group(2).strip()
                    return f"Element {selector} not {condition} within {seconds}s"
                error_messages.append(text.splitlines()[0][:300])
        
        for msg in root.iter('msg'):
            if msg.get('level') == 'FAIL' and (msg.text and msg.text.strip()):
                msg_text = msg.text.strip()
                # Check for connection errors in message text
                if re.search(r'HTTPConnectionPool|Connection.*refused|Failed to establish', msg_text, re.IGNORECASE):
                    return msg_text.splitlines()[0][:300]
                error_messages.append(msg_text.splitlines()[0][:300])
        
        # Return first error message found, or generic message
        if error_messages:
            return error_messages[0]
    except ET.ParseError as e:
        return f"XML parsing error: {str(e)[:200]}"
    except Exception as e:
        return f"Error extracting from output.xml: {str(e)[:200]}"
    return "Robot execution failed"


def _build_rpa_response(message: Dict, results_dir: Path, success: bool) -> Dict:
    # Build rpa_response with status for each nota fiscal
    rpa_request = message.get('rpa_request', {})
    notas_fiscais = rpa_request.get('notas_fiscais', [])
    if not success:
        return {"error": _extract_error_detail_from_output(results_dir)}
    errors_map = {}
    try:
        output_xml = results_dir / 'output.xml'
        if output_xml.exists():
            tree = ET.parse(str(output_xml))
            root = tree.getroot()
            current_nf = None
            for msg in root.iter('msg'):
                msg_text = msg.text or ""
                for nf in notas_fiscais:
                    nf_str = str(nf)
                    if f"Processing Nota Fiscal {nf_str}" in msg_text or f"[{nf_str}] Processing" in msg_text:
                        current_nf = nf_str
                if "Error modal detected" in msg_text:
                    if "after search:" in msg_text:
                        error_text = msg_text.split("after search:", 1)[1].strip()
                    elif ":" in msg_text:
                        error_text = msg_text.split(":", 1)[1].strip()
                    else:
                        error_text = ""
                    if current_nf and error_text:
                        errors_map[current_nf] = error_text
    except Exception:
        pass
    return {"notas_fiscais": [{"nota_fiscal": str(nf), "status": "error", "error_message": errors_map[str(nf)]} if str(nf) in errors_map else {"nota_fiscal": str(nf), "status": "success"} for nf in notas_fiscais]}




