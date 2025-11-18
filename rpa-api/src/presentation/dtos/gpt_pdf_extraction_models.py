"""Pydantic models for GPT PDF extraction operations."""
from typing import Dict, Optional, List, Literal
from pydantic import BaseModel, constr, Field


class GptPdfExtractionInput(BaseModel):
    """Request model for GPT PDF extraction."""

    file_path: constr(strip_whitespace=True, min_length=1) = Field(
        ..., description="Absolute or relative path to the PDF file to process"
    )
    fields: Optional[List[constr(strip_whitespace=True, min_length=1)]] = Field(
        None, description="List of field names to extract from the document. If None or empty, extracts all identifiable fields."
    )


class GptPdfExtractionOutput(BaseModel):
    """Response model for GPT PDF field extraction."""

    status: Literal["SUCCESS", "FAIL"] = Field(..., description="Status of the extraction")
    extracted: Dict[str, Optional[str]] = Field(
        ..., description="Extracted field values, with null for fields not found"
    )
    raw_text: Optional[str] = Field(
        None, description="Full extracted text from PDF (optional, may be large)"
    )

