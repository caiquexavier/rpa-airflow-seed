"""Utility functions for loading AWS secrets from Secrets Manager."""
import os
import json
import boto3
from botocore.exceptions import ClientError, BotoCoreError
from typing import Dict, Optional


def _check_aws_credentials() -> bool:
    """
    Check if AWS credentials are available for accessing Secrets Manager.
    
    Returns:
        True if credentials are available, False otherwise
    """
    # Check environment variables
    access_key = os.getenv("AWS_ACCESS_KEY_ID")
    secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    
    if access_key and secret_key:
        # Trim whitespace (common issue)
        access_key_trimmed = access_key.strip()
        secret_key_trimmed = secret_key.strip()
        
        # Validate format (basic checks)
        if len(access_key_trimmed) < 16:
            print("[AWS Secrets] WARNING: AWS_ACCESS_KEY_ID seems invalid (too short)")
            return False
        if len(secret_key_trimmed) < 20:
            print("[AWS Secrets] WARNING: AWS_SECRET_ACCESS_KEY seems invalid (too short)")
            return False
        
        # If there was whitespace, warn and suggest fixing
        if access_key != access_key_trimmed or secret_key != secret_key_trimmed:
            print("[AWS Secrets] WARNING: Credentials have whitespace - this can cause signature errors!")
            print("[AWS Secrets] Suggestion: Trim credentials with .Trim() in PowerShell")
        
        return True
    
    # Check if credentials are available via boto3 default chain
    try:
        session = boto3.Session()
        credentials = session.get_credentials()
        if credentials:
            return True
    except Exception:
        pass
    
    return False


def _test_aws_credentials(region: str = "eu-north-1") -> bool:
    """
    Test AWS credentials by making a simple STS call.
    This is faster/cheaper than trying Secrets Manager first.
    
    Returns:
        True if credentials work, False otherwise
    """
    try:
        session = boto3.Session()
        sts_client = session.client('sts', region_name=region)
        sts_client.get_caller_identity()
        return True
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        if error_code in ('InvalidSignatureException', 'SignatureDoesNotMatch'):
            print("[AWS Secrets] ERROR: AWS credentials are invalid (signature mismatch)")
            print("[AWS Secrets] This usually means:")
            print("[AWS Secrets]   1. Credentials are incorrect")
            print("[AWS Secrets]   2. Credentials have whitespace (use .Trim() in PowerShell)")
            print("[AWS Secrets]   3. Credentials are expired/rotated")
            print("[AWS Secrets]   4. System clock is out of sync")
        return False
    except Exception:
        return False


