"""DAG to convert XLSX to RPA request and POST to API."""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.http.operators.http import HttpOperator
import sys
import os
import json
import logging

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'services'))
from webhook import WebhookSensor
from tasks.tasks_rpa_protocolo_devolucao import (
    convert_xls_to_json_task,
    upload_nf_files_to_s3_task,
)

logger = logging.getLogger(__name__)

default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 0,
}

dag = DAG(
    dag_id="rpa_protocolo_devolucao",
    start_date=datetime(2024, 1, 1),
    schedule_interval=None,  # Manual trigger only
    default_args=default_args,
    catchup=False,
    max_active_runs=1,
    tags=["rpa", "manual"],
)

convert_task = PythonOperator(
    task_id="read_input_xls",
    python_callable=convert_xls_to_json_task,
    dag=dag,
)


def post_to_api_with_saga_logging(**context):
    """Post to API and log SAGA in Airflow logs."""
    import requests
    from airflow.models import Variable
    from tasks.saga_helper import get_saga_from_context, log_saga
    
    # Get SAGA and log it
    saga = get_saga_from_context(context)
    log_saga(saga, task_id="execute_signa_download_nf")
    
    if not saga:
        raise ValueError("SAGA object is required from previous task")
    
    # Get Airflow API base URL for callback
    from airflow.models import Variable
    api_base_url = Variable.get("AIRFLOW_API_BASE_URL", default_var="")
    api_base_url = api_base_url.rstrip('/')
    callback_url = f"{api_base_url}/trigger/upload_nf_files_to_s3" if api_base_url else None
    
    # Build API payload with SAGA (API now expects saga object)
    api_payload = {
        "saga": saga,
        "callback_url": callback_url
    }
    
    # Get API connection details
    from airflow.hooks.base import BaseHook
    conn = BaseHook.get_connection("rpa_api")
    api_url = f"{conn.schema or 'http'}://{conn.host}:{conn.port or 3000}/request_rpa_exec"
    
    # Make HTTP request
    response = requests.post(
        api_url,
        json=api_payload,
        headers={"Content-Type": "application/json"},
        timeout=30
    )
    
    if response.status_code != 202:
        raise Exception(f"API request failed with status {response.status_code}: {response.text}")
    
    # Log response and updated SAGA
    response_data = response.json()
    logger.info(f"API response: {response.status_code} - {response_data}")
    
    # Update SAGA in XCom with the one returned from API
    if "saga" in response_data:
        context['ti'].xcom_push(key='saga', value=response_data["saga"])
        log_saga(response_data["saga"], task_id="execute_signa_download_nf_after_api")
    
    return response_data


post_task = PythonOperator(
    task_id="execute_signa_download_nf",
    python_callable=post_to_api_with_saga_logging,
    dag=dag,
)

# Sensor that waits for webhook and validates status
wait_for_webhook = WebhookSensor(
    task_id="wait_for_webhook",
    target_task_id="upload_nf_files_to_s3",
    poke_interval=5,  # Check every 5 seconds
    timeout=3600,  # Wait up to 1 hour
    mode='poke',
    dag=dag,
)

# Upload task that executes after webhook is validated
upload_task = PythonOperator(
    task_id="upload_nf_files_to_s3",
    python_callable=upload_nf_files_to_s3_task,
    dag=dag,
)

# Define task dependencies
convert_task >> post_task >> wait_for_webhook >> upload_task

