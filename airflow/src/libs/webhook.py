"""Webhook-based task activation utilities for Airflow."""
from typing import Optional, Any
import json
import logging
from airflow.models import XCom, DagRun
from airflow.utils.session import provide_session
from airflow.sensors.base import BaseSensorOperator
from airflow.utils.context import Context
from airflow.exceptions import AirflowException
from sqlalchemy import desc

logger = logging.getLogger(__name__)


@provide_session
def get_latest_dag_run(dag_id: str, session=None) -> str:
    """Get the latest DAG run ID."""
    dag_run = session.query(DagRun).filter(DagRun.dag_id == dag_id).order_by(desc(DagRun.execution_date)).first()
    if not dag_run:
        raise ValueError("No active DAG run found. Please trigger the DAG first.")
    return dag_run.run_id


@provide_session
def set_webhook_signal(dag_id: str, task_id: str, run_id: str, data: Optional[Any] = None, signal_key: str = "webhook_triggered", data_key: str = "webhook_data", session=None) -> None:
    """Set webhook signal in XCom to activate a waiting task."""
    XCom.set(key=signal_key, value=True, dag_id=dag_id, task_id=task_id, run_id=run_id, session=session)
    if data is not None:
        # Serialize to JSON string to ensure XCom can store it properly
        if isinstance(data, (dict, list)):
            data_value = json.dumps(data)
        else:
            data_value = data
        XCom.set(key=data_key, value=data_value, dag_id=dag_id, task_id=task_id, run_id=run_id, session=session)
    session.commit()


@provide_session
def check_webhook_signal(dag_id: str, task_id: str, run_id: str, signal_key: str = "webhook_triggered", session=None) -> bool:
    """Check if webhook signal exists in XCom."""
    xcom_entry = session.query(XCom).filter(XCom.dag_id == dag_id, XCom.run_id == run_id, XCom.task_id == task_id, XCom.key == signal_key).first()
    return xcom_entry is not None


def get_webhook_data(task_instance, target_task_id: str, dag_id: str, data_key: str = "webhook_data") -> Optional[Any]:
    """Get webhook data from XCom."""
    data = task_instance.xcom_pull(key=data_key, task_ids=target_task_id, dag_id=dag_id, include_prior_dates=True)
    # If data is a JSON string, parse it; otherwise return as-is
    if isinstance(data, str):
        try:
            return json.loads(data)
        except (json.JSONDecodeError, TypeError):
            return data
    return data


class WebhookSensor(BaseSensorOperator):
    """Sensor that waits for HTTP webhook to trigger a task."""
    
    def __init__(self, target_task_id: str, signal_key: str = "webhook_triggered", data_key: str = "webhook_data", output_key: str = "webhook_data", **kwargs):
        super().__init__(**kwargs)
        self.target_task_id = target_task_id
        self.signal_key = signal_key
        self.data_key = data_key
        self.output_key = output_key
    
    def poke(self, context: Context) -> bool:
        """Check if webhook has been triggered. Returns True when webhook signal is detected."""
        task_instance = context['task_instance']
        dag_run = context['dag_run']
        
        # Only check if webhook signal exists - don't validate status here
        return check_webhook_signal(dag_id=dag_run.dag_id, task_id=self.target_task_id, run_id=dag_run.run_id, signal_key=self.signal_key)
    
    def execute(self, context: Context) -> Any:
        """Execute sensor and validate webhook status. Raises AirflowException if status is FAIL."""
        # First, run the sensor's normal execute (which calls poke() until it returns True)
        result = super().execute(context)
        
        # After sensor detects webhook, validate the status
        task_instance = context['task_instance']
        dag_run = context['dag_run']
        
        # Get webhook data
        webhook_data = get_webhook_data(task_instance=task_instance, target_task_id=self.target_task_id, dag_id=dag_run.dag_id, data_key=self.data_key)
        logger.info(f"[WebhookSensor] Retrieved webhook data: {type(webhook_data)}")
        
        # Validate status - THIS WILL FAIL THE TASK IF STATUS IS NOT SUCCESS
        if webhook_data is None:
            logger.warning("[WebhookSensor] Webhook data is None - skipping validation")
            return result
        
        if not isinstance(webhook_data, dict):
            logger.warning(f"[WebhookSensor] Webhook data is not a dict: {type(webhook_data)} - skipping validation")
            return result
        
        status = webhook_data.get("status")
        if status is None:
            logger.warning("[WebhookSensor] Webhook data missing 'status' field - skipping validation")
            return result
        
        # Convert to uppercase for comparison
        status_upper = str(status).upper()
        logger.info(f"[WebhookSensor] Validating webhook status: {status_upper}")
        
        # FAIL THE TASK if status is not SUCCESS
        if status_upper != "SUCCESS":
            error_msg = (
                webhook_data.get("error_message") or
                (webhook_data.get("rpa_response", {}).get("error") if isinstance(webhook_data.get("rpa_response"), dict) else None) or
                f"RPA execution failed with status: {status_upper}"
            )
            logger.error(f"[WebhookSensor] FAILURE DETECTED - Status: {status_upper}, Error: {error_msg}")
            # Raise exception in execute() method - this will definitely fail the task
            raise AirflowException(f"Webhook response indicates failure. Status: {status_upper}. Error message: {error_msg}")
        
        # Status is SUCCESS - store data and continue
        logger.info("[WebhookSensor] Status is SUCCESS - proceeding")
        context['ti'].xcom_push(key=self.output_key, value=webhook_data)
        return result
