"""Message handler that triggers Robot Framework runs."""
from pathlib import Path
from typing import Dict
import subprocess


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


def handle_message(message: Dict, project_path: Path, robot_exe: Path, tests_path: Path, results_dir: Path) -> bool:
    rpa_id = message.get('rpa_id')
    if not rpa_id:
        print("Error: Message missing 'rpa_id' field")
        return False
    print(f"Processing RPA ID: {rpa_id}")
    return run_robot_tests(project_path, robot_exe, tests_path, results_dir)


