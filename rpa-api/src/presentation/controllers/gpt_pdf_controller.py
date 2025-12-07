"""GPT PDF controller - Handles GPT Vision extraction and rotation."""
import logging
from typing import Any, Dict

from ...application.services.gpt_pdf_extraction_service import extract_pdf_data
from ...application.services.gpt_pdf_rotation_service import detect_pdf_rotation
from ..dtos.gpt_pdf_extraction_models import GptPdfExtractionInput
from ..dtos.gpt_pdf_rotation_models import GptPdfRotationInput

logger = logging.getLogger(__name__)


def handle_extract_pdf_fields(payload: GptPdfExtractionInput) -> Dict[str, Any]:
    """
    Handle GPT PDF field extraction (rotation handled elsewhere).
    """
    logger.info(
        "Extracting PDF fields from %s with field_map=%s",
        payload.file_path,
        len(payload.field_map) if payload.field_map else 0
    )

    try:
        # Extract data from PDF (assumes PDF is already rotated)
        extracted_data = extract_pdf_data(
            rotated_file_path=payload.file_path,
            field_map=payload.field_map,
        )
        
        # Use output_path if provided, otherwise use input file_path
        organized_file_path = payload.output_path or payload.file_path

        # Handle response format (may include suggested_fields if no field_map was provided)
        if isinstance(extracted_data, dict) and "extracted_data" in extracted_data:
            # Response with suggested_fields
            actual_data = extracted_data.get("extracted_data", {})
            suggested_fields = extracted_data.get("suggested_fields", [])
            extracted_count = len([v for v in actual_data.values() if v])
            logger.info(
                "Extracted %s fields. GPT suggested %s additional fields: %s",
                extracted_count,
                len(suggested_fields),
                suggested_fields
            )
        else:
            # Standard response (when field_map was provided)
            extracted_count = len([v for v in extracted_data.values() if v])
            if payload.field_map:
                logger.info(
                    "Extracted %s of %s requested fields from field_map",
                    extracted_count,
                    len(payload.field_map),
                )
            else:
                logger.info("Extracted %s identifiable fields", extracted_count)

        # Handle response format - may include suggested_fields
        response_data = {
            "status": "SUCCESS",
            "raw_text": None,
            "organized_file_path": organized_file_path,
        }
        
        if isinstance(extracted_data, dict) and "extracted_data" in extracted_data:
            # Response with suggested_fields (when no field_map was provided)
            response_data["extracted"] = extracted_data.get("extracted_data", {})
            response_data["suggested_fields"] = extracted_data.get("suggested_fields", [])
        else:
            # Standard response (when field_map was provided)
            response_data["extracted"] = extracted_data
        
        return response_data
    except FileNotFoundError as exc:
        logger.warning("File not found: %s", exc)
        raise ValueError(f"PDF file not found: {payload.file_path}") from exc
    except RuntimeError as exc:
        logger.error("OpenAI API error: %s", exc)
        raise ValueError(f"OpenAI API call failed: {exc}") from exc
    except Exception as exc:
        logger.error("Unexpected error extracting PDF fields: %s", exc)
        raise ValueError(f"Failed to extract PDF fields: {exc}") from exc


def handle_detect_rotation(payload: GptPdfRotationInput) -> Dict[str, Any]:
    """Handle GPT PDF rotation detection."""
    logger.info("Detecting PDF rotation using GPT Vision")
    
    try:
        result = detect_pdf_rotation(payload.page_image_base64)
        return result
    except RuntimeError as exc:
        logger.error("Rotation detection error: %s", exc)
        raise ValueError(f"Rotation detection failed: {exc}") from exc
    except Exception as exc:
        logger.error("Unexpected error detecting rotation: %s", exc)
        raise ValueError(f"Failed to detect rotation: {exc}") from exc

