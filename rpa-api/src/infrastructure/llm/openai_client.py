"""OpenAI client infrastructure - calls GPT to extract fields from text."""
import json
import logging
from typing import Dict, Any, List

from openai import OpenAI

from ...config.config import get_openai_api_key, get_openai_model_name

logger = logging.getLogger(__name__)


def extract_fields_with_gpt(text: str, fields: List[str]) -> Dict[str, Any]:
    """
    Call OpenAI with the given PDF text and list of fields.

    Return a dict[str, Any] representing the extracted JSON.
    If fields list is empty, extracts all identifiable fields from the document.

    Args:
        text: The extracted text from the PDF
        fields: List of field names to extract. If empty, extracts all identifiable fields.

    Returns:
        Dictionary with extracted field values

    Raises:
        RuntimeError: If OpenAI API call fails
        ValueError: If response cannot be parsed as JSON
    """
    api_key = get_openai_api_key()
    model_name = get_openai_model_name()

    client = OpenAI(api_key=api_key)

    if fields and len(fields) > 0:
        # Extract specific fields
        fields_str = ", ".join(fields)
        prompt = f"""You are a data extractor for PDF documents.
Extract the following fields from the provided text: {fields_str}.
Always return a single valid JSON object with exactly these fields as keys.
Use null when a field cannot be found.

Document text:
-----
{text}
-----"""
    else:
        # Extract all identifiable fields
        prompt = f"""You are a data extractor for PDF documents.
Extract ALL identifiable and relevant fields from the provided text.
Identify common document fields such as: CNPJ, CPF, invoice numbers, dates, amounts, values, names, addresses, etc.
Return a single valid JSON object with all identified fields as keys.
Use descriptive field names in lowercase with underscores (e.g., cnpj, valor_total, data_emissao).
Only include fields that have actual values - do not include null fields.

Document text:
-----
{text}
-----"""

    try:
        if fields and len(fields) > 0:
            logger.info(f"Calling OpenAI model {model_name} to extract {len(fields)} specific fields")
        else:
            logger.info(f"Calling OpenAI model {model_name} to extract all identifiable fields")
        
        # Log text preview (first 500 chars) for debugging
        text_preview = text[:500] if len(text) > 500 else text
        logger.info(f"Text being sent to GPT (preview, {len(text)} total chars): {text_preview}...")
        
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "You are a data extractor for PDF documents. Always return valid JSON."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.1
        )

        content = response.choices[0].message.content
        if not content:
            raise ValueError("Empty response from OpenAI")

        extracted_data = json.loads(content)
        logger.info(f"Successfully extracted {len(extracted_data)} fields from OpenAI response")
        return extracted_data

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse OpenAI response as JSON: {e}")
        raise ValueError(f"Invalid JSON response from OpenAI: {e}") from e
    except Exception as e:
        logger.error(f"OpenAI API error: {e}")
        raise RuntimeError(f"OpenAI API call failed: {e}") from e

