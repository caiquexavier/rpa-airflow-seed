"""GPT PDF router - Unified endpoints for PDF rotation and extraction using GPT."""
import logging
from typing import Dict, Any

from fastapi import APIRouter

from ..controllers.gpt_pdf_controller import (
    handle_rotate_and_extract_pdf,
    handle_extract_pdf_fields,
    handle_rotate_pdf
)
from ..dtos.gpt_pdf_rotate_extract_models import GptPdfRotateExtractInput, GptPdfRotateExtractOutput
from ..dtos.gpt_pdf_extraction_models import GptPdfExtractionInput, GptPdfExtractionOutput
from ..dtos.pdf_rotation_models import PdfRotationInput, PdfRotationOutput

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/rpa/pdf", tags=["GPT PDF"])


@router.post("/rotate-and-extract", response_model=GptPdfRotateExtractOutput, status_code=200)
async def rotate_and_extract_pdf_endpoint(payload: GptPdfRotateExtractInput) -> GptPdfRotateExtractOutput:
    """
    Rotate PDF to readable position and extract all data using GPT in a single operation.

    This endpoint:
    1. Tests different rotations (0°, 90°, 180°, 270°)
    2. Uses GPT to determine the best rotation AND extract all identifiable data in one prompt
    3. Applies the rotation to the PDF
    4. Saves the rotated PDF to output_path (or overwrites original if not specified)
    5. Returns the rotated file path and extracted JSON data
    """
    try:
        result = handle_rotate_and_extract_pdf(payload)
        return GptPdfRotateExtractOutput(**result)
    except ValueError as e:
        logger.warning(f"Validation error in rotate_and_extract_pdf: {e}")
        return GptPdfRotateExtractOutput(
            status="FAIL",
            rotated_file_path=payload.file_path,
            extracted_data={}
        )
    except Exception as e:
        logger.error(f"Error in rotate_and_extract_pdf: {e}")
        return GptPdfRotateExtractOutput(
            status="FAIL",
            rotated_file_path=payload.file_path,
            extracted_data={}
        )


@router.post("/extract-gpt", response_model=GptPdfExtractionOutput, status_code=200)
async def extract_pdf_fields_endpoint(payload: GptPdfExtractionInput) -> GptPdfExtractionOutput:
    """
    Extract fields from PDF using GPT (with rotation).

    Processes PDF file, rotates it if needed, and uses GPT to extract requested fields.
    """
    try:
        result = handle_extract_pdf_fields(payload)
        return GptPdfExtractionOutput(**result)
    except ValueError as e:
        logger.warning(f"Validation error in extract_pdf_fields: {e}")
        return GptPdfExtractionOutput(
            status="FAIL",
            extracted={},
            raw_text=None
        )
    except Exception as e:
        logger.error(f"Error in extract_pdf_fields: {e}")
        return GptPdfExtractionOutput(
            status="FAIL",
            extracted={},
            raw_text=None
        )


@router.post("/rotate", response_model=PdfRotationOutput, status_code=200)
async def rotate_pdf_endpoint(payload: PdfRotationInput) -> PdfRotationOutput:
    """
    Rotate PDF to readable position.

    Detects the correct rotation using GPT to analyze text at different rotations,
    then rotates all pages and saves the file.
    """
    try:
        result = handle_rotate_pdf(payload)
        return PdfRotationOutput(**result)
    except ValueError as e:
        logger.warning(f"Validation error in rotate_pdf: {e}")
        return PdfRotationOutput(
            file_path=payload.file_path,
            success=False
        )
    except Exception as e:
        logger.error(f"Error in rotate_pdf: {e}")
        return PdfRotationOutput(
            file_path=payload.file_path,
            success=False
        )

