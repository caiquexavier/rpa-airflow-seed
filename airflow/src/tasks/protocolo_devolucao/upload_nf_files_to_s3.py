"""Upload NF files to S3."""
import logging

from services.saga import (
    get_saga_rpa_key_id,
    get_saga_rpa_request,
    log_saga,
)

logger = logging.getLogger(__name__)


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

