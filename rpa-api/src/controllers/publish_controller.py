"""Publish controller for handling queue publishing requests."""
import logging
from typing import Dict, Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from ..services.queue_service import QueueService, QueuePublishError
from ..validations.publish_payload import PublishPayload

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/publish", tags=["publish"])


@router.post("/", status_code=202)
async def publish_message(request: Request) -> Dict[str, str]:
    """
    Publish a message to the RabbitMQ queue.
    
    Expects JSON with 'rpa-id' field and publishes only the validated rpa-id to the queue.
    Extra fields in the request are ignored and not sent to the queue.
    
    Returns:
        Dict with status and rpa-id confirmation
    """
    try:
        # Get the raw JSON payload
        raw_payload: Dict[str, Any] = await request.json()
        
        # Validate the payload using Pydantic model
        validated_payload = PublishPayload(**raw_payload)
        
        # Extract the rpa-id for response
        rpa_id = validated_payload.rpa_id
        
        # Create payload with only validated fields (rpa-id only)
        payload = {"rpa-id": rpa_id}
        
        # Publish to queue
        queue_service = QueueService()
        queue_service.publish(payload)
        
        logger.info(f"Successfully queued message with rpa-id: {rpa_id}")
        
        return {
            "status": "queued",
            "rpa-id": rpa_id
        }
        
    except ValueError as e:
        # Pydantic validation error
        logger.warning(f"Validation error: {e}")
        raise HTTPException(
            status_code=422,
            detail=f"Validation error: {e}"
        )
    
    except QueuePublishError as e:
        # Queue service error
        logger.error(f"Queue publish error: {e}")
        raise HTTPException(
            status_code=503,
            detail="queue_unavailable"
        )
    
    except Exception as e:
        # Unexpected error
        logger.error(f"Unexpected error in publish endpoint: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )
