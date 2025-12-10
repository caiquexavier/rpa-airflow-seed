"""Standalone DAG to generate protocolo de devolução PDFs."""
import logging
from datetime import datetime

from airflow import DAG

from operators.protocolo_pdf_generator_operator import ProtocoloPdfGeneratorOperator

logger = logging.getLogger(__name__)

default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 0,
}

dag = DAG(
    dag_id="protocolo_devolucao_standalone",
    start_date=datetime(2024, 1, 1),
    schedule=None,  # Manual trigger only (schedule_interval deprecated in Airflow 2.4+)
    default_args=default_args,
    catchup=False,
    max_active_runs=1,
    is_paused_upon_creation=False,  # Make DAG active (not transparent) in Graph view
    tags=["rpa", "manual", "protocolo", "standalone"],
)

generate_protocolo_pdf_task = ProtocoloPdfGeneratorOperator(
    task_id="generate_protocolo_pdf",
    processado_dir="/opt/airflow/data/processado",  # Directory where doc_transportes folders are located
    rpa_api_conn_id="rpa_api",
    dag=dag,
)

