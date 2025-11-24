"""Robot Framework variable file that reads from AWS Secrets Manager.

This file loads BASE_URL, USUARIO, and SENHA from AWS Secrets Manager.
The secrets are loaded from the secret name specified in AWS_SECRET_NAME
environment variable (default: 'dev/rpa-airflow').

Single source of truth: All values must be in AWS Secrets Manager.
No fallbacks to environment variables.
"""
import sys
import os
from pathlib import Path

# Add rpa-listener to path so we can import the AWS secrets module
# The listener is in the parent directory of rpa-robots
# Path calculation: robot/config/env_vars.py -> robot/config/ -> robot/ -> rpa-robots/ -> project_root
env_vars_file = Path(__file__).resolve()
project_root = env_vars_file.parent.parent.parent.parent
listener_src = project_root / 'rpa-listener' / 'src'

if not listener_src.exists():
    raise ImportError(
        f"rpa-listener/src not found at {listener_src}. "
        f"Current file: {env_vars_file}, Project root: {project_root}"
    )

if str(listener_src) not in sys.path:
    sys.path.insert(0, str(listener_src))

try:
    from infrastructure.secrets.aws_secrets import load_aws_secrets
except ImportError as e:
    raise ImportError(
        f"Failed to import AWS secrets module: {e}. "
        f"Listener src path: {listener_src}, sys.path: {sys.path[:3]}"
    ) from e

# Load secrets from AWS Secrets Manager - single source of truth
try:
    secrets = load_aws_secrets()
    BASE_URL = str(secrets.get('BASE_URL', '')).strip()
    USUARIO = str(secrets.get('USUARIO', '')).strip()
    SENHA = str(secrets.get('SENHA', '')).strip()
except Exception as e:
    error_msg = (
        f"Failed to load secrets from AWS Secrets Manager: {e}. "
        f"Secret name: {os.getenv('AWS_SECRET_NAME', 'dev/rpa-airflow')}, "
        f"Region: {os.getenv('AWS_REGION', 'eu-north-1')}. "
        "Ensure BASE_URL, USUARIO, and SENHA are set in AWS Secrets Manager."
    )
    raise RuntimeError(error_msg) from e

# Validate required variables
if not BASE_URL:
    raise ValueError(
        f"BASE_URL is empty in AWS Secrets Manager. "
        f"Secret name: {os.getenv('AWS_SECRET_NAME', 'dev/rpa-airflow')}. "
        "Ensure BASE_URL is set in the secret."
    )
if not USUARIO:
    raise ValueError(
        f"USUARIO is empty in AWS Secrets Manager. "
        f"Secret name: {os.getenv('AWS_SECRET_NAME', 'dev/rpa-airflow')}. "
        "Ensure USUARIO is set in the secret."
    )
if not SENHA:
    raise ValueError(
        f"SENHA is empty in AWS Secrets Manager. "
        f"Secret name: {os.getenv('AWS_SECRET_NAME', 'dev/rpa-airflow')}. "
        "Ensure SENHA is set in the secret."
    )

