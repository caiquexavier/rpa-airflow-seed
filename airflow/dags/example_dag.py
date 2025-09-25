from datetime import datetime
from airflow import DAG
from airflow.operators.empty import EmptyOperator

default_args = {"owner": "airflow"}

dag = DAG(
    dag_id="example_dag",
    start_date=datetime(2024, 1, 1),
    schedule_interval=None,
    default_args=default_args,
    catchup=False,
)

start = EmptyOperator(task_id="start", dag=dag)
end = EmptyOperator(task_id="end", dag=dag)
start >> end
