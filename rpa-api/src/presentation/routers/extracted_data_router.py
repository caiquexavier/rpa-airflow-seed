"""ExtractedData router - Endpoints for extracted data operations."""
import logging
from typing import Dict, Any

from fastapi import APIRouter, HTTPException

from ..controllers.extracted_data_controller import (
    handle_create_extracted_data,
    handle_get_extracted_data,
    handle_get_extracted_data_by_saga,
    handle_update_extracted_data
)
from ..dtos.extracted_data_models import (
    CreateExtractedDataRequest,
    UpdateExtractedDataRequest
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/extracted-data", tags=["ExtractedData"])


@router.post("/", status_code=201)
async def create_extracted_data(payload: CreateExtractedDataRequest) -> Dict[str, Any]:
    """
    Create a new extracted data record.
    
    Used by Airflow operators to persist GPT-extracted metadata.
    """
    try:
        result = handle_create_extracted_data(payload)
        return result
    except ValueError as e:
        logger.warning(f"Validation error in create_extracted_data: {e}")
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Error in create_extracted_data: {e}")
        raise HTTPException(status_code=500, detail="Internal error")


@router.get("/{id}", status_code=200)
async def get_extracted_data(id: int) -> Dict[str, Any]:
    """
    Get extracted data by ID.
    """
    try:
        result = handle_get_extracted_data(id)
        return result
    except ValueError as e:
        logger.warning(f"Validation error in get_extracted_data: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error in get_extracted_data: {e}")
        raise HTTPException(status_code=500, detail="Internal error")


@router.get("/by-saga/{saga_id}", status_code=200)
async def get_extracted_data_by_saga(saga_id: int) -> Dict[str, Any]:
    """
    Get all extracted data records for a saga.
    """
    try:
        result = handle_get_extracted_data_by_saga(saga_id)
        return result
    except Exception as e:
        logger.error(f"Error in get_extracted_data_by_saga: {e}")
        raise HTTPException(status_code=500, detail="Internal error")


@router.put("/{id}", status_code=200)
async def update_extracted_data(id: int, payload: UpdateExtractedDataRequest) -> Dict[str, Any]:
    """
    Update extracted data metadata.
    """
    try:
        result = handle_update_extracted_data(id, payload)
        return result
    except ValueError as e:
        logger.warning(f"Validation error in update_extracted_data: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error in update_extracted_data: {e}")
        raise HTTPException(status_code=500, detail="Internal error")

