"""Pydantic models for GPT PDF rotation operations."""
from typing import Literal
from pydantic import BaseModel, Field, constr


class GptPdfRotationInput(BaseModel):
    """Request model for GPT PDF rotation detection."""
    
    page_image_base64: constr(strip_whitespace=True, min_length=1) = Field(
        ..., description="Base64-encoded image of the PDF page to analyze for rotation"
    )


class GptPdfRotationOutput(BaseModel):
    """Response model for GPT PDF rotation detection."""
    
    rotation: int = Field(
        ..., 
        description="Rotation angle in degrees (0, 90, 180, or 270)", 
        ge=0, 
        le=270
    )
    confidence: float = Field(
        ..., 
        description="Confidence score between 0 and 100", 
        ge=0, 
        le=100
    )
    reasoning: str = Field(
        ..., 
        description="Brief explanation of the rotation detection"
    )

