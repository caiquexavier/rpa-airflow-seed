"""Environment variable utilities."""
import os
from typing import Optional


def get_required_env(name: str) -> str:
    """
    Get required environment variable or raise error.
    
    Args:
        name: Environment variable name
        
    Returns:
        Environment variable value
        
    Raises:
        RuntimeError: If environment variable is missing or empty
    """
    value = os.getenv(name)
    if value is None or value == "":
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def get_env(name: str, default: Optional[str] = None) -> Optional[str]:
    """
    Get environment variable with optional default.
    
    Args:
        name: Environment variable name
        default: Default value if not found
        
    Returns:
        Environment variable value or default
    """
    return os.getenv(name, default)

