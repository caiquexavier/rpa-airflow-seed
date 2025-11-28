"""Pydantic models for GPT PDF extraction operations."""
from typing import Dict, Optional, List, Literal
from pydantic import BaseModel, constr, Field


class GptPdfExtractionInput(BaseModel):
    """Request model for GPT PDF extraction."""

    file_path: constr(strip_whitespace=True, min_length=1) = Field(
        ..., description="Absolute path to the PDF file to process"
    )
    output_path: Optional[constr(strip_whitespace=True, min_length=1)] = Field(
        None,
        description="Optional path used when copying/renaming the processed PDF (e.g., /opt/airflow/data/processado/XYZ.pdf)",
    )
    field_map: Optional[Dict[str, str]] = Field(
        None,
        description=(
            "JSON model mapping field names to descriptions/instructions. "
            "Example: {'cnpj': 'Brazilian company registration number (CNPJ)', 'valor_total': 'Total invoice amount'}. "
            "If provided, GPT will use this map as a guide to locate and extract these specific fields from the document images. "
            "If None or empty, GPT will identify and suggest all fields it finds in the document."
        ),
    )


class GptPdfExtractionOutput(BaseModel):
    """Response model for GPT PDF field extraction."""

    status: Literal["SUCCESS", "FAIL"] = Field(..., description="Status of the extraction")
    extracted: Dict[str, Optional[str]] = Field(
        ..., description="Extracted field values, with null for fields not found"
    )
    suggested_fields: Optional[List[str]] = Field(
        None,
        description=(
            "List of field names suggested by GPT when no field_map was provided. "
            "This helps understand what fields are available in this document type."
        ),
    )
    raw_text: Optional[str] = Field(
        None, description="Full extracted text from PDF (optional, may be large)"
    )
    organized_file_path: Optional[str] = Field(
        None,
        description="Absolute path to the renamed/copied PDF (if available)",
    )


class GptPdfRotationInput(BaseModel):
    """Request model for GPT PDF rotation detection."""
    
    page_image_base64: constr(strip_whitespace=True, min_length=1) = Field(
        ..., description="Base64-encoded image of the PDF page to analyze"
    )


class GptPdfRotationOutput(BaseModel):
    """Response model for GPT PDF rotation detection."""
    
    rotation: int = Field(..., description="Rotation angle in degrees (0, 90, 180, or 270)", ge=0, le=270)
    confidence: float = Field(..., description="Confidence score between 0 and 100", ge=0, le=100)
    reasoning: str = Field(..., description="Brief explanation of the rotation detection")
