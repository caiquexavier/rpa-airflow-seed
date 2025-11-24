"""OpenAI client infrastructure - provides reusable OpenAI client instance."""
import logging
from typing import Optional

from openai import OpenAI

from ...config.config import get_openai_api_key, get_openai_model_name

logger = logging.getLogger(__name__)

_client: Optional[OpenAI] = None


def get_openai_client() -> OpenAI:
    """
    Get or create OpenAI client instance (singleton pattern).

    Returns:
        Configured OpenAI client instance

    Raises:
        RuntimeError: If OpenAI API key is not configured
    """
    global _client
    if _client is None:
        api_key = get_openai_api_key()
        _client = OpenAI(api_key=api_key)
        logger.debug("Initialized OpenAI client")
    return _client


def get_openai_model() -> str:
    """
    Get the configured OpenAI model name.

    Returns:
        Model name string (default: gpt-4o-mini)
    """
    return get_openai_model_name()
