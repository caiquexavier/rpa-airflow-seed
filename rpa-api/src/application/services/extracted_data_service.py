"""ExtractedData service - Use case layer for extracted data operations."""
import logging
from typing import Optional, List, Dict, Any

from ...domain.entities.extracted_data import ExtractedData
from ...infrastructure.repositories.extracted_data_repository import (
    create_extracted_data,
    get_extracted_data,
    get_all_extracted_data_for_saga,
    update_extracted_data,
    get_extracted_data_by_saga_and_identifier_code
)

logger = logging.getLogger(__name__)


def create_extracted_metadata(
    saga_id: int, 
    metadata: Dict[str, Any], 
    identifier: Optional[str] = None, 
    identifier_code: Optional[str] = None
) -> int:
    """
    Create new extracted metadata record.
    
    Pure function - delegates to repository.
    
    Args:
        saga_id: Parent saga ID
        metadata: JSON metadata dictionary
        identifier: Identifier type (e.g., "NF-E")
        identifier_code: Identifier code (e.g., nf_e number)
        
    Returns:
        Created record ID
        
    Raises:
        ValueError: If saga_id is invalid, metadata is empty, or record already exists
    """
    if not saga_id or saga_id <= 0:
        raise ValueError("saga_id must be a positive integer")
    
    if not metadata:
        raise ValueError("metadata cannot be empty")
    
    # Check if record already exists (if identifier_code is provided)
    if identifier_code:
        existing = get_extracted_data_by_saga_and_identifier_code(saga_id, identifier_code)
        if existing:
            raise ValueError(f"Record with saga_id={saga_id} and identifier_code={identifier_code} already exists")
    
    return create_extracted_data(saga_id, metadata, identifier, identifier_code)


def read_extracted_metadata(id: int) -> Optional[ExtractedData]:
    """
    Read extracted metadata by ID.
    
    Pure function - delegates to repository.
    
    Args:
        id: Record ID
        
    Returns:
        ExtractedData or None
    """
    if not id or id <= 0:
        return None
    
    return get_extracted_data(id)


def read_extracted_metadata_by_saga(saga_id: int) -> List[ExtractedData]:
    """
    Read all extracted metadata for a saga.
    
    Pure function - delegates to repository.
    
    Args:
        saga_id: Parent saga ID
        
    Returns:
        List of ExtractedData
    """
    if not saga_id or saga_id <= 0:
        return []
    
    return get_all_extracted_data_for_saga(saga_id)


def update_extracted_metadata(id: int, metadata: Dict[str, Any]) -> bool:
    """
    Update extracted metadata.
    
    Pure function - delegates to repository.
    
    Args:
        id: Record ID
        metadata: Updated JSON metadata dictionary
        
    Returns:
        True if updated, False otherwise
        
    Raises:
        ValueError: If metadata is empty
    """
    if not id or id <= 0:
        return False
    
    if not metadata:
        raise ValueError("metadata cannot be empty")
    
    return update_extracted_data(id, metadata)

