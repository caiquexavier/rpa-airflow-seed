"""
Minimal DAG to call POST /publish endpoint.
Requires Airflow HTTP Connection 'publish_api' with host:
- http://localhost:3000 (when Airflow runs on host)
- http://rpa-api:3000 (when both run in Docker Compose)
"""
from datetime import datetime
from airflow import DAG
from airflow.providers.http.operators.http import SimpleHttpOperator

default_args = {"owner": "airflow"}

dag = DAG(
    dag_id="call_publish_api",
    start_date=datetime(2024, 1, 1),
    schedule_interval=None,
    default_args=default_args,
    catchup=False,
)

publish_task = SimpleHttpOperator(
    task_id="publish_task",
    http_conn_id="publish_api",
    endpoint="publish/",
    method="POST",
    data='{"rpa-id": "job-001"}',
    headers={"Content-Type": "application/json"},
    dag=dag,
)
