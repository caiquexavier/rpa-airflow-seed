"""Task functions for rpa_protocolo_devolucao DAG."""
import logging
from datetime import datetime
from typing import Dict, Any

from airflow.exceptions import AirflowException
from airflow.models import Variable

from services.converter import xls_to_rpa_request
from services.pdf_generator import create_protocolo_de_devolucao_pdf
from services.saga import (
    get_saga_rpa_key_id,
    get_saga_rpa_request,
    log_saga,
    build_saga_event,
    send_saga_event_to_api,
    get_saga_from_context,
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


def upload_nf_files_to_s3_task(**context):
    """Upload NF files to S3."""
    # Get SAGA from previous tasks
    ti = context.get('task_instance')
    saga = None
    
    # Try to get SAGA from webhook_data first (most recent)
    webhook_data = ti.xcom_pull(key='webhook_data', default=None) if ti else None
    if webhook_data and isinstance(webhook_data, dict):
        saga = webhook_data.get('saga')
        if not saga and 'rpa_key_id' in webhook_data:
            # webhook_data itself might be SAGA-like
            saga = webhook_data
    
    # Fallback to XCom saga key
    if not saga and ti:
        saga = ti.xcom_pull(key='saga', default=None)
    
    # Log SAGA as INFO
    log_saga(saga, task_id="upload_nf_files_to_s3")
    
    # Get rpa_key_id and rpa_request from SAGA
    rpa_key_id = get_saga_rpa_key_id(saga)
    rpa_request = get_saga_rpa_request(saga)
    
    # Placeholder for S3 upload logic
    # TODO: Implement actual S3 upload logic here
    logger.info(f"Uploading NF files to S3 with SAGA: rpa_key_id={rpa_key_id}")
    
    return {"status": "uploaded", "saga": saga}


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


def generate_protocolo_pdf_task(**context):
    """Generate PDF protocolo de devolucao from SAGA data - one PDF per doc_transportes."""
    from pathlib import Path
    
    ti = context.get("task_instance")
    saga = get_saga_from_context(context)
    
    if not saga or not saga.get("saga_id"):
        raise AirflowException("SAGA not found in context, cannot generate PDF")
    
    # Get output directory from Variable or use default
    output_dir = Variable.get("PROTOCOLO_PDF_OUTPUT_DIR", default_var="/opt/airflow/data/protocolos")
    output_dir_path = Path(output_dir)
    output_dir_path.mkdir(parents=True, exist_ok=True)
    
    logger.info("Generating PDF protocolo de devolucao for saga_id=%s", saga.get("saga_id"))
    logger.info("Output directory: %s", output_dir_path)
    
    # Extract saga data for PDF generation
    saga_data = {
        "doc_transportes_list": saga.get("data", {}).get("doc_transportes_list", []),
        "extracted_data": saga.get("data", {}).get("extracted_data", {}),
        "saga_id": saga.get("saga_id"),
    }
    
    doc_transportes_list = saga_data.get("doc_transportes_list", [])
    if not doc_transportes_list:
        logger.warning("No doc_transportes_list found in SAGA data, cannot generate PDFs")
        return {
            "status": "success",
            "files_generated": 0,
            "output_paths": [],
            "saga_id": saga.get("saga_id")
        }
    
    # Generate one PDF for each doc_transportes
    generated_files = []
    for doc_entry in doc_transportes_list:
        doc_transportes = doc_entry.get("doc_transportes")
        if not doc_transportes:
            logger.warning("Found doc_transportes entry without value, skipping")
            continue
        
        doc_transportes_str = str(doc_transportes).strip()
        if not doc_transportes_str:
            continue
        
        # Generate filename: doc_transportes_POD.pdf
        output_filename = f"{doc_transportes_str}_POD.pdf"
        output_path = output_dir_path / output_filename
        
        logger.info("Generating PDF for doc_transportes=%s, output: %s", doc_transportes_str, output_path)
        
        try:
            create_protocolo_de_devolucao_pdf(
                output_path=str(output_path),
                saga_data=saga_data,
                doc_transportes=doc_transportes_str
            )
            logger.info("Successfully generated PDF at: %s", output_path)
            generated_files.append(str(output_path))
        except Exception as e:
            logger.error("Failed to generate PDF for doc_transportes %s: %s", doc_transportes_str, e)
            # Continue with other files even if one fails
            continue
    
    if not generated_files:
        logger.error("No PDFs were generated successfully")
        raise AirflowException("PDF generation failed: no files were generated")
    
    # Update SAGA with event
    if "events" not in saga:
        saga["events"] = []
    
    event = build_saga_event(
        event_type="TaskCompleted",
        event_data={
            "step": "generate_protocolo_pdf",
            "status": "SUCCESS",
            "files_generated": len(generated_files),
            "output_paths": generated_files,
        },
        context=context,
        task_id="generate_protocolo_pdf"
    )
    saga["events"].append(event)
    
    # Send event to rpa-api for persistence
    send_saga_event_to_api(saga, event, rpa_api_conn_id="rpa_api")
    
    # Update events_count
    saga["events_count"] = len(saga["events"])
    
    # Push updated SAGA back to XCom
    if ti:
        ti.xcom_push(key="saga", value=saga)
        ti.xcom_push(key="rpa_payload", value=saga)  # Backward compatibility
    
    # Log SAGA
    log_saga(saga, task_id="generate_protocolo_pdf")
    
    return {
        "status": "success",
        "files_generated": len(generated_files),
        "output_paths": generated_files,
        "saga_id": saga.get("saga_id")
    }

