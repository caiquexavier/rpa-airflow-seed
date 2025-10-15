#!/usr/bin/env python3
"""
RPA Listener - entrypoint using modular src structure
"""
import sys
from pathlib import Path
from dotenv import load_dotenv

# Ensure `src` is importable when running this file directly
CURRENT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(CURRENT_DIR))

from src.config.rabbitmq import load_rabbitmq_config  # noqa: E402
from src.services.consumer import RpaConsumer  # noqa: E402
from src.controllers.handler import handle_message  # noqa: E402


def get_robot_paths():
    repo_root = Path(__file__).resolve().parent.parent
    project_path = repo_root / 'rpa-robots'
    robot_exe = project_path / 'venv' / 'Scripts' / 'robot.exe'
    tests_path = project_path / 'tests'
    results_dir = project_path / 'results'
    return {
        'project_path': project_path,
        'robot_exe': robot_exe,
        'tests_path': tests_path,
        'results_dir': results_dir
    }


def main():
    load_dotenv()
    try:
        rabbitmq_config = load_rabbitmq_config()
        robot_config = get_robot_paths()

        # Validate robot paths
        if not robot_config['robot_exe'].exists():
            raise FileNotFoundError(f"Robot executable not found: {robot_config['robot_exe']}")
        if not robot_config['tests_path'].exists():
            raise FileNotFoundError(f"Tests directory not found: {robot_config['tests_path']}")

        consumer = RpaConsumer(rabbitmq_config)

        def _on_message(message: dict) -> bool:
            return handle_message(
                message,
                robot_config['project_path'],
                robot_config['robot_exe'],
                robot_config['tests_path'],
                robot_config['results_dir'],
            )

        consumer.start(_on_message)

    except KeyboardInterrupt:
        pass
    except Exception as exc:
        sys.stderr.write(f"Fatal error: {exc}\n")
        sys.exit(1)


if __name__ == '__main__':
    main()