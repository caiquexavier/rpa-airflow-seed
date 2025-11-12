# FastAPI application for Airflow webhook endpoints
import os
import sys
import logging
from typing import Optional, Dict, Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Add src directory to path for imports
src_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from libs.webhook import set_webhook_signal, get_latest_dag_run

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(title="Airflow API", version="0.1.0")


class TriggerTaskRequest(BaseModel):
    # Request model for triggering a task
    data: Optional[str] = None


@app.get("/health", summary="Service health check")
async def health_check() -> dict[str, str]:
    # Basic readiness endpoint
    return {"status": "ok"}


@app.post("/trigger/upload_nf_files_to_s3", summary="Trigger upload_nf_files_to_s3 task")
async def trigger_upload_nf_files_to_s3(request: TriggerTaskRequest) -> Dict[str, Any]:
    # Trigger task by setting webhook signal for waiting sensor
    dag_id = "ecargo_pod_download"
    task_id = "upload_nf_files_to_s3"
    try:
        dag_run_id = get_latest_dag_run(dag_id)
        set_webhook_signal(dag_id=dag_id, task_id=task_id, run_id=dag_run_id, data=request.data)
        return {"status": "success", "message": "Webhook signal set successfully", "dag_run_id": dag_run_id, "dag_id": dag_id, "task_id": task_id}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


