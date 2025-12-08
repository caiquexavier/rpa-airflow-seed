"""Robot Framework variable file that loads environment variables from root .env file."""
import os
from pathlib import Path
from dotenv import load_dotenv


def _get_required_env(key):
    """Get a required environment variable. Raises error if missing or empty."""
    value = os.getenv(key)
    if value is None:
        raise ValueError(f"Required environment variable '{key}' not found in .env file")
    value_str = str(value).strip()
    if not value_str:
        raise ValueError(f"Required environment variable '{key}' is empty in .env file")
    return value_str


# Load .env file from project root
# Path: robot/config/env_vars.py -> robot/config/ -> robot/ -> rpa-robots/ -> project_root
env_vars_file = Path(__file__).resolve()
project_root = env_vars_file.parent.parent.parent.parent
env_file = project_root / '.env'

if not env_file.exists():
    raise FileNotFoundError(
        f"Required .env file not found at: {env_file}\n"
        f"Project root: {project_root}\n"
        f"Generate .env file from AWS Secrets Manager first."
    )

# Load .env file - override=True ensures variables are loaded even if already set
load_dotenv(env_file, override=True)

# Load required environment variables - all must exist in .env file
BASE_URL = _get_required_env('BASE_URL')
USUARIO = _get_required_env('USUARIO')
SENHA = _get_required_env('SENHA')

# MultiCTE environment variables - load from .env if available
MULTICTE_USERNAME = os.getenv('MULTICTE_USERNAME', '')
MULTICTE_PASSWORD = os.getenv('MULTICTE_PASSWORD', '')
MULTICTE_EMISSOR_CODE = os.getenv('MULTICTE_EMISSOR_CODE', '')
MULTICTE_BASE_URL = os.getenv('MULTICTE_BASE_URL', '')
