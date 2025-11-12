# Utility functions for loading AWS secrets from Secrets Manager
import os
import json
import boto3
from botocore.exceptions import ClientError, BotoCoreError
from typing import Dict, Optional


def _check_aws_credentials() -> bool:
    # Check if AWS credentials are available for accessing Secrets Manager
    access_key = os.getenv("AWS_ACCESS_KEY_ID")
    secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    if access_key and secret_key:
        return True
    try:
        session = boto3.Session()
        return session.get_credentials() is not None
    except Exception:
        return False


def load_aws_secrets(secret_name: Optional[str] = None, region: Optional[str] = None) -> Dict[str, str]:
    # Load secrets from AWS Secrets Manager and return as dictionary
    secret_name = secret_name or os.getenv("AWS_SECRET_NAME", "dev/rpa-airflow")
    region = region or os.getenv("AWS_REGION", "eu-north-1")
    if not _check_aws_credentials():
        raise RuntimeError("AWS credentials not found or invalid")
    try:
        session = boto3.Session()
        client = session.client(service_name='secretsmanager', region_name=region)
        response = client.get_secret_value(SecretId=secret_name)
        secret_string = response.get('SecretString', '')
        if not secret_string:
            raise RuntimeError(f"Secret {secret_name} is empty")
        secrets = json.loads(secret_string)
        if not isinstance(secrets, dict):
            raise RuntimeError(f"Secret {secret_name} must be a JSON object")
        return {k: v for k, v in secrets.items() if v is not None and str(v).strip() != ""}
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        error_message = e.response.get('Error', {}).get('Message', str(e))
        raise RuntimeError(f"Failed to retrieve secret {secret_name}: {error_code} - {error_message}") from e
    except BotoCoreError as e:
        raise RuntimeError(f"AWS service error while retrieving secret {secret_name}: {str(e)}") from e
    except Exception as e:
        raise RuntimeError(f"Unexpected error while retrieving secret {secret_name}: {str(e)}") from e


def load_aws_secrets_to_environment(secret_name: Optional[str] = None, region: Optional[str] = None) -> Dict[str, str]:
    # Load secrets from AWS Secrets Manager and set them as environment variables
    secrets = load_aws_secrets(secret_name, region)
    for key, value in secrets.items():
        if key not in os.environ:
            os.environ[key] = str(value).strip()
    return secrets

