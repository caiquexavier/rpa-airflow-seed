"""Task functions for ecargo_pod_download DAG."""
from airflow.models import Variable
from airflow.exceptions import AirflowException
import sys
import os

# Add libs to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'libs'))
from converter import xls_to_rpa_request


def convert_xls_to_json_task(**context):
    """Convert XLSX file to RPA request payload."""
    # Get XLSX path from Airflow Variable
    xlsx_path = Variable.get("ECARGO_XLSX_PATH", default_var="")
    if not xlsx_path:
        raise AirflowException("ECARGO_XLSX_PATH Airflow Variable is required")
    
    # Validate path before attempting conversion
    from pathlib import Path
    src_path = Path(xlsx_path)
    
    # Log path information for debugging
    print(f"Attempting to read XLSX file from: {xlsx_path}")
    print(f"Absolute path: {src_path.resolve()}")
    
    # Check if file exists and provide helpful error if not
    if not src_path.exists():
        error_msg = f"XLSX file not found at path: {xlsx_path} (absolute: {src_path.resolve()})"
        # Check parent directory
        parent_dir = src_path.parent
        if parent_dir.exists():
            try:
                files = list(parent_dir.iterdir())
                error_msg += f"  Files in parent directory ({parent_dir}): {[f.name for f in files[:10]]}\n"
            except Exception as e:
                error_msg += f"  Could not list parent directory: {e}\n"
        else:
            error_msg += f"  Parent directory does not exist: {parent_dir}\n"
        
        raise AirflowException(error_msg)
    
    # Convert XLSX to RPA request payload
    payload = xls_to_rpa_request(xlsx_path)
    
    # Get Airflow API base URL from Variable
    api_base_url = Variable.get("AIRFLOW_API_BASE_URL")
    # Remove trailing slash if present
    api_base_url = api_base_url.rstrip('/')
    
    # Add callback_url field with webhook endpoint
    payload["callback_url"] = f"{api_base_url}/trigger/upload_nf_files_to_s3"
    
    # Push result to XCom
    context["task_instance"].xcom_push(key="rpa_payload", value=payload)
    
    return payload


def upload_nf_files_to_s3_task(**context):
    """Upload NF files to S3."""
    # Get webhook data passed from API trigger
    webhook_data = context['ti'].xcom_pull(key='webhook_data', default=None)
    
    # Placeholder for S3 upload logic
    # TODO: Implement actual S3 upload logic here
    print(f"Uploading NF files to S3 with webhook data: {webhook_data}")
    
    return {"status": "uploaded", "webhook_data": webhook_data}

