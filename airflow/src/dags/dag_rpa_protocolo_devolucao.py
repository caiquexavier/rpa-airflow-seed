"""DAG to convert XLSX to RPA request and POST to API."""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.http.operators.http import HttpOperator
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'services'))
from webhook import WebhookSensor
from tasks.tasks_rpa_protocolo_devolucao import (
    convert_xls_to_json_task,
    upload_nf_files_to_s3_task,
)

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

post_task = HttpOperator(
    task_id="execute_signa_download_nf",
    http_conn_id="rpa_api",
    endpoint="/request_rpa_exec",
    method="POST",
    headers={"Content-Type": "application/json"},
    data="{{ ti.xcom_pull(task_ids='read_input_xls', key='rpa_payload') | tojson }}",
    response_check=lambda response: response.status_code == 202,
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

