"""GPT PDF controller - Unified controller for PDF rotation and extraction using GPT."""
import logging
from typing import Dict, Any

from ...application.services.gpt_pdf_service import gpt_pdf_extractor
from ..dtos.gpt_pdf_rotate_extract_models import GptPdfRotateExtractInput
from ..dtos.gpt_pdf_extraction_models import GptPdfExtractionInput
from ..dtos.pdf_rotation_models import PdfRotationInput

logger = logging.getLogger(__name__)


def handle_rotate_and_extract_pdf(payload: GptPdfRotateExtractInput) -> Dict[str, Any]:
    """
    Handle GPT PDF rotation and extraction - pure function.

    Rotates PDF to readable position and extracts all data using GPT in a single operation.
    """
    logger.info(f"Rotating and extracting data from PDF: {payload.file_path}")

    try:
        # Call unified service
        rotated_file_path, extracted_data = gpt_pdf_extractor(
            file_path=payload.file_path,
            output_path=payload.output_path,
            fields=payload.fields
        )

        extracted_count = len([v for v in extracted_data.values() if v])
        if payload.fields:
            logger.info(f"Extracted {extracted_count} of {len(payload.fields)} requested fields")
        else:
            logger.info(f"Extracted {extracted_count} identifiable fields")

        return {
            "status": "SUCCESS",
            "rotated_file_path": rotated_file_path,
            "extracted_data": extracted_data
        }
    except FileNotFoundError as e:
        logger.warning(f"File not found: {e}")
        raise ValueError(f"PDF file not found: {payload.file_path}")
    except RuntimeError as e:
        logger.error(f"Processing error: {e}")
        raise ValueError(f"PDF processing failed: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise ValueError(f"Failed to process PDF: {e}")


def handle_extract_pdf_fields(payload: GptPdfExtractionInput) -> Dict[str, Any]:
    """
    Handle GPT PDF field extraction - pure function.

    Extracts requested fields from PDF using unified GPT service (rotates and extracts).
    """
    logger.info(f"Extracting PDF fields from {payload.file_path} for fields: {payload.fields}")

    try:
        # Use unified GPT service (rotates and extracts)
        rotated_file_path, extracted_data = gpt_pdf_extractor(
            file_path=payload.file_path,
            output_path=None,  # Overwrite original with rotated version
            fields=payload.fields if payload.fields else None
        )

        extracted_count = len([v for v in extracted_data.values() if v])
        if payload.fields:
            logger.info(f"Extracted {extracted_count} of {len(payload.fields)} requested fields from PDF")
        else:
            logger.info(f"Extracted {extracted_count} identifiable fields from PDF")

        return {
            "status": "SUCCESS",
            "extracted": extracted_data,
            "raw_text": None  # Not returned by unified service
        }
    except FileNotFoundError as e:
        logger.warning(f"File not found: {e}")
        raise ValueError(f"PDF file not found: {payload.file_path}")
    except RuntimeError as e:
        logger.error(f"OpenAI API error: {e}")
        raise ValueError(f"OpenAI API call failed: {e}")
    except Exception as e:
        logger.error(f"Unexpected error extracting PDF fields: {e}")
        raise ValueError(f"Failed to extract PDF fields: {e}")


def handle_rotate_pdf(payload: PdfRotationInput) -> Dict[str, Any]:
    """
    Handle PDF rotation - pure function.

    Rotates PDF to readable position using GPT service (rotation only, no extraction).
    """
    logger.info(f"Rotating PDF using GPT: {payload.file_path}")

    try:
        # Use unified GPT service (extract empty fields to get rotation only)
        rotated_file_path, _ = gpt_pdf_extractor(
            file_path=payload.file_path,
            output_path=None,  # Overwrite original
            fields=[]  # Empty fields list - just rotate, don't extract
        )

        logger.info(f"Successfully rotated PDF: {rotated_file_path}")

        return {
            "file_path": rotated_file_path,
            "success": True
        }
    except FileNotFoundError as e:
        logger.warning(f"File not found: {e}")
        raise ValueError(f"PDF file not found: {payload.file_path}")
    except RuntimeError as e:
        logger.error(f"PDF rotation error: {e}")
        raise ValueError(f"PDF rotation failed: {e}")
    except Exception as e:
        logger.error(f"Unexpected error rotating PDF: {e}")
        raise ValueError(f"Failed to rotate PDF: {e}")

