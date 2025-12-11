"""Standalone DAG to extract PDF fields from rotated PNG images using GPT Vision.

This DAG processes PNG files already in the rotated folder without requiring saga data.
It uses the default fallback doc_transportes_list for file organization.
"""
import logging
import shutil
from datetime import datetime
from pathlib import Path

from airflow import DAG
from airflow.operators.python import PythonOperator

from operators.gpt_pdf_extractor_operator import GptPdfExtractorOperator

logger = logging.getLogger(__name__)

default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 0,
}

dag = DAG(
    dag_id="gpt_pdf_extractor_standalone",
    start_date=datetime(2024, 1, 1),
    schedule=None,  # Manual trigger only
    default_args=default_args,
    catchup=False,
    max_active_runs=1,
    is_paused_upon_creation=False,
    tags=["gpt", "pdf", "extraction", "standalone", "manual"],
    description="Standalone GPT PDF extraction from rotated PNG images",
)


def clean_processado_folder():
    """Clean the processado folder by removing all files and subdirectories."""
    processado_folder = Path("/opt/airflow/data/processado")
    
    if not processado_folder.exists():
        logger.info("Processado folder does not exist, skipping cleanup")
        return
    
    # Remove all files and subdirectories in processado folder
    items_removed = 0
    for item in processado_folder.iterdir():
        try:
            if item.is_file():
                item.unlink()
                items_removed += 1
                logger.debug("Removed file: %s", item.name)
            elif item.is_dir():
                # Remove directory and all its contents
                shutil.rmtree(item)
                items_removed += 1
                logger.debug("Removed directory: %s", item.name)
        except Exception as e:
            logger.warning("Failed to remove %s: %s", item.name, e)
    
    if items_removed > 0:
        logger.info("Cleaned processado folder: removed %d item(s)", items_removed)
    else:
        logger.info("Processado folder is already empty")


clean_processado_task = PythonOperator(
    task_id="clean_processado_folder",
    python_callable=clean_processado_folder,
    dag=dag,
)

# Extract PDF fields from rotated PNG images
# Reads from: /opt/airflow/data/processar/rotated (maps to shared/data/processar/rotated)
# Outputs to: /opt/airflow/data/processado (maps to shared/data/processado)
# Uses default fallback doc_transportes_list when saga is not available
gpt_extract_task = GptPdfExtractorOperator(
    task_id="extract_pdf_fields_from_rotated",
    folder_path="/opt/airflow/data/processar/rotated",
    output_dir="/opt/airflow/data/processado",
    rpa_api_conn_id="rpa_api",
    endpoint="/rpa/pdf/extract-gpt",
    timeout=300,
    dag=dag,
)

# Set task dependencies: clean first, then extract
clean_processado_task >> gpt_extract_task

