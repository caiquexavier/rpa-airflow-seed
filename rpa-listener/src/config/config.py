"""Configuration module for rpa-listener."""
import os
import json
import boto3
from typing import Dict, Optional


def _get_required_env(name: str) -> str:
    """Get required environment variable or raise error."""
    value = os.getenv(name)
    if value is None or value == "":
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def load_aws_secrets_to_environment(
    secret_name: Optional[str] = None,
    region: Optional[str] = None
) -> Dict[str, str]:
    """Load secrets from AWS Secrets Manager and set as environment variables."""
    secret_name = secret_name or os.getenv("AWS_SECRET_NAME", "dev/rpa-airflow")
    region = region or os.getenv("AWS_REGION", "eu-north-1")
    
    try:
        # Create Secrets Manager client
        client = boto3.client('secretsmanager', region_name=region)
        # Get secret value
        response = client.get_secret_value(SecretId=secret_name)
        # Parse JSON secret
        secret_string = response.get('SecretString', '{}')
        if not secret_string:
            print(f"[Config] Warning: Secret {secret_name} is empty")
            return {}
        
        secrets = json.loads(secret_string)
        if not isinstance(secrets, dict):
            print(f"[Config] Warning: Secret {secret_name} is not a JSON object")
            return {}
        
        # Set environment variables (only if not already set)
        loaded_count = 0
        for key, value in secrets.items():
            if key not in os.environ:
                os.environ[key] = str(value).strip()
                loaded_count += 1
        
        print(f"[Config] Loaded {loaded_count} new environment variables from AWS Secrets Manager")
        
        # Verify critical AWS variables are present
        required_vars = ['AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'AWS_S3_BUCKET']
        missing = [var for var in required_vars if not os.getenv(var)]
        
        # Check for AWS_REGION or AWS_DEFAULT_REGION (at least one must be set)
        region = os.getenv('AWS_DEFAULT_REGION') or os.getenv('AWS_REGION')
        if not region:
            missing.append('AWS_REGION or AWS_DEFAULT_REGION')
            # Set a default region if not provided (for S3 operations)
            default_region = "eu-north-1"
            if 'AWS_DEFAULT_REGION' not in os.environ and 'AWS_REGION' not in os.environ:
                os.environ['AWS_DEFAULT_REGION'] = default_region
                print(f"[Config] Set default AWS_DEFAULT_REGION: {default_region}")
        
        if missing:
            print(f"[Config] Warning: Missing required AWS variables after loading secrets: {', '.join(missing)}")
        
        return secrets
    except Exception as e:
        # Log the error but don't fail completely - allow fallback to existing env vars
        print(f"[Config] Warning: Failed to load AWS secrets from Secrets Manager: {e}")
        print("[Config] Continuing with existing environment variables...")
        return {}

