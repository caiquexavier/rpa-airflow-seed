"""Configuration module for rpa-api."""
import os
from typing import Dict


def get_rabbitmq_config() -> Dict[str, str]:
    """Get RabbitMQ configuration from environment variables."""
    return {
        "RABBITMQ_HOST": os.getenv("RABBITMQ_HOST", "localhost"),
        "RABBITMQ_PORT": os.getenv("RABBITMQ_PORT", "5672"),
        "RABBITMQ_VHOST": os.getenv("RABBITMQ_VHOST", "/"),
        "RABBITMQ_USER": os.getenv("RABBITMQ_USER", ""),
        "RABBITMQ_PASSWORD": os.getenv("RABBITMQ_PASSWORD", ""),
        "RABBITMQ_EXCHANGE": os.getenv("RABBITMQ_EXCHANGE", ""),
        "RABBITMQ_ROUTING_KEY": os.getenv("RABBITMQ_ROUTING_KEY", "rpa_events"),
    }


def get_postgres_dsn() -> str:
    """Get Postgres DSN from environment variables."""
    host = os.getenv("RPA_DB_HOST", "postgres")
    port = os.getenv("RPA_DB_PORT", "5432")
    user = os.getenv("RPA_DB_USER", "airflow")
    password = os.getenv("RPA_DB_PASSWORD", "airflow")
    dbname = os.getenv("RPA_DB_NAME", "rpa_db")
    return f"postgresql://{user}:{password}@{host}:{port}/{dbname}"