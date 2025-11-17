"""OCR PDF router - Endpoints for OCR PDF operations."""
import logging
from typing import Dict, Any

from fastapi import APIRouter, HTTPException

from ..controllers.ocr_pdf_controller import handle_read_pdf
from ..dtos.ocr_pdf_models import ReadPdfRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ocr/pdf", tags=["OCR PDF"])


@router.post("/read", status_code=200)
async def read_pdf(payload: ReadPdfRequest) -> Dict[str, Any]:
    """
    Read PDF and extract requested fields using OCR.
    
    Processes PDF file, rotates pages to readable orientation,
    performs OCR, and extracts requested field values.
    """
    try:
        result = handle_read_pdf(payload)
        return result
    except ValueError as e:
        logger.warning(f"Validation error in read_pdf: {e}")
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Error in read_pdf: {e}")
        raise HTTPException(status_code=500, detail="Internal error")

