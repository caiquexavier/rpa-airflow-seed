"""Mark SAGA as completed when all DAG tasks finish successfully."""
import logging

from services.saga import (
    get_saga_from_context,
    log_saga,
    build_saga_event,
    send_saga_event_to_api,
)

logger = logging.getLogger(__name__)


def complete_saga_task(**context):
    """Mark SAGA as completed when all DAG tasks finish successfully."""
    ti = context.get('task_instance')
    saga = get_saga_from_context(context)
    
    if not saga or not saga.get("saga_id"):
        logger.warning("SAGA not found in context, cannot mark as completed")
        return {"status": "skipped", "reason": "SAGA not found"}
    
    logger.info(f"Completing SAGA {saga.get('saga_id')} - all DAG tasks finished successfully")
    
    # Ensure events list exists
    if "events" not in saga:
        saga["events"] = []
    
    # Build completion event
    event = build_saga_event(
        event_type="SagaCompleted",
        event_data={
            "step": "dag_completion",
            "status": "COMPLETED",
            "message": "All DAG tasks completed successfully"
        },
        context=context,
        task_id="complete_saga"
    )
    saga["events"].append(event)
    
    # Send completion event to rpa-api
    send_saga_event_to_api(saga, event, rpa_api_conn_id="rpa_api")
    
    # Update current_state to COMPLETED
    saga["current_state"] = "COMPLETED"
    saga["events_count"] = len(saga["events"])
    
    # Push final SAGA state to XCom
    if ti:
        ti.xcom_push(key="saga", value=saga)
        ti.xcom_push(key="rpa_payload", value=saga)  # Backward compatibility
    
    # Log final SAGA state
    log_saga(saga, task_id="complete_saga")
    
    logger.info(f"SAGA {saga.get('saga_id')} marked as COMPLETED with {len(saga.get('events', []))} events")
    
    return {"status": "completed", "saga_id": saga.get("saga_id"), "events_count": len(saga.get("events", []))}

