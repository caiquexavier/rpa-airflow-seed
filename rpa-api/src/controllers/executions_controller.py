"""Controller for execution endpoints."""
import logging
from typing import Dict, Any

from ..services.executions_service import create_execution, update_execution_status, get_execution, set_execution_running
from ..services.rabbitmq_service import publish_execution_message
from ..services.callback_service import post_callback
from ..validations.executions_models import (
    RpaExecutionRequestModel, RpaExecutionResponseModel,
    UpdateExecutionRequestModel, UpdateExecutionResponseModel,
    RabbitMQMessageModel, ExecutionStatus
)

logger = logging.getLogger(__name__)


def handle_request_rpa_exec(payload: RpaExecutionRequestModel) -> RpaExecutionResponseModel:
    """Handle RPA execution request."""
    try:
        # Create execution record
        exec_id = create_execution({
            "rpa_key_id": payload.rpa_key_id,
            "callback_url": str(payload.callback_url) if payload.callback_url else None,
            "rpa_request": payload.rpa_request or {}
        })
        
        if exec_id is None:
            raise Exception("Failed to create execution record")
        
        # Prepare RabbitMQ message
        message = RabbitMQMessageModel(
            exec_id=exec_id,
            rpa_key_id=payload.rpa_key_id,
            callback_url=str(payload.callback_url) if payload.callback_url else None,
            rpa_request=payload.rpa_request
        )
        
        # Publish to RabbitMQ
        published = publish_execution_message(message.dict())
        
        if published:
            # Set status to RUNNING after successful publish
            set_execution_running(exec_id)
            status = "ENQUEUED"
        else:
            status = "FAILED"
        
        return RpaExecutionResponseModel(
            exec_id=exec_id,
            rpa_key_id=payload.rpa_key_id,
            status=status,
            message="Execution accepted" if published else "Failed to publish to queue",
            published=published
        )
        
    except Exception as e:
        logger.error(f"Error in handle_request_rpa_exec: {e}")
        raise Exception(f"Failed to process execution request: {str(e)}")


def handle_update_rpa_execution(payload: UpdateExecutionRequestModel) -> UpdateExecutionResponseModel:
    """Handle RPA execution status update."""
    try:
        # Verify execution exists and get current status
        execution = get_execution(payload.exec_id)
        if not execution:
            raise ValueError(f"Execution {payload.exec_id} not found")
        
        if execution["rpa_key_id"] != payload.rpa_key_id:
            raise ValueError(f"RPA key ID mismatch for execution {payload.exec_id}")
        
        # Check if already in terminal state
        current_status = execution["exec_status"]
        if current_status in [ExecutionStatus.SUCCESS.value, ExecutionStatus.FAIL.value]:
            if current_status == payload.status.value:
                # Idempotent update - same status, return without database update or callback
                return UpdateExecutionResponseModel(
                    exec_id=payload.exec_id,
                    rpa_key_id=payload.rpa_key_id,
                    status=payload.status.value,
                    rpa_response=payload.rpa_response,
                    error_message=payload.error_message,
                    updated=True
                )
            else:
                raise ValueError(f"Execution {payload.exec_id} is already in terminal state: {current_status}")
        
        # Update execution in database
        full_update_payload = {
            "exec_id": payload.exec_id,
            "rpa_key_id": payload.rpa_key_id,
            "status": payload.status.value,
            "rpa_response": payload.rpa_response,
            "error_message": payload.error_message
        }

        updated = update_execution_status(
            exec_id=payload.exec_id,
            rpa_key_id=payload.rpa_key_id,
            status=payload.status,
            full_update_payload=full_update_payload,
            error_message=payload.error_message
        )
        
        if not updated:
            raise Exception("Failed to update execution")
        
        # Post callback to callback_url after successful database update
        callback_url = execution.get("callback_url")
        if callback_url:
            try:
                post_callback(
                    callback_url=callback_url,
                    exec_id=payload.exec_id,
                    rpa_key_id=payload.rpa_key_id,
                    status=payload.status.value,
                    rpa_response=payload.rpa_response,
                    error_message=payload.error_message
                )
            except Exception as callback_error:
                # Log error but don't fail the update - callback is best effort
                logger.warning(
                    f"Failed to post callback for exec_id={payload.exec_id} to {callback_url}: {callback_error}"
                )
        
        return UpdateExecutionResponseModel(
            exec_id=payload.exec_id,
            rpa_key_id=payload.rpa_key_id,
            status=payload.status.value,
            rpa_response=payload.rpa_response,
            error_message=payload.error_message,
            updated=True
        )
        
    except ValueError as e:
        logger.warning(f"Validation error in handle_update_rpa_execution: {e}")
        raise
    except Exception as e:
        logger.error(f"Error in handle_update_rpa_execution: {e}")
        raise Exception(f"Failed to update execution: {str(e)}")
