"""DAG to convert XLSX to RPA request and POST to API."""
import logging
from datetime import datetime

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.task_group import TaskGroup

from operators.robot_framework_operator import RobotFrameworkOperator
from operators.pdf_functions_operator import PdfFunctionsOperator
from operators.saga_operator import SagaOperator
from operators.gpt_pdf_extractor_operator import GptPdfExtractorOperator
from services.webhook import WebhookSensor
from tasks.tasks_rpa_protocolo_devolucao import (
    convert_xls_to_json_task,
    extract_doc_transportes_list,
    prepare_saga_for_item,
)

logger = logging.getLogger(__name__)

# Feature flag to enable/disable GPT PDF extractor task
ENABLE_GPT_PDF_EXTRACTOR = False

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

extract_items_task = PythonOperator(
    task_id="extract_items",
    python_callable=extract_doc_transportes_list,
    dag=dag,
)

# Helper function for dynamic task mapping - uses map_index to get item from XCom
def prepare_saga_wrapper(**context):
    """Get item from upstream XCom using map_index and prepare saga."""
    ti = context["task_instance"]
    # Get items list from upstream task
    items = ti.xcom_pull(task_ids="extract_items", key="return_value")
    if not items:
        raise ValueError("Items list not found from extract_items task")
    
    # Get map_index to determine which item to process
    # map_index is set by Airflow when using expand()
    map_index = getattr(ti, "map_index", None)
    if map_index is None:
        # If map_index is not available, try to get from mapped_kwargs
        mapped_kwargs = getattr(ti, "mapped_kwargs", {})
        if isinstance(mapped_kwargs, dict) and "item" in mapped_kwargs:
            item = mapped_kwargs["item"]
        else:
            raise ValueError(f"map_index not found and item not in mapped_kwargs. Available: {list(mapped_kwargs.keys()) if isinstance(mapped_kwargs, dict) else 'N/A'}")
    else:
        # Use map_index to get the correct item from the list
        if map_index >= len(items):
            raise ValueError(f"map_index {map_index} is out of range for items list of length {len(items)}")
        item = items[map_index]
    
    return prepare_saga_for_item(item=item, **context)

# Dynamic TaskGroup for processing each item in doc_transportes_list
with TaskGroup(group_id="process_transportes", dag=dag) as process_transportes_tg:
    items = extract_items_task.output
    
    # Use expand with a simple structure - we'll get the item using map_index
    # Create a list of empty dicts - the length will be determined at runtime
    # We use a workaround: expand with the items list but access via map_index
    prepare_saga_task = PythonOperator.partial(
        task_id="prepare_saga",
        python_callable=prepare_saga_wrapper,
        dag=dag,
    ).expand(op_kwargs={"item": items})
    
    robotFramework_task = RobotFrameworkOperator(
        task_id="pod_download",
        robot_test_file="protocolo_devolucao_main.robot",
        rpa_api_conn_id="rpa_api",
        api_endpoint="/api/v1/robot-operator-saga/start",
        callback_path="/trigger/split_pdf_files",
        airflow_api_base_url_var="AIRFLOW_API_BASE_URL",
        timeout=30,
        dag=dag,
    )
    
    wait_for_webhook = WebhookSensor(
        task_id="wait_for_webhook",
        target_task_id="split_pdf_files",
        poke_interval=5,
        timeout=3600,
        mode='poke',
        dag=dag,
    )
    
    split_files_task = PdfFunctionsOperator(
        task_id="split_pdf_files",
        folder_path="/opt/airflow/downloads",
        output_dir="/opt/airflow/data/processar",
        functions=["split", "rotate"],
        overwrite=True,
        dag=dag,
    )
    
    prepare_saga_task >> robotFramework_task >> wait_for_webhook >> split_files_task

# GPT PDF Extractor task: extracts all fields using GPT (expects rotation already done)
# Uses default field_map from libs.pdf_field_map (30 predefined fields)
# To let GPT suggest all fields, set field_map={}
if ENABLE_GPT_PDF_EXTRACTOR:
    gpt_pdf_extractor_task = GptPdfExtractorOperator(
        task_id="extract_pdf_fields",
        folder_path="/opt/airflow/data/processar",
        output_dir="/opt/airflow/data/processado",
        rpa_api_conn_id="rpa_api",
        timeout=300,
        save_extracted_data=True,
        dag=dag,
    )

# Final task to mark SAGA as completed
complete_saga_task_op = SagaOperator(
    task_id="complete_saga",
    action="complete",
    dag=dag,
)

# Define task dependencies
if ENABLE_GPT_PDF_EXTRACTOR:
    (start_saga_task
     >> convert_task
     >> extract_items_task
     >> process_transportes_tg
     >> gpt_pdf_extractor_task
     >> complete_saga_task_op)
else:
    (start_saga_task
     >> convert_task
     >> extract_items_task
     >> process_transportes_tg
     >> complete_saga_task_op)

