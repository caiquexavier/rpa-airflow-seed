"""Service for execution business logic and database operations."""
import json
import logging
from typing import Dict, Optional

from ..libs.postgres import execute_insert, execute_query, execute_update
from ..validations.executions_models import ExecutionStatus

logger = logging.getLogger(__name__)


def create_execution(payload: Dict[str, any]) -> Optional[int]:
    """Create a new execution record and return exec_id."""
    try:
        rpa_key_id = payload.get("rpa_key_id")
        callback_url = payload.get("callback_url")
        rpa_request = payload.get("rpa_request", {})
        
        sql = """
            INSERT INTO rpa_automation_exec 
            (rpa_key_id, callback_url, rpa_request, exec_status, created_at, updated_at)
            VALUES (%s, %s, %s, %s, NOW(), NOW())
            RETURNING exec_id
        """
        
        params = (
            rpa_key_id,
            callback_url,
            json.dumps(rpa_request),  # Serialize dict to JSON string
            ExecutionStatus.PENDING.value
        )
        
        exec_id = execute_insert(sql, params)

        # After obtaining exec_id, update rpa_request to hold the full JSON payload
        if exec_id is not None:
            full_request_payload = {
                "exec_id": exec_id,
                "rpa_key_id": rpa_key_id,
                "callback_url": callback_url,
                "rpa_request": rpa_request,
            }
            update_full_sql = """
                UPDATE rpa_automation_exec
                SET rpa_request = %s,
                    updated_at = NOW()
                WHERE exec_id = %s
            """
            rows = execute_update(update_full_sql, (json.dumps(full_request_payload), exec_id))
            if rows <= 0:
                logger.warning(f"No rows updated when setting full rpa_request for exec_id={exec_id}")

        return exec_id
        
    except Exception as e:
        logger.error(f"Failed to create execution record: {e}")
        raise Exception(f"Failed to create execution record: {str(e)}")


def update_execution_status(exec_id: int, rpa_key_id: str, status: ExecutionStatus,
                          full_update_payload: Dict[str, any], error_message: Optional[str] = None) -> bool:
    """Update execution status and response."""
    try:
        # First verify the execution exists and rpa_key_id matches
        verify_sql = """
            SELECT exec_id, exec_status FROM rpa_automation_exec 
            WHERE exec_id = %s AND rpa_key_id = %s
        """
        result = execute_query(verify_sql, (exec_id, rpa_key_id))
        
        if not result:
            return False
            
        current_status = result[0]["exec_status"]
        
        # Check if already in terminal state
        if current_status in [ExecutionStatus.SUCCESS.value, ExecutionStatus.FAIL.value]:
            # Allow idempotent updates with same status
            if current_status == status.value:
                return True
            else:
                raise ValueError(f"Execution {exec_id} is already in terminal state: {current_status}")
        
        # Update the execution
        update_sql = """
            UPDATE rpa_automation_exec 
            SET exec_status = %s, 
                rpa_response = %s, 
                error_message = %s,
                finished_at = NOW(),
                updated_at = NOW()
            WHERE exec_id = %s AND rpa_key_id = %s
        """
        
        params = (
            status.value,
            json.dumps(full_update_payload),  # Store full update payload
            error_message,
            exec_id,
            rpa_key_id
        )
        
        rows_affected = execute_update(update_sql, params)
        if rows_affected <= 0:
            logger.warning(f"No rows updated for execution {exec_id} when saving full rpa_response")
        return rows_affected > 0
        
    except Exception as e:
        logger.error(f"Failed to update execution {exec_id}: {e}")
        raise Exception(f"Failed to update execution: {str(e)}")


def set_execution_running(exec_id: int) -> bool:
    """Set execution status to RUNNING."""
    try:
        sql = """
            UPDATE rpa_automation_exec 
            SET exec_status = %s, updated_at = NOW()
            WHERE exec_id = %s
        """
        
        params = (ExecutionStatus.RUNNING.value, exec_id)
        rows_affected = execute_update(sql, params)
        return rows_affected > 0
        
    except Exception as e:
        logger.error(f"Failed to set execution {exec_id} to RUNNING: {e}")
        raise Exception(f"Failed to update execution status: {str(e)}")


def get_execution(exec_id: int) -> Optional[Dict[str, any]]:
    """Get execution record by ID."""
    try:
        sql = """
            SELECT exec_id, rpa_key_id, exec_status, rpa_request, rpa_response, 
                   callback_url, created_at, updated_at, finished_at, error_message
            FROM rpa_automation_exec 
            WHERE exec_id = %s
        """
        
        result = execute_query(sql, (exec_id,))
        if not result:
            return None
            
        row = result[0]
        return {
            "exec_id": row["exec_id"],
            "rpa_key_id": row["rpa_key_id"],
            "exec_status": row["exec_status"],
            "rpa_request": row["rpa_request"],
            "rpa_response": row.get("rpa_response"),
            "callback_url": row.get("callback_url"),
            "created_at": row.get("created_at"),
            "updated_at": row.get("updated_at"),
            "finished_at": row.get("finished_at"),
            "error_message": row.get("error_message")
        }
        
    except Exception as e:
        logger.error(f"Failed to get execution {exec_id}: {e}")
        raise Exception(f"Failed to retrieve execution: {str(e)}")
