# SAGA Structure Builder

## Overview

The SAGA Structure Builder creates a complete SAGA structure upfront with all events mapped and in PENDING state. This includes:

- All DAG tasks (in execution order based on dependencies)
- All Robot Framework steps for RobotFrameworkOperator tasks
- Complete event structure from start to end

## Architecture

### Components

1. **DAG Parser** (`rpa-api/src/application/services/dag_parser.py`)
   - Parses DAG configuration to extract tasks and dependencies
   - Builds execution order using topological sort
   - Identifies RobotFrameworkOperator tasks

2. **Robot Framework Parser** (`rpa-api/src/application/services/robot_parser.py`)
   - Parses `.robot` files to extract test cases and keywords
   - Maps Robot Framework steps to DAG tasks
   - Supports finding Robot files by `rpa_key_id`

3. **SAGA Structure Builder** (`rpa-api/src/application/services/saga_structure_builder.py`)
   - Orchestrates DAG and Robot parsing
   - Builds complete event structure
   - Creates all events in PENDING state

## Usage

### From Airflow DAG

#### Option 1: Automatic DAG Config Extraction

```python
from airflow import DAG
from operators.start_saga_operator import StartSagaOperator
from services.dag_config_builder import build_dag_config_from_dag
from airflow.providers.http.operators.http import HttpOperator

dag = DAG(
    dag_id="rpa_protocolo_devolucao",
    # ... other DAG config
)

# Build tasks
start_saga_task = StartSagaOperator(
    task_id="start_saga",
    rpa_key_id="rpa_protocolo_devolucao",
    dag=dag,
)

robot_task = RobotFrameworkOperator(
    task_id="execute_signa_download_nf",
    robot_test_file="ecargo_pod_download.robot",
    rpa_key_id="rpa_protocolo_devolucao",
    dag=dag,
)

# Create saga via API with complete structure
create_saga_task = HttpOperator(
    task_id="create_saga_with_structure",
    method="POST",
    http_conn_id="rpa_api",
    endpoint="/api/v1/saga/create",
    data={
        "exec_id": "{{ dag_run.run_id }}",
        "rpa_key_id": "rpa_protocolo_devolucao",
        "data": {},
        "dag_config": build_dag_config_from_dag(dag)
    },
    dag=dag,
)

start_saga_task >> create_saga_task >> robot_task
```

#### Option 2: Manual DAG Config

```python
from services.dag_config_builder import build_dag_config_manual

dag_config = build_dag_config_manual(
    dag_id="rpa_protocolo_devolucao",
    tasks=[
        {
            "task_id": "start_saga",
            "task_type": "StartSagaOperator",
            "dependencies": []
        },
        {
            "task_id": "read_input_xls",
            "task_type": "PythonOperator",
            "dependencies": ["start_saga"]
        },
        {
            "task_id": "execute_signa_download_nf",
            "task_type": "RobotFrameworkOperator",
            "dependencies": ["read_input_xls"],
            "robot_test_file": "ecargo_pod_download.robot",
            "rpa_key_id": "rpa_protocolo_devolucao"
        }
    ]
)

# Use in API call
create_saga_task = HttpOperator(
    task_id="create_saga_with_structure",
    method="POST",
    http_conn_id="rpa_api",
    endpoint="/api/v1/saga/create",
    data={
        "exec_id": 123,
        "rpa_key_id": "rpa_protocolo_devolucao",
        "data": {},
        "dag_config": dag_config
    },
    dag=dag,
)
```

### API Request Format

```json
{
  "exec_id": 123,
  "rpa_key_id": "rpa_protocolo_devolucao",
  "data": {
    "doc_transportes_list": []
  },
  "dag_config": {
    "dag_id": "rpa_protocolo_devolucao",
    "tasks": [
      {
        "task_id": "start_saga",
        "task_type": "StartSagaOperator",
        "dependencies": []
      },
      {
        "task_id": "read_input_xls",
        "task_type": "PythonOperator",
        "dependencies": ["start_saga"]
      },
      {
        "task_id": "execute_signa_download_nf",
        "task_type": "RobotFrameworkOperator",
        "dependencies": ["read_input_xls"],
        "robot_test_file": "ecargo_pod_download.robot",
        "rpa_key_id": "rpa_protocolo_devolucao"
      }
    ]
  }
}
```

## Event Structure

Events are created in the following order:

1. **Task Start Events** - For each DAG task (in execution order)
   - Event type: `TaskPending`
   - `task_id`: DAG task ID
   - `task_type`: Operator type
   - `status`: "PENDING"

2. **Robot Framework Step Events** - For RobotFrameworkOperator tasks
   - Event type: `RobotStepPending`
   - `robot_step`: Robot Framework keyword/test case name
   - `task_id`: Associated DAG task ID

3. **Task Complete Events** - For each DAG task
   - Event type: `TaskPending`
   - `status`: "PENDING"
   - `step`: "task_complete"

4. **Saga Complete Event** - Final event
   - Event type: `SagaPending`
   - `status`: "PENDING"
   - `step`: "saga_complete"

## Robot Framework File Discovery

The system attempts to find Robot Framework test files in the following order:

1. If `robot_test_file` is provided in task config, use that path
2. If `rpa_key_id` is provided, try to find file matching:
   - `{rpa_key_id}.robot`
   - `{rpa_key_id}_test.robot`
   - `test_{rpa_key_id}.robot`
3. If no match found, use first `.robot` file found in `rpa-robots/tests/`

## Benefits

1. **Complete Structure Upfront**: All events are created at saga creation time
2. **Predictable State**: All events start in PENDING state
3. **Robot Framework Integration**: Automatically maps Robot steps to DAG tasks
4. **Dependency Awareness**: Respects DAG task dependencies for execution order
5. **Backward Compatible**: Still supports legacy `initial_events` mode

## Migration

To migrate from legacy mode:

1. Update `StartSagaOperator` or create a new task that calls the API with `dag_config`
2. Remove manual event creation
3. Events will be automatically created from DAG structure

## Example: Complete DAG with SAGA Structure

```python
from airflow import DAG
from operators.start_saga_operator import StartSagaOperator
from operators.robot_framework_operator import RobotFrameworkOperator
from airflow.providers.http.operators.http import HttpOperator
from services.dag_config_builder import build_dag_config_from_dag

dag = DAG(
    dag_id="rpa_protocolo_devolucao",
    start_date=datetime(2024, 1, 1),
    schedule_interval=None,
    catchup=False,
)

# Build all tasks first
start_saga_task = StartSagaOperator(
    task_id="start_saga",
    rpa_key_id="rpa_protocolo_devolucao",
    dag=dag,
)

convert_task = PythonOperator(
    task_id="read_input_xls",
    python_callable=convert_xls_to_json_task,
    dag=dag,
)

robot_task = RobotFrameworkOperator(
    task_id="execute_signa_download_nf",
    robot_test_file="ecargo_pod_download.robot",
    rpa_key_id="rpa_protocolo_devolucao",
    dag=dag,
)

# Create saga with complete structure
create_saga_task = HttpOperator(
    task_id="create_saga_with_structure",
    method="POST",
    http_conn_id="rpa_api",
    endpoint="/api/v1/saga/create",
    data={
        "exec_id": "{{ dag_run.run_id }}",
        "rpa_key_id": "rpa_protocolo_devolucao",
        "data": {},
        "dag_config": build_dag_config_from_dag(dag)
    },
    dag=dag,
)

# Set dependencies
start_saga_task >> create_saga_task >> convert_task >> robot_task
```

