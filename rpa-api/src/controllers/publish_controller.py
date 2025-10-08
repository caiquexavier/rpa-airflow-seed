"""Publish controller for handling queue publishing requests."""
import logging
from typing import Dict, Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from ..services.queue_service import QueueService, QueuePublishError
from ..validations.publish_payload import PublishPayload

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/publish", tags=["publish"])


@router.post("/", status_code=200)
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

        # Validate the payload minimally (ensures required fields exist)
        _ = PublishPayload(**raw_payload)

        # Publish the original payload as-is
        queue_service = QueueService()
        queue_service.publish(raw_payload)

        logger.info("Successfully queued message")

        # Return the original payload
        return raw_payload
        
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
