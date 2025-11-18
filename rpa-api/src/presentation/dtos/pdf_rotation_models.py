"""Pydantic models for PDF rotation operations."""
from pydantic import BaseModel, constr, Field


class PdfRotationInput(BaseModel):
    """Request model for PDF rotation."""

    file_path: constr(strip_whitespace=True, min_length=1) = Field(
        ..., description="Absolute or relative path to the PDF file to rotate"
    )


class PdfRotationOutput(BaseModel):
    """Response model for PDF rotation."""

    file_path: str = Field(..., description="Path to the rotated PDF file")
    success: bool = Field(..., description="Whether rotation was successful")

