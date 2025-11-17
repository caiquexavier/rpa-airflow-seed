"""OCR PDF controller - Handles OCR PDF operations."""
import logging
from typing import Dict, Optional, Any

from ...application.services.ocr_pdf_service import read_pdf_fields
from ..dtos.ocr_pdf_models import ReadPdfRequest

logger = logging.getLogger(__name__)


def handle_read_pdf(payload: ReadPdfRequest) -> Dict[str, Any]:
    """
    Handle PDF field extraction - pure function.
    
    Extracts requested fields from PDF using OCR.
    If fields parameter is not provided, extracts all identifiable fields.
    """
    fields_info = payload.fields if payload.fields else "all fields"
    logger.info(f"Reading PDF fields from {payload.file_path} for fields: {fields_info}")
    
    try:
        result = read_pdf_fields(
            file_path=payload.file_path,
            fields=payload.fields
        )
        
        extracted_count = len([v for v in result.get("fields", {}).values() if v])
        logger.info(f"Extracted {extracted_count} fields from PDF")
        
        return result
    except FileNotFoundError as e:
        logger.warning(f"File not found: {e}")
        raise ValueError(f"PDF file not found: {payload.file_path}")
    except RuntimeError as e:
        logger.error(f"OCR error: {e}")
        raise ValueError(f"OCR processing failed: {e}")
    except Exception as e:
        logger.error(f"Unexpected error reading PDF: {e}")
        raise ValueError(f"Failed to read PDF: {e}")

