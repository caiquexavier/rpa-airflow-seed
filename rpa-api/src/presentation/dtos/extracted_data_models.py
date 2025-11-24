"""Pydantic models for ExtractedData operations."""
from typing import Any, Dict, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class CreateExtractedDataRequest(BaseModel):
    """Request model for creating extracted data."""
    saga_id: int = Field(..., description="Parent saga ID", gt=0)
    metadata: Dict[str, Any] = Field(..., description="Extracted JSON metadata")


class UpdateExtractedDataRequest(BaseModel):
    """Request model for updating extracted data."""
    metadata: Dict[str, Any] = Field(..., description="Updated JSON metadata")


class ExtractedDataResponse(BaseModel):
    """Response model for extracted data operations."""
    id: int = Field(..., description="Record ID")
    saga_id: int = Field(..., description="Parent saga ID")
    metadata: Dict[str, Any] = Field(..., description="Extracted JSON metadata")
    created_at: datetime = Field(..., description="Creation timestamp")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

