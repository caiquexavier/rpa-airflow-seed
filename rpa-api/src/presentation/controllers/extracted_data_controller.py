"""ExtractedData controller - Request/response handling."""
import logging
from typing import Dict, Any

from ...application.services.extracted_data_service import (
    create_extracted_metadata,
    read_extracted_metadata,
    read_extracted_metadata_by_saga,
    update_extracted_metadata
)
from ...domain.entities.extracted_data import ExtractedData
from ..dtos.extracted_data_models import (
    CreateExtractedDataRequest,
    UpdateExtractedDataRequest,
    ExtractedDataResponse
)

logger = logging.getLogger(__name__)


def _extracted_data_to_dict(entity: ExtractedData) -> Dict[str, Any]:
    """Convert ExtractedData entity to dictionary."""
    return {
        "id": entity.id,
        "saga_id": entity.saga_id,
        "metadata": entity.metadata,
        "created_at": entity.created_at.isoformat()
    }


def handle_create_extracted_data(payload: CreateExtractedDataRequest) -> Dict[str, Any]:
    """
    Handle create extracted data request.
    
    Args:
        payload: Create request payload
        
    Returns:
        Response dictionary
    """
    record_id = create_extracted_metadata(payload.saga_id, payload.metadata)
    
    if not record_id:
        raise Exception("Failed to create extracted data record")
    
    # Fetch created record to return full data
    created = read_extracted_metadata(record_id)
    if not created:
        raise Exception("Failed to retrieve created extracted data record")
    
    return {
        "id": created.id,
        "saga_id": created.saga_id,
        "metadata": created.metadata,
        "created_at": created.created_at.isoformat(),
        "message": "Extracted data created successfully"
    }


def handle_get_extracted_data(id: int) -> Dict[str, Any]:
    """
    Handle get extracted data request.
    
    Args:
        id: Record ID
        
    Returns:
        Response dictionary
    """
    entity = read_extracted_metadata(id)
    
    if not entity:
        raise ValueError(f"Extracted data with id {id} not found")
    
    return _extracted_data_to_dict(entity)


def handle_get_extracted_data_by_saga(saga_id: int) -> Dict[str, Any]:
    """
    Handle get all extracted data for saga request.
    
    Args:
        saga_id: Parent saga ID
        
    Returns:
        Response dictionary with list of records
    """
    entities = read_extracted_metadata_by_saga(saga_id)
    
    return {
        "saga_id": saga_id,
        "count": len(entities),
        "data": [_extracted_data_to_dict(e) for e in entities]
    }


def handle_update_extracted_data(id: int, payload: UpdateExtractedDataRequest) -> Dict[str, Any]:
    """
    Handle update extracted data request.
    
    Args:
        id: Record ID
        payload: Update request payload
        
    Returns:
        Response dictionary
    """
    updated = update_extracted_metadata(id, payload.metadata)
    
    if not updated:
        raise ValueError(f"Extracted data with id {id} not found or update failed")
    
    # Fetch updated record to return full data
    entity = read_extracted_metadata(id)
    if not entity:
        raise Exception("Failed to retrieve updated extracted data record")
    
    return {
        "id": entity.id,
        "saga_id": entity.saga_id,
        "metadata": entity.metadata,
        "created_at": entity.created_at.isoformat(),
        "message": "Extracted data updated successfully"
    }

