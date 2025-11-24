"""Robot Framework test execution service."""
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, Optional, Tuple

from .error_extractor import is_retry_loop_line, extract_retry_error_from_line, extract_error_from_output_text


DEFAULT_TIMEOUT_SECONDS = 7200  # 2 hours
NO_OUTPUT_TIMEOUT_SECONDS = 300  # 5 minutes


def execute_robot_tests(
    project_path: Path,
    robot_exe: Path,
    test_file_path: Path,
    results_dir: Path,
    message_data: Optional[Dict] = None,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS
) -> Tuple[bool, Optional[str]]:
    """Execute Robot Framework tests with optional variable file."""
    process = None
    try:
        # Resolve all paths to absolute
        project_path = project_path.resolve()
        test_file_path = test_file_path.resolve()
        results_dir = results_dir.resolve()
        robot_exe = robot_exe.resolve()
        if message_data:
            saga_id = message_data.get("saga_id")
            if not saga_id:
                print("WARNING: saga_id not present in message_data; robot tests depend on saga_id.", flush=True)
            else:
                print(f"Robot execution saga_id: {saga_id}", flush=True)
        
        # Validate required files exist
        env_var_file = project_path / 'robot' / 'variables' / 'env_vars.py'
        if not env_var_file.exists():
            raise FileNotFoundError(
                f"Required env_vars.py not found at: {env_var_file}\n"
                f"Project path: {project_path}"
            )
        if not test_file_path.exists():
            raise FileNotFoundError(f"Test file not found: {test_file_path}")
        if not robot_exe.exists():
            raise FileNotFoundError(f"Robot executable not found: {robot_exe}")
        
        results_dir.mkdir(parents=True, exist_ok=True)
        variable_file = _create_variable_file(message_data, results_dir)
        cmd = _build_robot_command(robot_exe, results_dir, test_file_path, variable_file, None, project_path)
        env = _build_robot_environment()
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
        assert process.stdout is not None
        return _monitor_robot_execution(process, timeout_seconds)
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


def _create_variable_file(message_data: Optional[Dict], results_dir: Path) -> Optional[Path]:
    """Create variable file from message data if provided."""
    if not message_data:
        return None
    variable_file = results_dir / "input_variables.json"
    with open(variable_file, 'w', encoding='utf-8') as f:
        json.dump(message_data, f, ensure_ascii=False, indent=2)
    return variable_file


def _build_robot_command(
    robot_exe: Path,
    results_dir: Path,
    test_file_path: Path,
    variable_file: Optional[Path],
    env_var_file: Optional[Path],
    project_path: Path
) -> list:
    """Build robot command arguments."""
    # Ensure all paths are absolute and resolved
    project_path = project_path.resolve()
    test_file_path = test_file_path.resolve()
    results_dir = results_dir.resolve()
    
    cmd = [str(robot_exe), "--outputdir", str(results_dir)]
    
    # Load environment variable file (env_vars.py) - REQUIRED, must be first
    env_var_file = (project_path / 'robot' / 'variables' / 'env_vars.py').resolve()
    if not env_var_file.exists():
        raise FileNotFoundError(
            f"Required env_vars.py not found at: {env_var_file}\n"
            f"Project path: {project_path} (exists: {project_path.exists()})"
        )
    # Use absolute path with forward slashes (Robot Framework compatible on all platforms)
    env_var_path = str(env_var_file).replace('\\', '/')
    cmd.extend(["--variablefile", env_var_path])
    
    # Then load message data variable file (saga context) if provided
    if variable_file:
        variable_file = variable_file.resolve()
        cmd.extend(["--variablefile", str(variable_file)])
    
    # Test file path - use relative to project_path since cwd is project_path
    try:
        test_file_relative = test_file_path.relative_to(project_path)
        cmd.append(str(test_file_relative).replace('\\', '/'))
    except ValueError:
        # If not relative, use absolute path
        cmd.append(str(test_file_path).replace('\\', '/'))
    
    return cmd


def _build_robot_environment() -> Dict[str, str]:
    """Build environment variables for robot execution."""
    env = os.environ.copy()
    env['PYTHONUNBUFFERED'] = '1'
    env['PYTHONIOENCODING'] = 'utf-8'
    return env


def _monitor_robot_execution(
    process: subprocess.Popen,
    timeout_seconds: int
) -> Tuple[bool, Optional[str]]:
    """Monitor robot execution with timeout and retry loop detection."""
    captured_output = []
    retry_loop_detected = False
    retry_count = 0
    last_retry_time = 0
    start_time = time.time()
    last_output_time = start_time
    
    while True:
        elapsed = time.time() - start_time
        if elapsed > timeout_seconds:
            error_msg = f"Robot execution timeout after {timeout_seconds // 60} minutes"
            print(f"ERROR: {error_msg}", file=sys.stderr)
            _terminate_process(process)
            return (False, error_msg)
        
        if process.poll() is not None:
            remaining = process.stdout.read()
            if remaining:
                for line in remaining.splitlines():
                    line_stripped = line.rstrip()
                    if line_stripped:
                        print(line_stripped)
                        sys.stdout.flush()
                        captured_output.append(line_stripped)
            break
        
        try:
            line = process.stdout.readline()
        except Exception:
            break
        
        if not line:
            current_time = time.time()
            if current_time - last_output_time > NO_OUTPUT_TIMEOUT_SECONDS:
                error_msg = f"Robot execution stalled (no output for {NO_OUTPUT_TIMEOUT_SECONDS // 60} minutes)"
                print(f"ERROR: {error_msg}", file=sys.stderr)
                _terminate_process(process)
                return (False, error_msg)
            time.sleep(0.5)
            continue
        
        last_output_time = time.time()
        line_stripped = line.rstrip()
        print(line_stripped)
        sys.stdout.flush()
        captured_output.append(line_stripped)
        
        if is_retry_loop_line(line_stripped):
            current_time = time.time()
            if current_time - last_retry_time < 10:
                retry_count += 1
            else:
                retry_count = 1
            last_retry_time = current_time
            
            if retry_count >= 2:
                retry_loop_detected = True
                error_msg = extract_retry_error_from_line(line_stripped)
                print(f"ERROR: Retry loop detected (count: {retry_count}) - {error_msg}", file=sys.stderr)
                _terminate_process(process)
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    pass
                return (False, error_msg)
    
    process.stdout.close()
    exit_code = process.wait()
    output_text = '\n'.join(captured_output)
    error_msg = extract_error_from_output_text(output_text)
    
    if exit_code != 0 or retry_loop_detected:
        return (False, error_msg or "Robot execution failed")
    return (True, None)


def _terminate_process(process: subprocess.Popen) -> None:
    """Terminate process gracefully, then force kill if needed."""
    try:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
    except Exception:
        pass

