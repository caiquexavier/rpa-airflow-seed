"""Controller for handling RPA execution requests."""
import logging
from typing import Dict, Any

from ..services.rabbitmq_service import publish_json
from ..services.rpa_automation_exec_service import insert as insert_exec_record
from ..validations.request_models import RpaRequestModel

logger = logging.getLogger(__name__)


def handle_request_rpa_exec(payload_model: RpaRequestModel) -> Dict[str, Any]:
    """Handle RPA execution request by publishing to queue and storing in database."""
    # Build minimal message dict with provided fields
    message = {
        "rpa_id": payload_model.rpa_id
    }
    
    if payload_model.callback_url is not None:
        message["callback_url"] = str(payload_model.callback_url)
    
    if payload_model.rpa_request is not None:
        message["rpa_request"] = payload_model.rpa_request
    
    # Store full payload in database
    full_payload = {
        "rpa_id": payload_model.rpa_id,
        "callback_url": str(payload_model.callback_url) if payload_model.callback_url else None,
        "rpa_request": payload_model.rpa_request
    }
    
    try:
        insert_exec_record(full_payload)
    except Exception as e:
        logger.error(f"Database insert failed: {e}")
        # Continue with RabbitMQ even if DB fails
    
    # Publish to RabbitMQ
    publish_json(message)
    
    # Return response data
    return {
        "status": "queued",
        "rpa_id": payload_model.rpa_id,
        "has_callback": payload_model.callback_url is not None
    }
