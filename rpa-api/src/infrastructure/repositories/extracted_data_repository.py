"""ExtractedData repository - Database implementation."""
import json
import logging
from typing import Optional, List
from datetime import datetime

from ...domain.entities.extracted_data import ExtractedData
from ..adapters.postgres import execute_insert, execute_query, execute_update

logger = logging.getLogger(__name__)


def create_extracted_data(saga_id: int, metadata: dict, identifier: Optional[str] = None, identifier_code: Optional[str] = None) -> int:
    """
    Create new extracted data record.
    
    Args:
        saga_id: Parent saga ID
        metadata: JSON metadata dictionary
        identifier: Identifier type (e.g., "NF-E")
        identifier_code: Identifier code (e.g., nf_e number)
        
    Returns:
        Created record ID
        
    Raises:
        ValueError: If record with same saga_id and identifier_code already exists
    """
    sql = """
        INSERT INTO rpa_extracted_data 
        (saga_id, identifier, identifier_code, metadata)
        VALUES (%s, %s, %s, %s)
        RETURNING id
    """
    params = (
        saga_id,
        identifier,
        identifier_code,
        json.dumps(metadata)
    )
    try:
        result = execute_insert(sql, params)
        if result:
            # execute_insert may return dict or int
            if isinstance(result, dict):
                # Try "id" first (our column name), then fallback to first value
                return result.get("id") or next(iter(result.values()))
            return result
        return 0
    except Exception as e:
        # Check if it's a unique constraint violation
        error_msg = str(e).lower()
        if "unique" in error_msg or "duplicate" in error_msg:
            raise ValueError(f"Record with saga_id={saga_id} and identifier_code={identifier_code} already exists")
        raise


def get_extracted_data(id: int) -> Optional[ExtractedData]:
    """
    Get extracted data by ID.
    
    Args:
        id: Record ID
        
    Returns:
        ExtractedData or None
    """
    sql = """
        SELECT id, saga_id, identifier, identifier_code, metadata, created_at
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
        SELECT id, saga_id, identifier, identifier_code, metadata, created_at
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


def get_extracted_data_by_saga_and_identifier_code(saga_id: int, identifier_code: str) -> Optional[ExtractedData]:
    """
    Get extracted data by saga_id and identifier_code.
    
    Args:
        saga_id: Parent saga ID
        identifier_code: Identifier code (e.g., nf_e number)
        
    Returns:
        ExtractedData or None
    """
    sql = """
        SELECT id, saga_id, identifier, identifier_code, metadata, created_at
        FROM rpa_extracted_data
        WHERE saga_id = %s AND identifier_code = %s
    """
    result = execute_query(sql, (saga_id, identifier_code))
    
    if not result:
        return None
    
    return _row_to_extracted_data(result[0])


def _row_to_extracted_data(row: dict) -> ExtractedData:
    """Convert database row to ExtractedData entity."""
    # Parse JSONB field
    metadata = row.get("metadata")
    if isinstance(metadata, str):
        metadata = json.loads(metadata)
    
    return ExtractedData(
        id=row["id"],
        saga_id=row["saga_id"],
        identifier=row.get("identifier"),
        identifier_code=row.get("identifier_code"),
        metadata=metadata,
        created_at=row["created_at"]
    )

