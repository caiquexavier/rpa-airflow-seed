# Start SAGA operator - Creates SAGA structure via rpa-api.
import logging
from typing import Any, Dict, Optional

import requests

from airflow.exceptions import AirflowException
from airflow.hooks.base import BaseHook
from airflow.models import BaseOperator
from airflow.utils.context import Context

from libs.rpa_robot_executor import build_api_url
from services.saga import log_saga

logger = logging.getLogger(__name__)


# ============================================================================
# Pure Functions
# ============================================================================



def extract_dag_context(context: Context) -> Dict[str, Any]:
    """
    Extract DAG context from Airflow context. Pure function.
    
    Args:
        context: Airflow context dictionary
        
    Returns:
        Dictionary with DAG context fields
    """
    dag = context.get('dag')
    dag_run = context.get('dag_run')
    task_instance = context.get('task_instance')
    
    dag_context = {}
    
    if dag:
        dag_context["dag_id"] = dag.dag_id
    
    if dag_run:
        dag_context["dag_run_id"] = dag_run.run_id
        if dag_run.execution_date:
            dag_context["execution_date"] = dag_run.execution_date.isoformat()
    
    if task_instance:
        dag_context["task_id"] = task_instance.task_id
        dag_context["try_number"] = task_instance.try_number
    
    # Extract operator information
    if task_instance and task_instance.task:
        operator = task_instance.task
        dag_context["operator_type"] = operator.__class__.__name__
        dag_context["operator_id"] = operator.task_id
        # Extract minimal operator params (only what's already available)
        operator_params = {}
        if hasattr(operator, 'rpa_key_id'):
            operator_params["rpa_key_id"] = operator.rpa_key_id
        if hasattr(operator, 'rpa_api_conn_id'):
            operator_params["rpa_api_conn_id"] = operator.rpa_api_conn_id
        if operator_params:
            dag_context["operator_params"] = operator_params
    
    return dag_context


def build_create_saga_payload(
    rpa_key_id: str,
    data: Dict[str, Any],
    dag_context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Build payload for createSaga API request. Pure function.
    
    Args:
        rpa_key_id: RPA key identifier
        data: Saga data payload
        dag_context: Optional DAG context dictionary
        
    Returns:
        Request payload dictionary
        
    Note: Saga creation returns saga_id (not exec_id).
    """
    payload = {
        "rpa_key_id": rpa_key_id,
        "data": data
    }
    
    # Add DAG context if provided
    if dag_context:
        payload.update(dag_context)
    
    return payload


def call_create_saga_api(
    api_url: str,
    payload: Dict[str, Any],
    timeout: int = 30
) -> requests.Response:
    """
    Make HTTP POST request to createSaga endpoint. Pure function.
    
    Args:
        api_url: Full API URL
        payload: Request payload
        timeout: Request timeout in seconds
        
    Returns:
        HTTP response object
    """
    response = requests.post(
        api_url,
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=timeout
    )
    return response


def validate_create_saga_response(response: requests.Response) -> None:
    """
    Validate createSaga API response. Pure function.
    
    Args:
        response: HTTP response object
        
    Raises:
        AirflowException: If response status is not successful
    """
    if response.status_code not in [200, 201]:
        error_msg = response.text if response.text else "Unknown error"
        raise AirflowException(
            f"createSaga API request failed with status {response.status_code}: {error_msg}"
        )


def parse_create_saga_response(response: requests.Response) -> Dict[str, Any]:
    """
    Parse createSaga API response JSON. Pure function.
    
    Args:
        response: HTTP response object
        
    Returns:
        Parsed response dictionary
    """
    return response.json()


def validate_saga_response(api_response: Dict[str, Any]) -> None:
    """
    Validate that API response contains required saga fields. Pure function.
    
    Args:
        api_response: API response dictionary
        
    Raises:
        AirflowException: If required fields are missing
    """
    required_fields = ["saga_id", "rpa_key_id", "data", "current_state"]
    missing_fields = [field for field in required_fields if field not in api_response]
    if missing_fields:
        logger.error(f"API response missing required fields: {missing_fields}")
        logger.error(f"API response keys: {list(api_response.keys())}")
        logger.error(f"API response: {api_response}")
        raise AirflowException(
            f"Invalid saga response from API: missing fields {missing_fields}. "
            f"Response keys: {list(api_response.keys())}"
        )


# ============================================================================
# Operator Class
# ============================================================================

class StartSagaOperator(BaseOperator):
    """
    Creates SAGA structure via rpa-api createSaga endpoint.
    
    Args:
        rpa_key_id: RPA key identifier
        rpa_api_conn_id: Connection ID for RPA API (default: "rpa_api")
        saga_xcom_key: XCom key for saga (default: "saga")
        rpa_payload_xcom_key: XCom key for backward compatibility (default: "rpa_payload")
        timeout: Request timeout in seconds (default: 30)
    """

    def __init__(
        self,
        rpa_key_id: str,
        rpa_api_conn_id: str = "rpa_api",
        saga_xcom_key: str = "saga",
        rpa_payload_xcom_key: str = "rpa_payload",
        timeout: int = 30,
        task_id: Optional[str] = None,
        **kwargs
    ):
        super().__init__(task_id=task_id, **kwargs)
        self.rpa_key_id = rpa_key_id
        self.rpa_api_conn_id = rpa_api_conn_id
        self.saga_xcom_key = saga_xcom_key
        self.rpa_payload_xcom_key = rpa_payload_xcom_key
        self.timeout = timeout

    def execute(self, context: Context) -> Dict[str, Any]:
        """
        Create SAGA via rpa-api createSaga endpoint.
        Orchestrates side effects and delegates to pure functions.
        """
        task_instance = context.get('task_instance')
        if not task_instance:
            raise AirflowException("Task instance not found in context")

        # Get context values
        dag = context.get('dag')
        dag_id = dag.dag_id if dag else ""
        task_id = self.task_id or "start_saga"

        # Extract DAG context
        dag_context = extract_dag_context(context)

        # Build API URL
        conn = BaseHook.get_connection(self.rpa_api_conn_id)
        api_url = build_api_url(
            schema=conn.schema,
            host=conn.host,
            port=conn.port,
            endpoint="/api/v1/saga/create"
        )

        # Build request payload (empty data initially, will be updated by convert task)
        payload = build_create_saga_payload(
            rpa_key_id=self.rpa_key_id,
            data={},  # Empty initially, will be updated by convert task
            dag_context=dag_context
        )

        # Call createSaga API - rpa-api creates saga, returns full object
        try:
            response = call_create_saga_api(
                api_url=api_url,
                payload=payload,
                timeout=self.timeout
            )
            validate_create_saga_response(response)
            saga = parse_create_saga_response(response)  # API returns full saga object
            validate_saga_response(saga)  # Validate required fields
        except requests.exceptions.RequestException as e:
            raise AirflowException(f"Failed to call createSaga API: {e}") from e
        except Exception as e:
            raise AirflowException(f"Error creating saga: {e}") from e

        # Always log saga into Airflow
        log_saga(saga, task_id=task_id)

        # Push to XCom for use between DAG execution
        # rpa-api returns complete saga object - no conversion needed
        task_instance.xcom_push(key=self.saga_xcom_key, value=saga)
        task_instance.xcom_push(key=self.rpa_payload_xcom_key, value=saga)  # Backward compatibility

        logger.info(
            f"Created SAGA via API: saga_id={saga.get('saga_id')}, "
            f"rpa_key_id={saga.get('rpa_key_id')}"
        )
        logger.debug(f"Full saga pushed to XCom: {saga}")

        return saga

