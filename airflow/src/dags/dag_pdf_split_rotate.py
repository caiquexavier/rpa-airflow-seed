"""DAG to split PDF files and rotate each page to readable position."""
import logging
from datetime import datetime
from pathlib import Path

from airflow import DAG
from airflow.operators.python import PythonOperator

from operators.pdf_split_operator import PdfSplitOperator
from operators.pdf_rotate_operator import PdfRotateOperator

logger = logging.getLogger(__name__)

default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 0,
}

dag = DAG(
    dag_id="pdf_split_rotate",
    start_date=datetime(2024, 1, 1),
    schedule=None,
    default_args=default_args,
    catchup=False,
    max_active_runs=1,
    is_paused_upon_creation=False,
    tags=["pdf", "split", "rotate", "manual"],
)


def clean_processar_folder():
    """Clean the processar folder by removing all PNG files from split and rotated subdirectories."""
    processar_folder = Path("/opt/airflow/data/processar")
    
    if not processar_folder.exists():
        logger.info("Processar folder does not exist, skipping cleanup")
        return
    
    # Clean split subdirectory (PNG files)
    split_folder = processar_folder / "split"
    if split_folder.exists():
        png_files = list(split_folder.glob("*.png"))
        if png_files:
            logger.info("Cleaning split folder: removing %d PNG file(s)", len(png_files))
            for png_file in png_files:
                try:
                    png_file.unlink()
                    logger.debug("Removed file: %s", png_file.name)
                except Exception as e:
                    logger.warning("Failed to remove file %s: %s", png_file.name, e)
        else:
            logger.info("Split folder is already empty")
    else:
        logger.info("Split folder does not exist, skipping cleanup")
    
    # Clean rotated subdirectory (PNG files)
    rotated_folder = processar_folder / "rotated"
    if rotated_folder.exists():
        png_files = list(rotated_folder.glob("*.png"))
        if png_files:
            logger.info("Cleaning rotated folder: removing %d PNG file(s)", len(png_files))
            for png_file in png_files:
                try:
                    png_file.unlink()
                    logger.debug("Removed file: %s", png_file.name)
                except Exception as e:
                    logger.warning("Failed to remove file %s: %s", png_file.name, e)
        else:
            logger.info("Rotated folder is already empty")
    else:
        logger.info("Rotated folder does not exist, skipping cleanup")
    
    # Also clean any PNG files directly in processar folder (legacy cleanup)
    png_files = list(processar_folder.glob("*.png"))
    if png_files:
        logger.info("Cleaning processar root folder: removing %d PNG file(s)", len(png_files))
        for png_file in png_files:
            try:
                png_file.unlink()
                logger.debug("Removed file: %s", png_file.name)
            except Exception as e:
                logger.warning("Failed to remove file %s: %s", png_file.name, e)


clean_processar_task = PythonOperator(
    task_id="clean_processar_folder",
    python_callable=clean_processar_folder,
    dag=dag,
)

split_task = PdfSplitOperator(
    task_id="split_pdfs",
    folder_path="/opt/airflow/downloads",
    output_dir="/opt/airflow/data/processar",
    overwrite=True,
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

clean_processar_task >> split_task >> rotate_task

