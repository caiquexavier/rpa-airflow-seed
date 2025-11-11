"""Listener controller to execute Robot Framework tests from queue messages and call webhook."""
from pathlib import Path
from typing import Dict, Optional
import subprocess
import json
import os
import sys
import re
import xml.etree.ElementTree as ET
from ..services.webhook import call_webhook


def run_robot_tests(
    project_path: Path,
    robot_exe: Path,
    tests_path: Path,
    results_dir: Path,
    message_data: Optional[Dict] = None
) -> bool:
    """Run Robot Framework tests with optional variable file built from message_data."""
    results_dir.mkdir(exist_ok=True)

    # Create variable file with message data if provided
    variable_file = None
    if message_data:
        variable_file = results_dir / "input_variables.json"
        with open(variable_file, 'w', encoding='utf-8') as f:
            json.dump(message_data, f, ensure_ascii=False, indent=2)

    # Build robot command
    cmd = [str(robot_exe), "--outputdir", str(results_dir)]
    if variable_file:
        cmd.extend(["--variablefile", str(variable_file)])
    cmd.append(str(tests_path))

    env = os.environ.copy()
    env['PYTHONUNBUFFERED'] = '1'
    env['PYTHONIOENCODING'] = 'utf-8'

    # Stream output without extra controller logs
    sys.stdout.flush()

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=env,
        bufsize=1,
        universal_newlines=True,
        cwd=str(project_path)
    )

    # Stream subprocess output to stdout
    assert process.stdout is not None
    for line in iter(process.stdout.readline, ''):
        if not line:
            break
        print(line.rstrip())
        sys.stdout.flush()
    process.stdout.close()

    return_code = process.wait()
    return return_code == 0


def handle_message(message: Dict, project_path: Path, robot_exe: Path, tests_path: Path, results_dir: Path) -> bool:
    """Handle message by executing Robot Framework tests, call webhook, and return success flag."""
    success = run_robot_tests(project_path, robot_exe, tests_path, results_dir, message)
    rpa_response = _build_rpa_response(message, results_dir, success)
    status = "SUCCESS" if success else "FAIL"
    error_message = None if success else rpa_response.get("error") or "Robot execution failed"
    exec_id = message.get('exec_id')
    rpa_key_id = message.get('rpa_key_id')
    if exec_id and rpa_key_id:
        try:
            call_webhook(exec_id, rpa_key_id, status, rpa_response, error_message)
        except Exception:
            pass
    return success


def _extract_error_detail_from_output(results_dir: Path) -> str:
    """Extract a concise error detail string from Robot Framework output.xml."""
    try:
        output_xml = results_dir / 'output.xml'
        if not output_xml.exists():
            return "Robot execution failed"
        tree = ET.parse(str(output_xml))
        root = tree.getroot()
        for status in root.iter('status'):
            if status.get('status') == 'FAIL' and (status.text and status.text.strip()):
                text = status.text.strip()
                ms_match = re.search(r"Timeout\s+(\d+)ms", text)
                locator_match = re.search(r"waiting for locator\('([^']+)'\) to be ([^\n\r]+)", text)
                if ms_match and locator_match:
                    ms = int(ms_match.group(1))
                    seconds = max(1, round(ms / 1000))
                    selector = locator_match.group(1)
                    condition = locator_match.group(2).strip()
                    return f"Element {selector} not {condition} within {seconds}s"
                return text.splitlines()[0][:300]
        for msg in root.iter('msg'):
            if msg.get('level') == 'FAIL' and (msg.text and msg.text.strip()):
                return msg.text.strip().splitlines()[0][:300]
    except Exception:
        pass
    return "Robot execution failed"


def _build_rpa_response(message: Dict, results_dir: Path, success: bool) -> Dict:
    """Build rpa_response with status for each nota fiscal."""
    rpa_request = message.get('rpa_request', {})
    notas_fiscais = rpa_request.get('notas_fiscais', [])
    if not success:
        error_detail = _extract_error_detail_from_output(results_dir)
        return {"error": error_detail}
    notas_fiscais_status = []
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
    for nf in notas_fiscais:
        nf_str = str(nf)
        if nf_str in errors_map:
            notas_fiscais_status.append({
                "nota_fiscal": nf_str,
                "status": "error",
                "error_message": errors_map[nf_str]
            })
        else:
            notas_fiscais_status.append({
                "nota_fiscal": nf_str,
                "status": "success"
            })
    return {"notas_fiscais": notas_fiscais_status}


def call_webhook(exec_id: int, rpa_key_id: str, status: str, rpa_response: Dict, error_message: Optional[str] = None) -> bool:
    """Deprecated in controller: kept for backward-compat import; use services.webhook.call_webhook instead."""
    return call_webhook(exec_id, rpa_key_id, status, rpa_response, error_message)


