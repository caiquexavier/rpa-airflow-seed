"""Execution repository - Database implementation."""
import json
import logging
from typing import Optional
from datetime import datetime

from ...domain.entities.execution import Execution, ExecutionStatus
from ..adapters.postgres import execute_insert, execute_query, execute_update

logger = logging.getLogger(__name__)


def save_execution(execution: Execution) -> int:
    """
    Save execution to database (Command side).
    
    Returns:
        exec_id
    """
    if execution.exec_id == 0:
        # Insert new execution
        sql = """
            INSERT INTO rpa_automation_exec 
            (rpa_key_id, callback_url, rpa_request, exec_status, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING exec_id
        """
        params = (
            execution.rpa_key_id,
            execution.callback_url,
            json.dumps(execution.rpa_request) if execution.rpa_request else None,
            execution.exec_status.value,
            execution.created_at,
            execution.updated_at
        )
        exec_id = execute_insert(sql, params)
        return exec_id if exec_id else 0
    else:
        # Update existing execution
        sql = """
            UPDATE rpa_automation_exec 
            SET exec_status = %s,
                rpa_response = %s,
                error_message = %s,
                finished_at = %s,
                updated_at = %s
            WHERE exec_id = %s
        """
        params = (
            execution.exec_status.value,
            json.dumps(execution.rpa_response) if execution.rpa_response else None,
            execution.error_message,
            execution.finished_at,
            execution.updated_at,
            execution.exec_id
        )
        execute_update(sql, params)
        return execution.exec_id


def get_execution(exec_id: int) -> Optional[Execution]:
    """
    Get execution from database (Query side - uses read model).
    
    Returns:
        Execution or None
    """
    sql = """
        SELECT exec_id, rpa_key_id, exec_status, rpa_request, rpa_response,
               callback_url, created_at, updated_at, finished_at, error_message
        FROM execution_read_model
        WHERE exec_id = %s
    """
    result = execute_query(sql, (exec_id,))
    
    if not result:
        return None
    
    row = result[0]
    
    # Parse JSON fields
    rpa_request = row.get("rpa_request")
    if isinstance(rpa_request, str):
        rpa_request = json.loads(rpa_request)
    
    rpa_response = row.get("rpa_response")
    if isinstance(rpa_response, str):
        rpa_response = json.loads(rpa_response)
    
    return Execution(
        exec_id=row["exec_id"],
        rpa_key_id=row["rpa_key_id"],
        exec_status=ExecutionStatus(row["exec_status"]),
        rpa_request=rpa_request,
        rpa_response=rpa_response,
        error_message=row.get("error_message"),
        callback_url=row.get("callback_url"),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        finished_at=row.get("finished_at")
    )


def set_execution_running(exec_id: int) -> bool:
    """Set execution status to RUNNING."""
    sql = """
        UPDATE rpa_automation_exec 
        SET exec_status = %s, updated_at = NOW()
        WHERE exec_id = %s
    """
    rows_affected = execute_update(sql, (ExecutionStatus.RUNNING.value, exec_id))
    return rows_affected > 0

