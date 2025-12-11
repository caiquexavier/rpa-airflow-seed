"""DAG to convert XLSX to RPA request and POST to API."""
import logging
from datetime import datetime

from airflow import DAG
from airflow.operators.python import PythonOperator

from operators.robot_framework_operator import RobotFrameworkOperator
from operators.pdf_split_operator import PdfSplitOperator
from operators.pdf_rotate_operator import PdfRotateOperator
from operators.saga_operator import SagaOperator
from operators.gpt_pdf_extractor_operator import GptPdfExtractorOperator
from operators.protocolo_pdf_generator_operator import ProtocoloPdfGeneratorOperator
from services.webhook import WebhookSensor
from tasks.protocolo_devolucao.convert_xls_to_json import (
    convert_xls_to_json_task,
)
from tasks.protocolo_devolucao.categorize_protocolo_devolucao import (
    categorize_protocolo_devolucao_task,
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

robot_protocolo_devolucao_task = RobotFrameworkOperator(
    task_id="robot_protocolo_devolucao",
    robot_test_file="protocolo_devolucao_main.robot",
    rpa_api_conn_id="rpa_api",
    api_endpoint="/api/v1/robot-operator-saga/start",
    callback_path="/trigger/split_pdf_files",
    airflow_api_base_url_var="AIRFLOW_API_BASE_URL",
    timeout=30,
    dag=dag,
)

# Sensor that waits for webhook and validates status
wait_for_protocolo_devolucao_webhook = WebhookSensor(
    task_id="wait_for_protocolo_devolucao_webhook",
    target_task_id="split_pdf_files",
    poke_interval=5,  # Check every 5 seconds
    timeout=3600,  # Wait up to 1 hour
    mode='poke',
    dag=dag,
)

# Split PDF files task that executes after webhook is validated
split_files_task = PdfSplitOperator(
    task_id="split_pdf_files",
    folder_path="/opt/airflow/downloads",
    output_dir="/opt/airflow/data/processar",
    overwrite=True,  # Always overwrite existing files
    include_single_page=True,
    subdirectory="split",  # Files will be saved to processar/split/
    dag=dag,
)

rotate_task = PdfRotateOperator(
    task_id="rotate_pdfs",
    folder_path="/opt/airflow/data/processar/split",  # Read from split subdirectory
    output_dir="/opt/airflow/data/processar",
    overwrite=True,
    subdirectory="rotated",  # Files will be saved to processar/rotated/
    dag=dag,
)

gpt_pdf_extractor_task = GptPdfExtractorOperator(
    task_id="extract_pdf_fields",
    folder_path="/opt/airflow/data/processar/rotated",  # Read from rotated subdirectory
    output_dir="/opt/airflow/data/processado",
    rpa_api_conn_id="rpa_api",
    timeout=300,
    dag=dag,
)

generate_protocolo_pdf_task = ProtocoloPdfGeneratorOperator(
    task_id="generate_protocolo_pdf",
    processado_dir="/opt/airflow/data/processado",  # Directory where doc_transportes folders are located
    rpa_api_conn_id="rpa_api",
    dag=dag,
)

categorize_task = PythonOperator(
    task_id="categorize_protocolo_devolucao",
    python_callable=categorize_protocolo_devolucao_task,
    dag=dag,
)

robot_upload_multi_cte_task = RobotFrameworkOperator(
    task_id="robot_upload_multi_cte",
    robot_test_file="upload-multi-cte.robot",
    rpa_api_conn_id="rpa_api",
    api_endpoint="/api/v1/robot-operator-saga/start",
    callback_path="/trigger/robot_download_multi_cte_reports",
    airflow_api_base_url_var="AIRFLOW_API_BASE_URL",
    timeout=30,
    dag=dag,
)

# Sensor that waits for webhook and validates status
wait_for_upload_multi_cte_webhook = WebhookSensor(
    task_id="wait_for_upload_multi_cte_webhook",
    target_task_id="robot_download_multi_cte_reports",
    poke_interval=5,  # Check every 5 seconds
    timeout=3600,  # Wait up to 1 hour
    mode='poke',
    dag=dag,
)

robot_download_multi_cte_reports_task = RobotFrameworkOperator(
    task_id="robot_download_multi_cte_reports",
    robot_test_file="download-multi-cte-reports.robot",
    rpa_api_conn_id="rpa_api",
    api_endpoint="/api/v1/robot-operator-saga/start",
    callback_path="/trigger/complete_saga",
    airflow_api_base_url_var="AIRFLOW_API_BASE_URL",
    timeout=30,
    dag=dag,
)

# Sensor that waits for webhook and validates status
wait_for_download_multi_cte_reports_webhook = WebhookSensor(
    task_id="wait_for_download_multi_cte_reports_webhook",
    target_task_id="complete_saga",
    poke_interval=5,  # Check every 5 seconds
    timeout=3600,  # Wait up to 1 hour
    mode='poke',
    dag=dag,
)

# Final task to mark SAGA as completed
complete_saga_task_op = SagaOperator(
    task_id="complete_saga",
    action="complete",
    dag=dag,
)

(start_saga_task
 >> convert_task
 >> robot_protocolo_devolucao_task
 >> wait_for_protocolo_devolucao_webhook
 >> split_files_task
 >> rotate_task
 >> gpt_pdf_extractor_task
 >> generate_protocolo_pdf_task
 >> categorize_task
 >> robot_upload_multi_cte_task
 >> wait_for_upload_multi_cte_webhook
 >> robot_download_multi_cte_reports_task
 >> wait_for_download_multi_cte_reports_webhook
 >> complete_saga_task_op)

