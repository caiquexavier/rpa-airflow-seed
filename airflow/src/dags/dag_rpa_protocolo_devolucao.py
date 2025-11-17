"""DAG to convert XLSX to RPA request and POST to API."""
import logging
from datetime import datetime

from airflow import DAG
from airflow.operators.python import PythonOperator

from operators.robot_framework_operator import RobotFrameworkOperator
from operators.split_files_operator import SplitFilesOperator
from operators.saga_operator import SagaOperator
from operators.ocr_operator import OcrOperator
from services.webhook import WebhookSensor
from tasks.tasks_rpa_protocolo_devolucao import (
    convert_xls_to_json_task,
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
    schedule=None,  # Manual trigger only (schedule_interval deprecated in Airflow 2.4+)
    default_args=default_args,
    catchup=False,
    max_active_runs=1,
    is_paused_upon_creation=False,  # Make DAG active (not transparent) in Graph view
    tags=["rpa", "manual"],
)

start_saga_task = SagaOperator(
    task_id="start_saga",
    action="start",
    rpa_key_id="rpa_protocolo_devolucao",
    dag=dag,
)

convert_task = PythonOperator(
    task_id="read_input_xls",
    python_callable=convert_xls_to_json_task,
    dag=dag,
)

robotFramework_task = RobotFrameworkOperator(
    task_id="pod_download",
    robot_test_file="ecargo_pod_download.robot",
    rpa_api_conn_id="rpa_api",
    api_endpoint="/api/v1/robot-operator-saga/start",
    callback_path="/trigger/split_pdf_files",
    airflow_api_base_url_var="AIRFLOW_API_BASE_URL",
    timeout=30,
    dag=dag,
)

# Sensor that waits for webhook and validates status
wait_for_webhook = WebhookSensor(
    task_id="wait_for_webhook",
    target_task_id="split_pdf_files",
    poke_interval=5,  # Check every 5 seconds
    timeout=3600,  # Wait up to 1 hour
    mode='poke',
    dag=dag,
)

# Split PDF files task that executes after webhook is validated
split_files_task = SplitFilesOperator(
    task_id="split_pdf_files",
    folder_path="/opt/airflow/downloads",
    output_dir="/opt/airflow/data/processar",
    overwrite=True,  # Always overwrite existing files
    dag=dag,
)

# OCR PDF files task that processes split PDFs
ocr_task = OcrOperator(
    task_id="ocr_pdf_files",
    folder_path="/opt/airflow/data/processar",
    fields=None,  # None means extract only NF-E number
    rpa_api_conn_id="rpa_api",
    timeout=300,  # 5 minutes timeout per file
    dag=dag,
)

# Final task to mark SAGA as completed
complete_saga_task_op = SagaOperator(
    task_id="complete_saga",
    action="complete",
    dag=dag,
)

# Define task dependencies
start_saga_task >> convert_task >> robotFramework_task >> wait_for_webhook >> split_files_task >> ocr_task >> complete_saga_task_op