def load_aws_secrets(
    secret_name: Optional[str] = None,
    region: Optional[str] = None
) -> Dict[str, str]:
    """
    Load secrets from AWS Secrets Manager and return as dictionary.
    
    Args:
        secret_name: Name of the secret in AWS Secrets Manager.
                    Defaults to AWS_SECRET_NAME env var or "dev/rpa-airflow"
        region: AWS region where the secret is stored.
               Defaults to AWS_REGION env var or "eu-north-1"
    
    Returns:
        Dictionary of secret key-value pairs
    
    Raises:
        RuntimeError: If secret cannot be retrieved
    """
    # Get secret name and region from parameters or environment
    secret_name = secret_name or os.getenv("AWS_SECRET_NAME", "dev/rpa-airflow")
    region = region or os.getenv("AWS_REGION", "eu-north-1")
    
    print(f"[AWS Secrets] Loading secrets from: {secret_name} (region: {region})")
    
    # Check if AWS credentials are available before attempting to access Secrets Manager
    if not _check_aws_credentials():
        raise RuntimeError(
            "AWS credentials not found or invalid. "
            "To access Secrets Manager, you need to provide AWS credentials via:\n"
            "  1. Environment variables: AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY\n"
            "  2. AWS CLI configuration: Run 'aws configure'\n"
            "  3. IAM role (if running on EC2/ECS/Lambda)\n"
            "\n"
            "For local development, set:\n"
            "  $env:AWS_ACCESS_KEY_ID = 'your-access-key'\n"
            "  $env:AWS_SECRET_ACCESS_KEY = 'your-secret-key'\n"
            "  $env:AWS_DEFAULT_REGION = 'eu-north-1'\n"
            "\n"
            "IMPORTANT: Always trim whitespace:\n"
            "  $env:AWS_ACCESS_KEY_ID = $env:AWS_ACCESS_KEY_ID.Trim()\n"
            "  $env:AWS_SECRET_ACCESS_KEY = $env:AWS_SECRET_ACCESS_KEY.Trim()"
        )
    
    # Test credentials before attempting Secrets Manager (faster failure)
    print("[AWS Secrets] Testing AWS credentials...")
    if not _test_aws_credentials(region):
        raise RuntimeError(
            "AWS credentials are invalid or incorrect. "
            "The credentials cannot authenticate with AWS.\n"
            "\n"
            "Common causes:\n"
            "  1. Credentials are incorrect - verify in AWS IAM Console\n"
            "  2. Credentials have whitespace - use .Trim() in PowerShell\n"
            "  3. Credentials are expired/rotated - create new access key\n"
            "  4. System clock is out of sync - sync system time\n"
            "\n"
            "To fix:\n"
            "  - Get fresh credentials from AWS IAM Console\n"
            "  - Set: $env:AWS_ACCESS_KEY_ID = 'key'.Trim()\n"
            "  - Set: $env:AWS_SECRET_ACCESS_KEY = 'secret'.Trim()\n"
            "  - Test: aws sts get-caller-identity"
        )
    print("[AWS Secrets] Credentials validated successfully")
    
    try:
        # Create Secrets Manager client
        # Use default credentials (from environment, IAM role, or AWS CLI config)
        session = boto3.Session()
        client = session.client(
            service_name='secretsmanager',
            region_name=region
        )
        
        # Get secret value
        response = client.get_secret_value(SecretId=secret_name)
        
        # Parse secret string (can be JSON or plain text)
        secret_string = response.get('SecretString', '')
        if not secret_string:
            raise RuntimeError(f"Secret {secret_name} is empty")
        
        # Try to parse as JSON
        try:
            secrets = json.loads(secret_string)
        except json.JSONDecodeError:
            # If not JSON, treat as plain text
            raise RuntimeError(
                f"Secret {secret_name} is not in JSON format. "
                "Expected JSON object with key-value pairs."
            )
        
        # Ensure it's a dictionary
        if not isinstance(secrets, dict):
            raise RuntimeError(
                f"Secret {secret_name} must be a JSON object, got {type(secrets).__name__}"
            )
        
        # Filter out empty values
        filtered_secrets = {
            k: v for k, v in secrets.items()
            if v is not None and str(v).strip() != ""
        }
        
        print(f"[AWS Secrets] Loaded {len(filtered_secrets)} secrets from AWS Secrets Manager")
        
        # Log which AWS-related secrets were found (without values)
        aws_secrets = [
            k for k in filtered_secrets.keys()
            if k.startswith('AWS_')
        ]
        if aws_secrets:
            print(f"[AWS Secrets] Found AWS credentials: {', '.join(aws_secrets)}")
        
        return filtered_secrets
        
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        error_message = e.response.get('Error', {}).get('Message', str(e))
        
        if error_code == 'ResourceNotFoundException':
            raise RuntimeError(
                f"Secret {secret_name} not found in region {region}. "
                f"Check secret name and region."
            ) from e
        elif error_code == 'AccessDeniedException':
            raise RuntimeError(
                f"Access denied to secret {secret_name}. "
                f"Check IAM permissions for secretsmanager:GetSecretValue."
            ) from e
        elif error_code == 'InvalidSignatureException':
            # Provide detailed troubleshooting
            access_key = os.getenv("AWS_ACCESS_KEY_ID", "")
            secret_key = os.getenv("AWS_SECRET_ACCESS_KEY", "")
            
            error_msg = (
                f"Invalid AWS credentials signature when accessing Secrets Manager.\n"
                f"\n"
                f"DIAGNOSIS:\n"
            )
            
            if access_key:
                if access_key != access_key.strip():
                    error_msg += f"  ❌ AWS_ACCESS_KEY_ID has whitespace (length: {len(access_key)})\n"
                else:
                    error_msg += f"  ✓ AWS_ACCESS_KEY_ID length: {len(access_key)} (should be 20)\n"
            else:
                error_msg += f"  ❌ AWS_ACCESS_KEY_ID not set in environment\n"
            
            if secret_key:
                if secret_key != secret_key.strip():
                    error_msg += f"  ❌ AWS_SECRET_ACCESS_KEY has whitespace (length: {len(secret_key)})\n"
                else:
                    error_msg += f"  ✓ AWS_SECRET_ACCESS_KEY length: {len(secret_key)} (should be 40)\n"
            else:
                error_msg += f"  ❌ AWS_SECRET_ACCESS_KEY not set in environment\n"
            
            error_msg += (
                f"\n"
                f"SOLUTION:\n"
                f"  1. Verify credentials are correct in AWS IAM Console\n"
                f"  2. Remove whitespace: $env:AWS_ACCESS_KEY_ID = $env:AWS_ACCESS_KEY_ID.Trim()\n"
                f"  3. Test with: aws sts get-caller-identity\n"
                f"  4. If test fails, credentials are wrong - get new ones from AWS\n"
                f"  5. Check system time: Get-Date (must be synchronized)"
            )
            
            raise RuntimeError(error_msg) from e
        else:
            raise RuntimeError(
                f"Failed to retrieve secret {secret_name}: {error_code} - {error_message}"
            ) from e
    except BotoCoreError as e:
        raise RuntimeError(
            f"AWS service error while retrieving secret {secret_name}: {str(e)}"
        ) from e
    except Exception as e:
        raise RuntimeError(
            f"Unexpected error while retrieving secret {secret_name}: {str(e)}"
        ) from e


def load_aws_secrets_to_environment(
    secret_name: Optional[str] = None,
    region: Optional[str] = None
) -> Dict[str, str]:
    """
    Load secrets from AWS Secrets Manager and set them as environment variables.
    
    Args:
        secret_name: Name of the secret in AWS Secrets Manager
        region: AWS region where the secret is stored
    
    Returns:
        Dictionary of loaded secrets
    
    Note:
        This modifies os.environ. Existing environment variables are NOT overwritten
        unless the secret contains the same key.
    """
    secrets = load_aws_secrets(secret_name, region)
    
    # Set environment variables
    for key, value in secrets.items():
        # Only set if not already in environment (allow override)
        if key not in os.environ:
            # Strip whitespace from string values (common issue with secrets)
            str_value = str(value).strip()
            os.environ[key] = str_value
            print(f"[AWS Secrets] Set environment variable: {key}")
            
            # Validate AWS credentials format if applicable
            if key == "AWS_ACCESS_KEY_ID" and len(str_value) < 16:
                print(f"[AWS Secrets] WARNING: AWS_ACCESS_KEY_ID seems too short ({len(str_value)} chars)")
            elif key == "AWS_SECRET_ACCESS_KEY" and len(str_value) < 20:
                print(f"[AWS Secrets] WARNING: AWS_SECRET_ACCESS_KEY seems too short ({len(str_value)} chars)")
        else:
            print(f"[AWS Secrets] Skipped {key} (already set in environment)")
    
    return secrets

