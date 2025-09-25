from datetime import datetime
from airflow import DAG
from airflow.providers.microsoft.winrm.operators.winrm import WinRMOperator

default_args = {
    "owner": "airflow",
    "start_date": datetime(2024, 1, 1),
    "retries": 0,
}

dag = DAG(
    dag_id="robot_powershell_host_run",
    start_date=datetime(2024, 1, 1),
    schedule_interval=None,
    default_args=default_args,
    catchup=False,
    description="Run Robot Framework tests on Windows host via WinRM",
)

run_robot_tests = WinRMOperator(
    task_id="run_robot_tests",
    ssh_conn_id="winrm_localhost",
    command="powershell -NoProfile -ExecutionPolicy Bypass -Command \"Set-Location $env:ROBOT_PROJECT_DIR; .\\venv\\Scripts\\robot.exe -d results tests\"",
    dag=dag,
)


