"""Pydantic models for OCR PDF operations."""
from typing import Dict, Optional
from pydantic import BaseModel, Field


class ReadPdfRequest(BaseModel):
    """Request model for reading PDF fields."""
    file_path: str = Field(..., description="Absolute or relative path to the PDF file to process")
    fields: Optional[list[str]] = Field(None, description="List of field names to identify in the document. If not provided, all identified fields will be returned.")


class ReadPdfResponse(BaseModel):
    """Response model for PDF field extraction."""
    fields: Dict[str, Optional[str]] = Field(..., description="Extracted field values, with null for fields not found")
    file_path: str = Field(..., description="Path to the processed PDF file (rotated and saved)")

