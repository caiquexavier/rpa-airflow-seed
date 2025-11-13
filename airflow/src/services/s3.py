"""AWS S3 integration service."""
import os
import json
import logging
from pathlib import Path
from typing import Optional, Dict, List
import boto3
from botocore.exceptions import ClientError, BotoCoreError

logger = logging.getLogger(__name__)


def _check_aws_credentials() -> bool:
    """Check if AWS credentials are available."""
    access_key = os.getenv("AWS_ACCESS_KEY_ID")
    secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    if access_key and secret_key:
        return True
    try:
        session = boto3.Session()
        return session.get_credentials() is not None
    except Exception:
        return False


def _load_aws_secrets(secret_name: Optional[str] = None, region: Optional[str] = None) -> Dict[str, str]:
    """Load secrets from AWS Secrets Manager and return as dictionary."""
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


def _get_s3_client(secret_name: Optional[str] = None, region: Optional[str] = None):
    """Get S3 client with credentials from AWS Secrets Manager."""
    secrets = _load_aws_secrets(secret_name, region)
    
    access_key = secrets.get("AWS_ACCESS_KEY_ID")
    secret_key = secrets.get("AWS_SECRET_ACCESS_KEY")
    aws_region = secrets.get("AWS_DEFAULT_REGION") or secrets.get("AWS_REGION") or os.getenv("AWS_REGION", "eu-north-1")
    
    if not access_key or not secret_key:
        raise RuntimeError("AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY must be in AWS Secrets Manager")
    
    return boto3.client(
        's3',
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=aws_region
    )


def _get_bucket_name(secret_name: Optional[str] = None, region: Optional[str] = None) -> str:
    """Get S3 bucket name from AWS Secrets Manager."""
    secrets = _load_aws_secrets(secret_name, region)
    bucket_name = secrets.get("AWS_S3_BUCKET")
    if not bucket_name:
        raise RuntimeError("AWS_S3_BUCKET must be in AWS Secrets Manager")
    return bucket_name


def upload_file(local_path: str, s3_key: str, bucket_name: Optional[str] = None, secret_name: Optional[str] = None, region: Optional[str] = None) -> str:
    """Upload a file to S3."""
    local_file = Path(local_path)
    if not local_file.exists():
        raise FileNotFoundError(f"Local file not found: {local_path}")
    
    if not bucket_name:
        bucket_name = _get_bucket_name(secret_name, region)
    
    s3_client = _get_s3_client(secret_name, region)
    
    try:
        s3_client.upload_file(str(local_file), bucket_name, s3_key)
        logger.info(f"Uploaded {local_path} to s3://{bucket_name}/{s3_key}")
        return f"s3://{bucket_name}/{s3_key}"
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        error_message = e.response.get('Error', {}).get('Message', str(e))
        raise RuntimeError(f"Failed to upload file to S3: {error_code} - {error_message}") from e
    except Exception as e:
        raise RuntimeError(f"Unexpected error uploading file to S3: {str(e)}") from e


def upload_folder(local_folder_path: str, s3_prefix: str = "", bucket_name: Optional[str] = None, secret_name: Optional[str] = None, region: Optional[str] = None) -> List[str]:
    """Upload a folder and all its files to S3, maintaining folder structure."""
    local_folder = Path(local_folder_path)
    if not local_folder.exists():
        raise FileNotFoundError(f"Local folder not found: {local_folder_path}")
    if not local_folder.is_dir():
        raise ValueError(f"Path is not a directory: {local_folder_path}")
    
    if not bucket_name:
        bucket_name = _get_bucket_name(secret_name, region)
    
    s3_client = _get_s3_client(secret_name, region)
    
    uploaded_files = []
    
    try:
        # Normalize S3 prefix (remove leading/trailing slashes, add trailing if not empty)
        s3_prefix = s3_prefix.strip().strip('/')
        if s3_prefix and not s3_prefix.endswith('/'):
            s3_prefix += '/'
        
        # Walk through all files in the folder
        for file_path in local_folder.rglob('*'):
            if file_path.is_file():
                # Get relative path from the folder root
                relative_path = file_path.relative_to(local_folder)
                # Convert to S3 key (use forward slashes)
                s3_key = (s3_prefix + str(relative_path).replace('\\', '/')).strip('/')
                
                # Upload file
                s3_client.upload_file(str(file_path), bucket_name, s3_key)
                s3_path = f"s3://{bucket_name}/{s3_key}"
                uploaded_files.append(s3_path)
                logger.info(f"Uploaded {file_path} to {s3_path}")
        
        if not uploaded_files:
            logger.warning(f"No files found in folder: {local_folder_path}")
        
        logger.info(f"Uploaded {len(uploaded_files)} files from {local_folder_path} to s3://{bucket_name}/{s3_prefix}")
        return uploaded_files
        
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        error_message = e.response.get('Error', {}).get('Message', str(e))
        raise RuntimeError(f"Failed to upload folder to S3: {error_code} - {error_message}") from e
    except Exception as e:
        raise RuntimeError(f"Unexpected error uploading folder to S3: {str(e)}") from e


def download_file(s3_key: str, local_path: str, bucket_name: Optional[str] = None, secret_name: Optional[str] = None, region: Optional[str] = None) -> str:
    """Download a file from S3."""
    local_file = Path(local_path)
    local_file.parent.mkdir(parents=True, exist_ok=True)
    
    if not bucket_name:
        bucket_name = _get_bucket_name(secret_name, region)
    
    s3_client = _get_s3_client(secret_name, region)
    
    try:
        s3_client.download_file(bucket_name, s3_key, str(local_file))
        logger.info(f"Downloaded s3://{bucket_name}/{s3_key} to {local_path}")
        return str(local_file.resolve())
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        if error_code == 'NoSuchKey':
            raise FileNotFoundError(f"S3 object not found: s3://{bucket_name}/{s3_key}") from e
        error_message = e.response.get('Error', {}).get('Message', str(e))
        raise RuntimeError(f"Failed to download file from S3: {error_code} - {error_message}") from e
    except Exception as e:
        raise RuntimeError(f"Unexpected error downloading file from S3: {str(e)}") from e


def list_files(prefix: str = "", bucket_name: Optional[str] = None, secret_name: Optional[str] = None, region: Optional[str] = None) -> List[str]:
    """List files in S3 bucket with optional prefix."""
    if not bucket_name:
        bucket_name = _get_bucket_name(secret_name, region)
    
    s3_client = _get_s3_client(secret_name, region)
    
    try:
        response = s3_client.list_objects_v2(Bucket=bucket_name, Prefix=prefix)
        if 'Contents' not in response:
            return []
        return [obj['Key'] for obj in response['Contents']]
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        error_message = e.response.get('Error', {}).get('Message', str(e))
        raise RuntimeError(f"Failed to list files in S3: {error_code} - {error_message}") from e
    except Exception as e:
        raise RuntimeError(f"Unexpected error listing files in S3: {str(e)}") from e

