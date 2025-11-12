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


def validate_webhook_status_task(**context):
    """Validate webhook status and fail if status is not SUCCESS."""
    import sys
    import os
    import json
    from airflow.exceptions import AirflowException
    
    # Add libs to path
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'libs'))
    from webhook import get_webhook_data
    
    task_instance = context['task_instance']
    dag_run = context['dag_run']
    target_task_id = "upload_nf_files_to_s3"
    
    # Get webhook data
    webhook_data = get_webhook_data(task_instance=task_instance, target_task_id=target_task_id, dag_id=dag_run.dag_id, data_key="webhook_data")
    
    print(f"[validate_webhook_status] Retrieved webhook data: {type(webhook_data)}")
    
    if webhook_data is None:
        print("[validate_webhook_status] WARNING: Webhook data is None - skipping validation")
        return
    
    if not isinstance(webhook_data, dict):
        print(f"[validate_webhook_status] WARNING: Webhook data is not a dict: {type(webhook_data)} - skipping validation")
        return
    
    status = webhook_data.get("status")
    if status is None:
        print("[validate_webhook_status] WARNING: Webhook data missing 'status' field - skipping validation")
        return
    
    status_upper = str(status).upper()
    print(f"[validate_webhook_status] Validating status: {status_upper}")
    
    if status_upper != "SUCCESS":
        error_msg = (
            webhook_data.get("error_message") or
            (webhook_data.get("rpa_response", {}).get("error") if isinstance(webhook_data.get("rpa_response"), dict) else None) or
            f"RPA execution failed with status: {status_upper}"
        )
        print(f"[validate_webhook_status] FAILURE DETECTED - Status: {status_upper}, Error: {error_msg}")
        # Raise exception to fail the task
        raise AirflowException(f"Webhook response indicates failure. Status: {status_upper}. Error message: {error_msg}")
    
    print("[validate_webhook_status] Status is SUCCESS - validation passed")
    # Push data for downstream tasks
    context['ti'].xcom_push(key='webhook_data', value=webhook_data)


def upload_nf_files_to_s3_task(**context):
    """Upload NF files to S3."""
    # Get webhook data passed from validation task
    webhook_data = context['ti'].xcom_pull(key='webhook_data', default=None)
    
    # Placeholder for S3 upload logic
    # TODO: Implement actual S3 upload logic here
    print(f"Uploading NF files to S3 with webhook data: {webhook_data}")
    
    return {"status": "uploaded", "webhook_data": webhook_data}

