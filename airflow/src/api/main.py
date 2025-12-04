# FastAPI application for Airflow webhook endpoints
import json
import logging
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel

from services.webhook import get_latest_dag_run, set_webhook_signal

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(title="Airflow API", version="0.1.0")


@app.on_event("startup")
async def startup_event():
    """Log all registered routes on startup."""
    routes = [r.path for r in app.routes if hasattr(r, 'path')]
    logger.info(f"FastAPI app started. Registered {len(routes)} routes:")
    for route in sorted(routes):
        logger.info(f"  {route}")


class RpaExecutionResponse(BaseModel):
    """Model for RPA execution response from rpa-api."""
    saga_id: int
    rpa_key_id: str
    status: str
    rpa_response: Dict[str, Any]
    error_message: Optional[str] = None


def _normalize_webhook_data(body: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize and validate webhook data from request body."""
    # Extract webhook data - handle different formats
    if isinstance(body, dict) and "saga_id" in body and "status" in body:
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
    
    if not isinstance(webhook_data, dict):
        return {}
    
    # Normalize robot_saga to robot_operator_saga for consistency
    if "robot_saga" in webhook_data and "robot_operator_saga" not in webhook_data:
        webhook_data["robot_operator_saga"] = webhook_data.pop("robot_saga")
        logger.info("Normalized 'robot_saga' to 'robot_operator_saga' in webhook payload")
    
    # Extract status from robot_operator_saga if missing
    if "status" not in webhook_data:
        robot_operator_saga = webhook_data.get("robot_operator_saga") or webhook_data.get("robot_saga")
        if isinstance(robot_operator_saga, dict):
            # Try to extract status from robot_operator_saga current_state
            current_state = robot_operator_saga.get("current_state", "").upper()
            if current_state in ["COMPLETED", "SUCCESS"]:
                webhook_data["status"] = "SUCCESS"
                logger.info("Extracted status=SUCCESS from robot_operator_saga.current_state")
            elif current_state in ["FAILED", "FAIL"]:
                webhook_data["status"] = "FAIL"
                logger.info("Extracted status=FAIL from robot_operator_saga.current_state")
            else:
                # Default to SUCCESS if state is unclear
                webhook_data["status"] = "SUCCESS"
                logger.warning(f"Status missing and could not determine from current_state='{current_state}', defaulting to SUCCESS")
        else:
            # Default to SUCCESS if robot_operator_saga is not available
            webhook_data["status"] = "SUCCESS"
            logger.warning("Status missing and robot_operator_saga not available, defaulting to SUCCESS")
    
    return webhook_data


def _log_webhook_data(webhook_data: Dict[str, Any]) -> None:
    """Log webhook data for debugging."""
    status = webhook_data.get("status", "N/A")
    logger.info(f"Webhook data status: {status}")
    
    # Log parent SAGA if present
    saga = webhook_data.get("saga")
    saga_id = webhook_data.get("saga_id")
    if saga:
        logger.info(f"SAGA: {json.dumps(saga, indent=2, ensure_ascii=False)}")
    elif saga_id:
        logger.info(f"SAGA ID: {saga_id} (full SAGA not available in payload)")
    
    # Log RobotOperatorSaga if present
    robot_operator_saga = webhook_data.get("robot_operator_saga") or webhook_data.get("robot_saga")
    if robot_operator_saga:
        logger.info(f"RobotOperatorSaga: {json.dumps(robot_operator_saga, indent=2, ensure_ascii=False)}")
    else:
        logger.warning("RobotOperatorSaga not found in webhook payload")


async def _handle_webhook_trigger(
    request: Request,
    dag_id: str,
    task_id: str
) -> Dict[str, Any]:
    """
    Generic webhook handler that processes webhook requests and triggers Airflow tasks.
    
    Args:
        request: FastAPI request object
        dag_id: DAG ID to trigger
        task_id: Task ID to trigger
        
    Returns:
        Success response with dag_run_id and task details
    """
    try:
        # Read message from POST body
        body = await request.json()
        logger.info(f"Received webhook for {task_id}: {body}")
        
        # Normalize webhook data
        webhook_data = _normalize_webhook_data(body)
        
        # Log webhook data
        _log_webhook_data(webhook_data)
        
        # Store webhook data - sensor will validate status
        dag_run_id = get_latest_dag_run(dag_id)
        set_webhook_signal(dag_id=dag_id, task_id=task_id, run_id=dag_run_id, data=webhook_data)
        logger.info(f"Webhook signal set for dag_id={dag_id}, task_id={task_id}, run_id={dag_run_id}")
        
        return {
            "status": "success",
            "message": "Webhook signal set successfully",
            "dag_run_id": dag_run_id,
            "dag_id": dag_id,
            "task_id": task_id
        }
    except ValueError as e:
        logger.error(f"ValueError in webhook handler for {task_id}: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error in webhook handler for {task_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@app.get("/health", summary="Service health check")
async def health_check() -> dict[str, str]:
    """Basic readiness endpoint."""
    return {"status": "ok"}


@app.get("/routes", summary="List all registered routes")
async def list_routes() -> Dict[str, Any]:
    """Debug endpoint to list all registered routes."""
    routes = []
    for route in app.routes:
        if hasattr(route, 'path') and hasattr(route, 'methods'):
            routes.append({
                "path": route.path,
                "methods": list(route.methods),
                "name": getattr(route, 'name', 'N/A')
            })
    return {"routes": routes, "total": len(routes)}


@app.post("/trigger/upload_nf_files_to_s3", summary="Trigger upload_nf_files_to_s3 task")
async def trigger_upload_nf_files_to_s3(request: Request) -> Dict[str, Any]:
    """Trigger task by setting webhook signal for waiting sensor. Accepts RPA execution response from rpa-api."""
    return await _handle_webhook_trigger(
        request=request,
        dag_id="rpa_protocolo_devolucao",
        task_id="upload_nf_files_to_s3"
    )


@app.post("/trigger/split_pdf_files", summary="Trigger split_pdf_files task")
async def trigger_split_pdf_files(request: Request) -> Dict[str, Any]:
    """Trigger task by setting webhook signal for waiting sensor. Accepts RPA execution response from rpa-api."""
    return await _handle_webhook_trigger(
        request=request,
        dag_id="rpa_protocolo_devolucao",
        task_id="split_pdf_files"
    )


@app.post("/trigger/robot_download_multi_cte_reports", summary="Trigger robot_download_multi_cte_reports task")
async def trigger_robot_download_multi_cte_reports(request: Request) -> Dict[str, Any]:
    """Trigger task by setting webhook signal for waiting sensor. Accepts RPA execution response from rpa-api."""
    return await _handle_webhook_trigger(
        request=request,
        dag_id="rpa_protocolo_devolucao",
        task_id="robot_download_multi_cte_reports"
    )


@app.post("/trigger/complete_saga", summary="Trigger complete_saga task")
async def trigger_complete_saga(request: Request) -> Dict[str, Any]:
    """Trigger task by setting webhook signal for waiting sensor. Accepts RPA execution response from rpa-api."""
    return await _handle_webhook_trigger(
        request=request,
        dag_id="rpa_protocolo_devolucao",
        task_id="complete_saga"
    )
