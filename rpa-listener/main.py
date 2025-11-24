#!/usr/bin/env python3
"""
RPA Listener - entrypoint using modular src structure
"""
import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

# Configure logging before imports
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Reduce pika logging to WARNING to reduce noise
logging.getLogger('pika').setLevel(logging.WARNING)

# Ensure `src` is importable when running this file directly
CURRENT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(CURRENT_DIR))

logger = logging.getLogger(__name__)

from src.core.config.rabbitmq import load_rabbitmq_config  # noqa: E402
from src.infrastructure.messaging.consumer import RpaConsumer  # noqa: E402
from src.application.message_processor import process_message  # noqa: E402
from src.infrastructure.secrets.aws_secrets import load_aws_secrets  # noqa: E402


def get_robot_paths():
    repo_root = Path(__file__).resolve().parent.parent
    project_path = repo_root / 'rpa-robots'
    robot_exe = project_path / 'venv' / 'Scripts' / 'robot.exe'
    tests_path = project_path / 'robot' / 'tests'
    results_dir = project_path / 'results'
    return {
        'project_path': project_path,
        'robot_exe': robot_exe,
        'tests_path': tests_path,
        'results_dir': results_dir
    }


def _load_required_runtime_secrets():
    """
    Ensure required settings are present, preferring `.env` but falling back to AWS.
    
    We first honor variables that may have been written by `load-aws-secrets.ps1`
    (or any other local workflow). Only when `RPA_API_BASE_URL` is absent do we
    hit AWS Secrets Manager, keeping local development friction low.
    """
    required_keys = ["RPA_API_BASE_URL"]
    missing_keys = [key for key in required_keys if not os.getenv(key)]
    if not missing_keys:
        return
    
    secrets = load_aws_secrets()
    still_missing = [key for key in missing_keys if not secrets.get(key)]
    if still_missing:
        raise RuntimeError(
            "Missing required keys in AWS Secrets Manager: "
            + ", ".join(still_missing)
        )
    for key in missing_keys:
        os.environ[key] = str(secrets[key]).strip()


def main():
    logger.info("Starting RPA Listener...")
    load_dotenv()
    _load_required_runtime_secrets()
    try:
        logger.info("Loading RabbitMQ configuration...")
        rabbitmq_config = load_rabbitmq_config()
        logger.info(f"RabbitMQ config loaded: host={rabbitmq_config.host}, queue={rabbitmq_config.queue}, user={rabbitmq_config.user}")
        
        logger.info("Loading robot paths...")
        robot_config = get_robot_paths()

        # Validate robot paths
        if not robot_config['robot_exe'].exists():
            raise FileNotFoundError(f"Robot executable not found: {robot_config['robot_exe']}")
        if not robot_config['tests_path'].exists():
            raise FileNotFoundError(f"Tests directory not found: {robot_config['tests_path']}")
        
        logger.info("Robot paths validated successfully")

        logger.info("Creating RpaConsumer instance...")
        consumer = RpaConsumer(rabbitmq_config)

        def _on_message(message: dict) -> bool:
            return process_message(
                message,
                robot_config['project_path'],
                robot_config['robot_exe'],
                robot_config['tests_path'],
                robot_config['results_dir'],
            )

        logger.info("Starting consumer...")
        consumer.start(_on_message)

    except KeyboardInterrupt:
        if 'consumer' in locals():
            try:
                consumer.close()
            except Exception:
                pass
    except Exception as exc:
        sys.stderr.write(f"{exc}\n")
        sys.exit(1)


if __name__ == '__main__':
    main()
