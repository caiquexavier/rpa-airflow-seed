# Configuration module for rpa-listener
import os
import json
import boto3
from typing import Dict, Optional


def _get_required_env(name: str) -> str:
    # Get required environment variable or raise error
    value = os.getenv(name)
    if value is None or value == "":
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def load_aws_secrets_to_environment(secret_name: Optional[str] = None, region: Optional[str] = None) -> Dict[str, str]:
    # Load secrets from AWS Secrets Manager and set as environment variables
    secret_name = secret_name or os.getenv("AWS_SECRET_NAME", "dev/rpa-airflow")
    region = region or os.getenv("AWS_REGION", "eu-north-1")
    try:
        client = boto3.client('secretsmanager', region_name=region)
        response = client.get_secret_value(SecretId=secret_name)
        secret_string = response.get('SecretString', '{}')
        if not secret_string:
            return {}
        secrets = json.loads(secret_string)
        if not isinstance(secrets, dict):
            return {}
        for key, value in secrets.items():
            if key not in os.environ:
                os.environ[key] = str(value).strip()
        region = os.getenv('AWS_DEFAULT_REGION') or os.getenv('AWS_REGION')
        if not region:
            os.environ['AWS_DEFAULT_REGION'] = "eu-north-1"
        return secrets
    except Exception:
        return {}

