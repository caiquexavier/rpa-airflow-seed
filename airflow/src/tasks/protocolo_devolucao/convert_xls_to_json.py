"""Convert XLSX file to RPA request payload and update SAGA."""
import logging
from airflow.exceptions import AirflowException
from airflow.models import Variable

from services.converter import xls_to_rpa_request
from services.saga import (
    log_saga,
    build_saga_event,
    send_saga_event_to_api,
    update_saga_data_in_api,
)

logger = logging.getLogger(__name__)


def convert_xls_to_json_task(**context):
    """Convert XLSX file to RPA request payload and update SAGA."""
    xlsx_path = Variable.get("ECARGO_XLSX_PATH", default_var="")
    if not xlsx_path:
        raise AirflowException("ECARGO_XLSX_PATH Airflow Variable is required")
    
    logger.info("Converting XLSX file at path configured via ECARGO_XLSX_PATH")
    rpa_data = xls_to_rpa_request(xlsx_path)
    
    # Get existing SAGA from StartSagaOperator (upstream task)
    ti = context["task_instance"]
    dag_run = context.get("dag_run")
    run_id = dag_run.run_id if dag_run else None
    
    logger.debug("Retrieving SAGA from 'start_saga' task (run_id=%s)", run_id)
    
    # Pull from upstream task 'start_saga'
    saga = ti.xcom_pull(task_ids="start_saga", key="saga", default=None)
    if saga:
        logger.debug(
            "Retrieved SAGA from 'start_saga' with saga_id=%s",
            saga.get("saga_id") if isinstance(saga, dict) else "N/A",
        )
    else:
        logger.warning("SAGA not found with task_ids='start_saga', trying fallback")
        # Fallback: try without task_ids (current task)
        saga = ti.xcom_pull(key="saga", default=None)
        if saga:
            logger.debug(
                "Retrieved SAGA from fallback with saga_id=%s",
                saga.get("saga_id") if isinstance(saga, dict) else "N/A",
            )
    
    if saga:
        # Validate saga has required fields (saga_id must be present from saga creation)
        if "saga_id" not in saga or not saga.get("saga_id"):
            logger.error(f"SAGA missing saga_id. Saga keys: {list(saga.keys())}")
            logger.error(f"Full saga retrieved: {saga}")
            raise AirflowException(
                f"SAGA must have saga_id (created by saga creation). "
                f"Received saga with keys: {list(saga.keys())}"
            )
        
        # Update SAGA with RPA data (preserve all existing fields)
        saga["rpa_key_id"] = rpa_data["rpa_key_id"]
        saga["data"] = rpa_data["data"]  # Use 'data' field (rpa_request_object was replaced)
        
        # Ensure events list exists
        if "events" not in saga:
            saga["events"] = []
        
        # Persist updated saga data in rpa-api before recording the event
        updated_in_api = update_saga_data_in_api(saga, rpa_api_conn_id="rpa_api")
        if not updated_in_api:
            logger.warning(
                "Failed to persist updated saga data for saga_id=%s in rpa-api",
                saga.get("saga_id"),
            )

        # Add conversion event with complete DAG and operator context
        event = build_saga_event(
            event_type="TaskCompleted",
            event_data={
                "step": "convert_xls_to_json",
                "status": "SUCCESS",
                "dt_count": len(rpa_data["data"].get("dt_list", []))
            },
            context=context,
            task_id="read_input_xls"
        )
        saga["events"].append(event)
        
        # Send event to rpa-api for persistence
        send_saga_event_to_api(saga, event, rpa_api_conn_id="rpa_api")
        
        # Update events_count to match actual events array length
        saga["events_count"] = len(saga["events"])
        
        # Update SAGA in XCom (preserves all fields)
        ti.xcom_push(key="saga", value=saga)
        ti.xcom_push(key="rpa_payload", value=saga)  # Backward compatibility
        
        log_saga(saga, task_id="read_input_xls")
    else:
        # If no SAGA exists, push RPA data for backward compatibility
        ti.xcom_push(key="rpa_data", value=rpa_data)
    
    return rpa_data

