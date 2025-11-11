"""DAG to convert XLSX to RPA request and POST to API."""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.models import Variable
from airflow.operators.python import PythonOperator
from airflow.providers.http.operators.http import HttpOperator
from airflow.exceptions import AirflowException
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'libs'))
from converter import xls_to_rpa_request

default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 0,
}

dag = DAG(
    dag_id="ecargo_pod_download",
    start_date=datetime(2024, 1, 1),
    schedule_interval=None,  # Manual trigger only
    default_args=default_args,
    catchup=False,
    max_active_runs=1,
    tags=["ecargo", "rpa", "manual"],
)

def convert_xls_to_json_task(**context):
    """Convert XLSX file to RPA request payload."""
    # Get XLSX path from Airflow Variable
    xlsx_path = Variable.get("ECARGO_XLSX_PATH", default_var="")
    if not xlsx_path:
        raise AirflowException("ECARGO_XLSX_PATH Airflow Variable is required")
    
    # Convert XLSX to RPA request payload
    payload = xls_to_rpa_request(xlsx_path)
    
    # Push result to XCom
    context["task_instance"].xcom_push(key="rpa_payload", value=payload)
    
    return payload

convert_task = PythonOperator(
    task_id="convert_xls_to_json",
    python_callable=convert_xls_to_json_task,
    dag=dag,
)

post_task = HttpOperator(
    task_id="post_to_rpa_api",
    http_conn_id="rpa_api",
    endpoint="/request_rpa_exec",
    method="POST",
    headers={"Content-Type": "application/json"},
    data="{{ ti.xcom_pull(task_ids='convert_xls_to_json', key='rpa_payload') | tojson }}",
    response_check=lambda response: response.status_code == 202,
    dag=dag,
)

# Define task dependencies
convert_task >> post_task
