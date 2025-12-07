"""GPT PDF router - GPT Vision extraction and rotation endpoints."""
import logging

from fastapi import APIRouter

from ..controllers.gpt_pdf_controller import handle_extract_pdf_fields, handle_detect_rotation
from ..dtos.gpt_pdf_extraction_models import (
    GptPdfExtractionInput, GptPdfExtractionOutput
)
from ..dtos.gpt_pdf_rotation_models import (
    GptPdfRotationInput, GptPdfRotationOutput
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/rpa/pdf", tags=["GPT PDF"])


@router.post("/extract-gpt", response_model=GptPdfExtractionOutput, status_code=200)
async def extract_pdf_fields_endpoint(payload: GptPdfExtractionInput) -> GptPdfExtractionOutput:
    """Extract fields from a (pre-rotated) PDF using GPT Vision."""
    try:
        result = handle_extract_pdf_fields(payload)
        return GptPdfExtractionOutput(**result)
    except ValueError as exc:
        logger.warning("Validation error in extract_pdf_fields: %s", exc)
        return GptPdfExtractionOutput(status="FAIL", extracted={}, raw_text=None)
    except Exception as exc:
        logger.error("Error in extract_pdf_fields: %s", exc)
        return GptPdfExtractionOutput(status="FAIL", extracted={}, raw_text=None)


@router.post("/detect-rotation", response_model=GptPdfRotationOutput, status_code=200)
async def detect_rotation_endpoint(payload: GptPdfRotationInput) -> GptPdfRotationOutput:
    """Detect PDF page rotation/orientation using GPT Vision. Prefers landscape orientation."""
    try:
        result = handle_detect_rotation(payload)
        return GptPdfRotationOutput(**result)
    except ValueError as exc:
        logger.warning("Validation error in detect_rotation: %s", exc)
        return GptPdfRotationOutput(rotation=0, confidence=0, reasoning=str(exc))
    except Exception as exc:
        logger.error("Error in detect_rotation: %s", exc)
        return GptPdfRotationOutput(rotation=0, confidence=0, reasoning=f"Error: {str(exc)}")
