"""Service for rpa_automation_exec table operations."""
import json
import logging
from typing import Dict, Optional

from ..libs.postgres import execute_insert

logger = logging.getLogger(__name__)


def insert(payload: Dict[str, any]) -> Optional[int]:
    """Insert a new RPA automation execution record."""
    try:
        # Use default definition_id since rpa_id is a string and definition_id expects bigint
        definition_id = 1  # Default definition ID
        callback_url = payload.get("callback_url")
        request_json = json.dumps(payload)  # Store full input JSON
        
        sql = """
            INSERT INTO rpa_automation_exec 
            (definition_id, exec_status, current_step, request, callback_url)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING exec_id
        """
        
        params = (
            definition_id,
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
