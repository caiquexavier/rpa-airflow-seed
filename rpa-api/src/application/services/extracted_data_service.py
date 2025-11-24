"""ExtractedData service - Use case layer for extracted data operations."""
import logging
from typing import Optional, List, Dict, Any

from ...domain.entities.extracted_data import ExtractedData
from ...infrastructure.repositories.extracted_data_repository import (
    create_extracted_data,
    get_extracted_data,
    get_all_extracted_data_for_saga,
    update_extracted_data
)

logger = logging.getLogger(__name__)


def create_extracted_metadata(saga_id: int, metadata: Dict[str, Any]) -> int:
    """
    Create new extracted metadata record.
    
    Pure function - delegates to repository.
    
    Args:
        saga_id: Parent saga ID
        metadata: JSON metadata dictionary
        
    Returns:
        Created record ID
        
    Raises:
        ValueError: If saga_id is invalid or metadata is empty
    """
    if not saga_id or saga_id <= 0:
        raise ValueError("saga_id must be a positive integer")
    
    if not metadata:
        raise ValueError("metadata cannot be empty")
    
    return create_extracted_data(saga_id, metadata)


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

