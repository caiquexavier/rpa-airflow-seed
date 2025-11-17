"""Webhook-based task activation utilities for Airflow."""
import json
import logging
from typing import Any, Optional

from airflow.exceptions import AirflowException
from airflow.models import DagRun, XCom
from airflow.sensors.base import BaseSensorOperator
from airflow.utils.context import Context
from airflow.utils.session import provide_session
from sqlalchemy import desc

from services.saga import get_saga_from_context, build_saga_event, send_saga_event_to_api, log_saga

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


@provide_session
def get_webhook_data(task_instance, target_task_id: str, dag_id: str, data_key: str = "webhook_data", session=None) -> Optional[Any]:
    """Get webhook data from XCom using direct query."""
    dag_run = task_instance.get_dagrun()
    run_id = dag_run.run_id
    
    # Query XCom directly to get webhook data
    xcom_entry = session.query(XCom).filter(
        XCom.dag_id == dag_id,
        XCom.run_id == run_id,
        XCom.task_id == target_task_id,
        XCom.key == data_key
    ).first()
    
    if xcom_entry is None:
        return None
    
    # Get the value from XCom
    data = xcom_entry.value
    
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
        # Run the sensor's normal execute (which calls poke() until it returns True)
        result = super().execute(context)
        
        # After sensor detects webhook, validate the status
        task_instance = context['task_instance']
        dag_run = context['dag_run']
        
        # Get webhook data using direct XCom query
        webhook_data = get_webhook_data(task_instance=task_instance, target_task_id=self.target_task_id, dag_id=dag_run.dag_id, data_key=self.data_key)
        logger.info(f"[WebhookSensor] Retrieved webhook data: {type(webhook_data)}")
        
        if isinstance(webhook_data, dict):
            logger.info(f"[WebhookSensor] Webhook data keys: {list(webhook_data.keys())}")
            
            # Log SAGA if present
            saga = webhook_data.get("saga")
            if saga:
                logger.info(f"[WebhookSensor] SAGA: {json.dumps(saga, indent=2, ensure_ascii=False)}")
            
            # Log RobotOperatorSaga if present
            robot_operator_saga = webhook_data.get("robot_operator_saga") or webhook_data.get("robot_saga")
            if robot_operator_saga:
                logger.info(f"[WebhookSensor] RobotOperatorSaga: {json.dumps(robot_operator_saga, indent=2, ensure_ascii=False)}")
        
        # Validate status - fail task if data is missing or status is not SUCCESS
        if webhook_data is None:
            error_msg = "Webhook data is None - cannot validate status"
            logger.error(f"[WebhookSensor] ERROR: {error_msg}")
            raise AirflowException(error_msg)
        
        if not isinstance(webhook_data, dict):
            error_msg = f"Webhook data is not a dict: {type(webhook_data)} - cannot validate status"
            logger.error(f"[WebhookSensor] ERROR: {error_msg}")
            raise AirflowException(error_msg)
        
        status = webhook_data.get("status")
        if status is None:
            error_msg = f"Webhook data missing 'status' field. Available keys: {list(webhook_data.keys())}"
            logger.error(f"[WebhookSensor] ERROR: {error_msg}")
            raise AirflowException(error_msg)
        
        status_upper = str(status).upper()
        logger.info(f"[WebhookSensor] Validating webhook status: {status_upper}")
        
        # FAIL THE TASK if status is not SUCCESS
        if status_upper != "SUCCESS":
            # Extract error message
            error_msg = (
                webhook_data.get("error_message") or
                (webhook_data.get("rpa_response", {}).get("error") if isinstance(webhook_data.get("rpa_response"), dict) else None) or
                f"RPA execution failed with status: {status_upper}"
            )
            
            # Build detailed error message with SAGA and RobotOperatorSaga information
            saga_info_parts = []
            
            # Include SAGA information
            saga = webhook_data.get("saga")
            saga_id = webhook_data.get("saga_id")
            if saga:
                saga_id_from_saga = saga.get("saga_id", "N/A")
                saga_state = saga.get("current_state", "N/A")
                saga_info_parts.append(f"SAGA(id={saga_id_from_saga}, state={saga_state})")
            elif saga_id:
                saga_info_parts.append(f"SAGA(id={saga_id})")
            
            # Include RobotOperatorSaga information
            robot_operator_saga = webhook_data.get("robot_operator_saga") or webhook_data.get("robot_saga")
            if robot_operator_saga and isinstance(robot_operator_saga, dict):
                robot_saga_id = robot_operator_saga.get("robot_operator_saga_id", "N/A")
                robot_saga_state = robot_operator_saga.get("current_state", "N/A")
                robot_operator_id = robot_operator_saga.get("robot_operator_id", "N/A")
                saga_info_parts.append(f"RobotOperatorSaga(id={robot_saga_id}, state={robot_saga_state}, operator={robot_operator_id})")
            
            # Build comprehensive error message
            saga_context = f" [{', '.join(saga_info_parts)}]" if saga_info_parts else ""
            detailed_error = f"Webhook response indicates failure. Status: {status_upper}. Error message: {error_msg}{saga_context}"
            
            # Log full details including SAGA and RobotOperatorSaga
            logger.error(f"[WebhookSensor] FAILURE DETECTED - Status: {status_upper}, Error: {error_msg}")
            if saga:
                logger.error(f"[WebhookSensor] FAILURE SAGA details: {json.dumps(saga, indent=2, ensure_ascii=False)}")
            if robot_operator_saga:
                logger.error(f"[WebhookSensor] FAILURE RobotOperatorSaga details: {json.dumps(robot_operator_saga, indent=2, ensure_ascii=False)}")
            
            raise AirflowException(detailed_error)
        
        # Status is SUCCESS - store data and continue
        logger.info("[WebhookSensor] Status is SUCCESS - proceeding")
        context['ti'].xcom_push(key=self.output_key, value=webhook_data)
        
        # Update SAGA with webhook received event
        saga = get_saga_from_context(context)
        if saga and saga.get("saga_id"):
            # Merge webhook_data saga if present (may have updated robot_sagas)
            webhook_saga = webhook_data.get("saga")
            if webhook_saga and isinstance(webhook_saga, dict):
                # Merge robot_sagas if present in webhook
                if "robot_sagas" in webhook_saga:
                    saga["robot_sagas"] = webhook_saga["robot_sagas"]
                # Merge any other updated fields
                for key in ["current_state", "data", "rpa_key_id"]:
                    if key in webhook_saga:
                        saga[key] = webhook_saga[key]
            
            # Ensure events list exists
            if "events" not in saga:
                saga["events"] = []
            
            # Build event for webhook received
            event = build_saga_event(
                event_type="TaskCompleted",
                event_data={
                    "step": "webhook_received",
                    "status": "SUCCESS",
                    "webhook_status": status_upper,
                    "target_task_id": self.target_task_id,
                    "robot_operator_saga_id": webhook_data.get("robot_operator_saga", {}).get("robot_operator_saga_id") if isinstance(webhook_data.get("robot_operator_saga"), dict) else None
                },
                context=context,
                task_id=self.task_id
            )
            saga["events"].append(event)
            
            # Send event to rpa-api
            send_saga_event_to_api(saga, event, rpa_api_conn_id="rpa_api")
            
            # Update events_count
            saga["events_count"] = len(saga["events"])
            
            # Push updated SAGA back to XCom
            task_instance = context.get('task_instance')
            if task_instance:
                task_instance.xcom_push(key="saga", value=saga)
                task_instance.xcom_push(key="rpa_payload", value=saga)  # Backward compatibility
            
            log_saga(saga, task_id=self.task_id)
        
        return result
