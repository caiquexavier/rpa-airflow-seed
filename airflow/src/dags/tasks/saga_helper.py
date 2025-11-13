"""SAGA helper utilities for DAG tasks."""
import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


def get_saga_from_context(context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Get SAGA from XCom, trying multiple keys.
    
    Returns:
        SAGA dict or None
    """
    ti = context.get('task_instance')
    if not ti:
        return None
    
    # Try to get SAGA from various XCom keys
    saga = ti.xcom_pull(key='saga', default=None)
    if saga:
        return saga
    
    # Try from rpa_payload (backward compatibility)
    rpa_payload = ti.xcom_pull(key='rpa_payload', default=None)
    if rpa_payload and isinstance(rpa_payload, dict) and 'rpa_key_id' in rpa_payload:
        return rpa_payload
    
    # Try from webhook_data
    webhook_data = ti.xcom_pull(key='webhook_data', default=None)
    if webhook_data and isinstance(webhook_data, dict):
        if 'saga' in webhook_data:
            return webhook_data['saga']
        # If webhook_data itself is a SAGA-like structure
        if 'rpa_key_id' in webhook_data and 'rpa_request' in webhook_data:
            return webhook_data
    
    return None


def log_saga(saga: Optional[Dict[str, Any]], task_id: str = None) -> None:
    """
    Log SAGA as INFO level.
    
    Args:
        saga: SAGA dictionary
        task_id: Optional task ID for context
    """
    if saga:
        task_prefix = f"[{task_id}] " if task_id else ""
        logger.info(f"{task_prefix}SAGA: {json.dumps(saga, indent=2, ensure_ascii=False)}")
    else:
        logger.warning(f"SAGA not found for logging")


def get_saga_rpa_key_id(saga: Optional[Dict[str, Any]]) -> Optional[str]:
    """Get rpa_key_id from SAGA."""
    if saga and isinstance(saga, dict):
        return saga.get('rpa_key_id')
    return None


def get_saga_rpa_request(saga: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Get rpa_request from SAGA."""
    if saga and isinstance(saga, dict):
        return saga.get('rpa_request')
    return None

