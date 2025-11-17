"""Custom operator for Robot Framework execution."""
from typing import Any, Dict, Optional

from airflow.exceptions import AirflowException
from airflow.hooks.base import BaseHook
from airflow.models import BaseOperator, Variable
from airflow.utils.context import Context

from libs.rpa_robot_executor import build_api_url, build_callback_url, execute_robot_business_flow
from services.saga import get_saga_from_context, log_saga


class RobotFrameworkOperator(BaseOperator):
    """
    Operator for executing Robot Framework tasks via RPA API.
    
    Args:
        robot_test_file: Robot Framework test file name (e.g., "ecargo_pod_download.robot")
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
        except Exception as e:
            raise AirflowException(f"Failed to create RobotOperatorSaga: {e}") from e

        return result

