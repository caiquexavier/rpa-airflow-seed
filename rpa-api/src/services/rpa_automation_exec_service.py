"""Service for rpa_automation_exec table operations."""
import json
import logging
from typing import Dict, Optional

from ..libs.postgres import execute_insert

logger = logging.getLogger(__name__)


def insert(payload: Dict[str, any]) -> Optional[int]:
    """Insert a new RPA automation execution record."""
    try:
        rpa_key_id = payload.get("rpa_key_id") or payload.get("rpa_id")
        callback_url = payload.get("callback_url")
        request_json = json.dumps(payload)  # Store full input JSON
        
        sql = """
            INSERT INTO rpa_automation_exec 
            (rpa_key_id, exec_status, current_step, request, callback_url)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING exec_id
        """
        
        params = (
            rpa_key_id,
            "RECEIVED",  # exec_status
            "REQUESTED",  # current_step
            request_json,  # request (full JSON)
            callback_url
        )
        
        exec_id = execute_insert(sql, params)
        return exec_id
        
    except Exception as e:
        logger.error(f"Failed to insert RPA automation exec record: {e}")
        raise Exception(f"Failed to store RPA execution request: {str(e)}")
