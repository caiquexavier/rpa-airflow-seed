"""ExtractedData repository - Database implementation."""
import json
import logging
from typing import Optional, List
from datetime import datetime

from ...domain.entities.extracted_data import ExtractedData
from ..adapters.postgres import execute_insert, execute_query, execute_update

logger = logging.getLogger(__name__)


def create_extracted_data(saga_id: int, metadata: dict) -> int:
    """
    Create new extracted data record.
    
    Args:
        saga_id: Parent saga ID
        metadata: JSON metadata dictionary
        
    Returns:
        Created record ID
    """
    sql = """
        INSERT INTO rpa_extracted_data 
        (saga_id, metadata)
        VALUES (%s, %s)
        RETURNING id
    """
    params = (
        saga_id,
        json.dumps(metadata)
    )
    result = execute_insert(sql, params)
    if result:
        # execute_insert may return dict or int
        if isinstance(result, dict):
            # Try "id" first (our column name), then fallback to first value
            return result.get("id") or next(iter(result.values()))
        return result
    return 0


def get_extracted_data(id: int) -> Optional[ExtractedData]:
    """
    Get extracted data by ID.
    
    Args:
        id: Record ID
        
    Returns:
        ExtractedData or None
    """
    sql = """
        SELECT id, saga_id, metadata, created_at
        FROM rpa_extracted_data
        WHERE id = %s
    """
    result = execute_query(sql, (id,))
    
    if not result:
        return None
    
    return _row_to_extracted_data(result[0])


def get_all_extracted_data_for_saga(saga_id: int) -> List[ExtractedData]:
    """
    Get all extracted data records for a saga.
    
    Args:
        saga_id: Parent saga ID
        
    Returns:
        List of ExtractedData
    """
    sql = """
        SELECT id, saga_id, metadata, created_at
        FROM rpa_extracted_data
        WHERE saga_id = %s
        ORDER BY created_at ASC
    """
    result = execute_query(sql, (saga_id,))
    
    return [_row_to_extracted_data(row) for row in result]


def update_extracted_data(id: int, metadata: dict) -> bool:
    """
    Update extracted data metadata.
    
    Args:
        id: Record ID
        metadata: Updated JSON metadata dictionary
        
    Returns:
        True if updated, False otherwise
    """
    sql = """
        UPDATE rpa_extracted_data 
        SET metadata = %s
        WHERE id = %s
    """
    params = (
        json.dumps(metadata),
        id
    )
    affected_rows = execute_update(sql, params)
    return affected_rows > 0


def _row_to_extracted_data(row: dict) -> ExtractedData:
    """Convert database row to ExtractedData entity."""
    # Parse JSONB field
    metadata = row.get("metadata")
    if isinstance(metadata, str):
        metadata = json.loads(metadata)
    
    return ExtractedData(
        id=row["id"],
        saga_id=row["saga_id"],
        metadata=metadata,
        created_at=row["created_at"]
    )

