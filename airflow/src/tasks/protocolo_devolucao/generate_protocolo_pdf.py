"""Generate PDF protocolo de devolucao from SAGA data - one PDF per doc_transportes."""
import logging
from pathlib import Path

from airflow.exceptions import AirflowException
from airflow.models import Variable

from services.pdf_generator import create_protocolo_de_devolucao_pdf
from services.saga import (
    get_saga_from_context,
    log_saga,
    build_saga_event,
    send_saga_event_to_api,
)

logger = logging.getLogger(__name__)


def generate_protocolo_pdf_task(**context):
    """Generate PDF protocolo de devolucao from SAGA data - one PDF per doc_transportes."""
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

