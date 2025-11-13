"""Task functions for rpa_protocolo_devolucao DAG."""
from airflow.models import Variable
from airflow.exceptions import AirflowException
import sys
import os
import json
import logging

# Add services to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'services'))
from converter import xls_to_rpa_request
try:
    from .saga_helper import log_saga, get_saga_rpa_key_id, get_saga_rpa_request
except ImportError:
    # Fallback if saga_helper not available
    def log_saga(saga, task_id=None):
        import json
        if saga:
            logger.info(f"[{task_id}] SAGA: {json.dumps(saga, indent=2, ensure_ascii=False)}")
    
    def get_saga_rpa_key_id(saga):
        return saga.get('rpa_key_id') if saga and isinstance(saga, dict) else None
    
    def get_saga_rpa_request(saga):
        return saga.get('rpa_request') if saga and isinstance(saga, dict) else None

logger = logging.getLogger(__name__)


def convert_xls_to_json_task(**context):
    """Convert XLSX file to RPA request payload and create SAGA."""
    # Get XLSX path from Airflow Variable
    xlsx_path = Variable.get("ECARGO_XLSX_PATH", default_var="")
    if not xlsx_path:
        raise AirflowException("ECARGO_XLSX_PATH Airflow Variable is required")
    
    # Validate path before attempting conversion
    from pathlib import Path
    src_path = Path(xlsx_path)
    
    # Log path information for debugging
    logger.info(f"Attempting to read XLSX file from: {xlsx_path}")
    logger.info(f"Absolute path: {src_path.resolve()}")
    
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
    
    # Convert XLSX to SAGA structure (includes first step event: convert_xls_to_json)
    saga = xls_to_rpa_request(xlsx_path)
    
    # Log SAGA as INFO
    logger.info(f"INFO SAGA (Task: read_input_xls): {json.dumps(saga, indent=2, ensure_ascii=False)}")
    
    # Push SAGA to XCom
    context["task_instance"].xcom_push(key="saga", value=saga)
    # Also push as rpa_payload for backward compatibility
    context["task_instance"].xcom_push(key="rpa_payload", value=saga)
    
    return saga


def upload_nf_files_to_s3_task(**context):
    """Upload NF files to S3."""
    # Get SAGA from previous tasks
    ti = context.get('task_instance')
    saga = None
    
    # Try to get SAGA from webhook_data first (most recent)
    webhook_data = ti.xcom_pull(key='webhook_data', default=None) if ti else None
    if webhook_data and isinstance(webhook_data, dict):
        saga = webhook_data.get('saga')
        if not saga and 'rpa_key_id' in webhook_data:
            # webhook_data itself might be SAGA-like
            saga = webhook_data
    
    # Fallback to XCom saga key
    if not saga and ti:
        saga = ti.xcom_pull(key='saga', default=None)
    
    # Log SAGA as INFO
    log_saga(saga, task_id="upload_nf_files_to_s3")
    
    # Get rpa_key_id and rpa_request from SAGA
    rpa_key_id = get_saga_rpa_key_id(saga)
    rpa_request = get_saga_rpa_request(saga)
    
    # Placeholder for S3 upload logic
    # TODO: Implement actual S3 upload logic here
    logger.info(f"Uploading NF files to S3 with SAGA: rpa_key_id={rpa_key_id}")
    
    return {"status": "uploaded", "saga": saga}

