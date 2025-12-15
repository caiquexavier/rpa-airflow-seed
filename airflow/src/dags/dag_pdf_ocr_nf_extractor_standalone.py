"""Standalone DAG to extract NF-E numbers from rotated PNG images using OCR.

This DAG processes PNG files already in the rotated folder without requiring saga data.
It uses ROI cropping and preprocessing for reliable NF-E extraction.
"""
import logging
import shutil
from datetime import datetime
from pathlib import Path

from airflow import DAG
from airflow.operators.python import PythonOperator

from operators.pdf_ocr_nf_extractor_operator import PdfOcrNfExtractorOperator

logger = logging.getLogger(__name__)

default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 0,
}

dag = DAG(
    dag_id="pdf_ocr_nf_extractor_standalone",
    start_date=datetime(2024, 1, 1),
    schedule=None,  # Manual trigger only
    default_args=default_args,
    catchup=False,
    max_active_runs=1,
    is_paused_upon_creation=False,
    tags=["ocr", "nf-e", "extraction", "standalone", "manual"],
    description="Standalone OCR NF-E extraction from rotated PNG images using ROI cropping",
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

# Extract NF-E numbers from rotated PNG images using OCR with ROI cropping
# Reads from: /opt/airflow/data/processar/rotated (maps to shared/data/processar/rotated)
# Outputs to: /opt/airflow/data/processado (maps to shared/data/processado)
# Uses ROI cropping (x_start=1200, x_end=1700, y_start=300, y_end=650) for reliable extraction
extract_nf_e_task = PdfOcrNfExtractorOperator(
    task_id="extract_nf_e_from_rotated",
    rotated_folder_path="/opt/airflow/data/processar/rotated",
    processado_folder_path="/opt/airflow/data/processado",
    overwrite=True,
    dag=dag,
)

# Set task dependencies: clean first, then extract
clean_processado_task >> extract_nf_e_task

