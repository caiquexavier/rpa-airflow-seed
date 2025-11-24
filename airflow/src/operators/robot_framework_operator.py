"""Custom operator for Robot Framework execution."""
from typing import Any, Dict, Optional

from airflow.exceptions import AirflowException
from airflow.hooks.base import BaseHook
from airflow.models import BaseOperator
from airflow.utils.context import Context

from libs.rpa_robot_executor import build_api_url, execute_robot_business_flow
from services.saga import get_saga_from_context, log_saga, build_saga_event, send_saga_event_to_api


class RobotFrameworkOperator(BaseOperator):
    """
    Operator for executing Robot Framework tasks via RPA API.
    
    Args:
        robot_test_file: Robot Framework test file name (e.g., "protocolo_devolucao_main.robot")
        rpa_api_conn_id: Connection ID for RPA API
        api_endpoint: API endpoint for robot execution
        callback_path: Optional callback path for webhook
        airflow_api_base_url_var: Airflow variable name for API base URL
        timeout: Request timeout in seconds
    """

    def __init__(
        self,
        robot_test_file: str,
        rpa_api_conn_id: str = "rpa_api",
        api_endpoint: str = "/api/v1/robot-operator-saga/start",
        callback_path: Optional[str] = None,
        airflow_api_base_url_var: str = "AIRFLOW_API_BASE_URL",
        timeout: int = 30,
        task_id: Optional[str] = None,
        **kwargs
    ):
        super().__init__(task_id=task_id, **kwargs)
        self.robot_test_file = robot_test_file
        self.rpa_api_conn_id = rpa_api_conn_id
        self.api_endpoint = api_endpoint
        self.callback_path = callback_path
        self.airflow_api_base_url_var = airflow_api_base_url_var
        self.timeout = timeout

    def execute(self, context: Context) -> Dict[str, Any]:
        """Create RobotOperatorSaga via rpa-api for robot execution."""
        saga = get_saga_from_context(context)
        
        if not saga or not saga.get("saga_id"):
            raise AirflowException("SAGA with saga_id not found in XCom from previous task")
        
        log_saga(saga, task_id=self.task_id)

        conn = BaseHook.get_connection(self.rpa_api_conn_id)
        api_url = build_api_url(conn.schema, conn.host, conn.port, self.api_endpoint)
        
        # Use robot_test_file (without .robot extension) as robot_operator_id, fallback to task_id
        robot_operator_id = self.robot_test_file.replace(".robot", "") if self.robot_test_file else self.task_id

        try:
            result = execute_robot_business_flow(
                saga=saga,
                api_url=api_url,
                callback_path=self.callback_path,
                robot_operator_id=robot_operator_id,
                robot_test_file=self.robot_test_file,
                timeout=self.timeout
            )
            
            # Update SAGA with robot execution started event
            if saga and saga.get("saga_id"):
                # Ensure events list exists
                if "events" not in saga:
                    saga["events"] = []
                
                # Build event for robot execution start
                event = build_saga_event(
                    event_type="TaskStarted",
                    event_data={
                        "step": "robot_execution",
                        "status": "STARTED",
                        "robot_test_file": self.robot_test_file,
                        "robot_operator_id": robot_operator_id,
                        "callback_path": self.callback_path
                    },
                    context=context,
                    task_id=self.task_id
                )
                saga["events"].append(event)
                
                # Send event to rpa-api
                send_saga_event_to_api(saga, event, rpa_api_conn_id=self.rpa_api_conn_id)
                
                # Update events_count
                saga["events_count"] = len(saga["events"])
                
                # Push updated SAGA back to XCom
                task_instance = context.get('task_instance')
                if task_instance:
                    task_instance.xcom_push(key="saga", value=saga)
                    task_instance.xcom_push(key="rpa_payload", value=saga)  # Backward compatibility
                
                log_saga(saga, task_id=self.task_id)
        except Exception as e:
            # Update SAGA with failure event
            if saga and saga.get("saga_id"):
                if "events" not in saga:
                    saga["events"] = []
                
                event = build_saga_event(
                    event_type="TaskFailed",
                    event_data={
                        "step": "robot_execution",
                        "status": "FAILED",
                        "error": str(e),
                        "robot_test_file": self.robot_test_file
                    },
                    context=context,
                    task_id=self.task_id
                )
                saga["events"].append(event)
                send_saga_event_to_api(saga, event, rpa_api_conn_id=self.rpa_api_conn_id)
                saga["events_count"] = len(saga["events"])
                saga["current_state"] = "FAILED"
                
                task_instance = context.get('task_instance')
                if task_instance:
                    task_instance.xcom_push(key="saga", value=saga)
                    task_instance.xcom_push(key="rpa_payload", value=saga)
            
            raise AirflowException(f"Failed to create RobotOperatorSaga: {e}") from e

        return result

