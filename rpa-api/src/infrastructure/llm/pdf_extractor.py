"""PDF extraction using OpenAI Vision - extracts fields from PDF images."""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

from .openai_client import get_openai_client, get_openai_model
from .prompts import (
    get_vision_system_message,
    build_vision_field_map_instruction,
    build_vision_suggest_fields_instruction,
    build_vision_user_content,
)

logger = logging.getLogger(__name__)


def extract_fields_with_vision(
    all_pages_images: List[str],
    field_map: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Extract fields from PDF images using OpenAI Vision API.

    This is the primary extraction method - always uses Vision API with images.
    PDFs must be converted to images before calling this function.

    Args:
        all_pages_images: List of base64-encoded images for all pages
        field_map: Optional dictionary mapping field names to descriptions/instructions.
                   If provided, GPT uses this as a guide to extract specific fields.
                   If None or empty, GPT will identify and suggest all fields it finds.

    Returns:
        Dictionary with extracted data. If field_map was provided, contains only mapped fields.
        If no field_map, contains 'extracted_data' and 'suggested_fields'.

    Raises:
        RuntimeError: If OpenAI API call fails
        ValueError: If response cannot be parsed as JSON
    """
    client = get_openai_client()
    model_name = get_openai_model()

    # Use field_map if provided, otherwise suggest all fields
    if field_map and len(field_map) > 0:
        extraction_instruction = build_vision_field_map_instruction(field_map)
        has_field_map = True
    else:
        extraction_instruction = build_vision_suggest_fields_instruction()
        has_field_map = False

    extraction_content = build_vision_user_content(all_pages_images, extraction_instruction, has_field_map)

    try:
        logger.info(f"Calling OpenAI Vision model {model_name} to extract data from {len(all_pages_images)} pages")

        request_timestamp = datetime.utcnow().isoformat()
        logger.info(
            f"LLM Vision Request - Model: {model_name}, Images: {len(all_pages_images)}, "
            f"Timestamp: {request_timestamp}"
        )

        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": get_vision_system_message()},
                {"role": "user", "content": extraction_content}
            ],
            response_format={"type": "json_object"},
            temperature=0.1
        )

        response_timestamp = datetime.utcnow().isoformat()
        usage = response.usage
        logger.info(
            f"LLM Response - Model: {model_name}, "
            f"Tokens: prompt={usage.prompt_tokens}, completion={usage.completion_tokens}, "
            f"total={usage.total_tokens}, Timestamp: {response_timestamp}"
        )

        content = response.choices[0].message.content
        if not content:
            raise ValueError("Empty response from OpenAI")

        # Save LLM execution results for debugging
        _save_llm_execution_result(
            request_timestamp=request_timestamp,
            response_timestamp=response_timestamp,
            model=model_name,
            extraction_content=extraction_content,
            response_content=content,
            usage=usage
        )

        result = json.loads(content)
        extracted_data = result.get("extracted_data", {})
        if not isinstance(extracted_data, dict):
            logger.warning("extracted_data is not a dictionary, using empty dict")
            extracted_data = {}

        # If no field_map was provided, include suggested_fields in response
        if not has_field_map:
            suggested_fields = result.get("suggested_fields", [])
            if suggested_fields:
                logger.info(f"GPT identified {len(suggested_fields)} suggested fields: {suggested_fields}")
                return {
                    "extracted_data": extracted_data,
                    "suggested_fields": suggested_fields
                }

        logger.info(f"GPT extracted {len(extracted_data)} fields")
        return extracted_data

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse OpenAI response as JSON: {e}")
        logger.warning("Defaulting to empty data")
        return {}
    except Exception as e:
        logger.error(f"OpenAI API error: {e}")
        logger.warning("Defaulting to empty data")
        return {}


def _save_llm_execution_result(
    request_timestamp: str,
    response_timestamp: str,
    model: str,
    extraction_content: List[Dict[str, Any]],
    response_content: str,
    usage: Any
) -> None:
    """
    Save LLM execution results to a file for debugging and analysis.

    Args:
        request_timestamp: ISO timestamp of the request
        response_timestamp: ISO timestamp of the response
        model: Model name used
        extraction_content: The content sent to the API
        response_content: Full response content from LLM
        usage: Token usage information
    """
    try:
        results_dir = Path("/tmp/llm_execution_results")
        results_dir.mkdir(parents=True, exist_ok=True)

        timestamp_str = request_timestamp.replace(":", "-").replace(".", "-")
        filename = results_dir / f"llm_result_{timestamp_str}.json"

        prompt_text = json.dumps(extraction_content, indent=2, default=str)[:1000]
        usage_dict = {
            "prompt_tokens": getattr(usage, 'prompt_tokens', 0),
            "completion_tokens": getattr(usage, 'completion_tokens', 0),
            "total_tokens": getattr(usage, 'total_tokens', 0)
        }

        result_data = {
            "request_timestamp": request_timestamp,
            "response_timestamp": response_timestamp,
            "model": model,
            "prompt_length": len(str(extraction_content)),
            "prompt_preview": prompt_text + "..." if len(prompt_text) > 1000 else prompt_text,
            "response_content": response_content,
            "usage": usage_dict,
            "duration_seconds": (
                datetime.fromisoformat(response_timestamp.replace("Z", "+00:00")) -
                datetime.fromisoformat(request_timestamp.replace("Z", "+00:00"))
            ).total_seconds() if "Z" in request_timestamp else None
        }

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(result_data, f, indent=2, ensure_ascii=False)

        logger.info(f"Saved LLM execution result to: {filename}")
    except Exception as e:
        logger.warning(f"Failed to save LLM execution result: {e}")

