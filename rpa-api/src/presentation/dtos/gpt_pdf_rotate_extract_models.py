"""Pydantic models for GPT PDF rotate and extract operations."""
from typing import Dict, Optional, List
from pydantic import BaseModel, constr, Field


class GptPdfRotateExtractInput(BaseModel):
    """Request model for GPT PDF rotation and extraction."""

    file_path: constr(strip_whitespace=True, min_length=1) = Field(
        ..., description="Absolute or relative path to the PDF file to process"
    )
    output_path: Optional[constr(strip_whitespace=True, min_length=1)] = Field(
        None, description="Optional path to save rotated PDF. If None, overwrites original file."
    )
    fields: Optional[List[constr(strip_whitespace=True, min_length=1)]] = Field(
        None, description="List of field names to extract. If None or empty, extracts all identifiable fields."
    )


class GptPdfRotateExtractOutput(BaseModel):
    """Response model for GPT PDF rotation and extraction."""

    status: str = Field(..., description="Status of the operation")
    rotated_file_path: str = Field(..., description="Path to the rotated PDF file")
    extracted_data: Dict[str, Optional[str]] = Field(
        ..., description="All extracted field values as JSON object"
    )

