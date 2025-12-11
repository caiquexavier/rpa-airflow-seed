"""Standalone DAG to categorize Protocolo Devolução results."""
import logging
from datetime import datetime

from airflow import DAG
from airflow.operators.python import PythonOperator

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
    dag_id="categorize_protocolo_devolucao",
    start_date=datetime(2024, 1, 1),
    schedule=None,  # Manual trigger only
    default_args=default_args,
    catchup=False,
    max_active_runs=1,
    is_paused_upon_creation=False,
    tags=["protocolo-devolucao", "categorization", "standalone"],
    description="Categorize Protocolo Devolução results by validating POD files",
)

categorize_task = PythonOperator(
    task_id="categorize_protocolo_devolucao",
    python_callable=categorize_protocolo_devolucao_task,
    dag=dag,
)

categorize_task

