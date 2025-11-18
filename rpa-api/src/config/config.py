"""Configuration module for rpa-api."""
import os
from typing import Dict


def _get_required_env(name: str) -> str:
    """Get required environment variable or raise error."""
    value = os.getenv(name)
    if value is None or value == "":
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def get_rabbitmq_config() -> Dict[str, str]:
    """Get RabbitMQ configuration from environment variables."""
    return {
        "RABBITMQ_HOST": _get_required_env("RABBITMQ_HOST"),
        "RABBITMQ_PORT": _get_required_env("RABBITMQ_PORT"),
        "RABBITMQ_VHOST": _get_required_env("RABBITMQ_VHOST"),
        "RABBITMQ_USER": _get_required_env("RABBITMQ_USER"),
        "RABBITMQ_PASSWORD": _get_required_env("RABBITMQ_PASSWORD"),
        "RABBITMQ_EXCHANGE": os.getenv("RABBITMQ_EXCHANGE", ""),
        "RABBITMQ_ROUTING_KEY": _get_required_env("RABBITMQ_ROBOT_OPERATOR_QUEUE"),
    }


def get_postgres_dsn() -> str:
    """Get Postgres DSN from environment variables."""
    host = _get_required_env("RPA_DB_HOST")
    port = _get_required_env("RPA_DB_PORT")
    user = _get_required_env("RPA_DB_USER")
    password = _get_required_env("RPA_DB_PASSWORD")
    dbname = _get_required_env("RPA_DB_NAME")
    return f"postgresql://{user}:{password}@{host}:{port}/{dbname}"


def get_openai_api_key() -> str:
    """Get OpenAI API key from environment variables."""
    return _get_required_env("OPENAI_API_KEY")


def get_openai_model_name() -> str:
    """Get OpenAI model name from environment variables, with safe default."""
    return os.getenv("OPENAI_MODEL_NAME", "gpt-4o-mini")