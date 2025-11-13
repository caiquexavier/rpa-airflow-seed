# FastAPI application for Airflow webhook endpoints
import os
import sys
import logging
import json
from typing import Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel

# Add src directory to path for imports
src_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from services.webhook import set_webhook_signal, get_latest_dag_run

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(title="Airflow API", version="0.1.0")


class RpaExecutionResponse(BaseModel):
    """Model for RPA execution response from rpa-api."""
    exec_id: int
    rpa_key_id: str
    status: str
    rpa_response: Dict[str, Any]
    error_message: Optional[str] = None


@app.get("/health", summary="Service health check")
async def health_check() -> dict[str, str]:
    """Basic readiness endpoint."""
    return {"status": "ok"}


@app.post("/trigger/upload_nf_files_to_s3", summary="Trigger upload_nf_files_to_s3 task")
async def trigger_upload_nf_files_to_s3(request: Request) -> Dict[str, Any]:
    """Trigger task by setting webhook signal for waiting sensor. Accepts RPA execution response from rpa-api."""
    dag_id = "rpa_protocolo_devolucao"
    task_id = "upload_nf_files_to_s3"
    try:
        # Read message from POST body
        body = await request.json()
        logger.info(f"Received webhook body: {body}")
        
        # Extract webhook data - handle different formats
        if isinstance(body, dict) and "exec_id" in body and "status" in body:
            # RPA execution response format (from rpa-api)
            webhook_data = body
        elif isinstance(body, dict) and "data" in body:
            # Legacy format: {"data": "string"}
            data_str = body.get("data")
            if data_str:
                try:
                    webhook_data = json.loads(data_str) if isinstance(data_str, str) else data_str
                except (json.JSONDecodeError, TypeError):
                    webhook_data = data_str
            else:
                webhook_data = None
        else:
            webhook_data = body if isinstance(body, dict) else None
        
        # Log status for debugging
        if isinstance(webhook_data, dict):
            status = webhook_data.get("status", "N/A")
            logger.info(f"Webhook data status: {status}")
        
        # Store webhook data - sensor will validate status
        dag_run_id = get_latest_dag_run(dag_id)
        set_webhook_signal(dag_id=dag_id, task_id=task_id, run_id=dag_run_id, data=webhook_data)
        logger.info(f"Webhook signal set for dag_id={dag_id}, task_id={task_id}, run_id={dag_run_id}")
        
        return {"status": "success", "message": "Webhook signal set successfully", "dag_run_id": dag_run_id, "dag_id": dag_id, "task_id": task_id}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


