"""Prompt builders for OpenAI Vision API interactions."""
import json
from typing import List, Dict, Any, Optional


def get_vision_system_message() -> str:
    """
    Get the system message for OpenAI Vision API.

    Returns:
        System message string for PDF data extraction using Vision API
    """
    return (
        "You are a PDF document analyzer with vision capabilities. Always return valid JSON. "
        "Extract all relevant data from the document images. "
        "CRITICAL: Only extract data that is ACTUALLY visible in the images. "
        "Do NOT invent, guess, or create example values."
    )


def build_vision_field_map_instruction(field_map: Dict[str, str]) -> str:
    """
    Build extraction instruction using a field map (field name -> description).

    Args:
        field_map: Dictionary mapping field names to their descriptions/instructions

    Returns:
        Extraction instruction string that uses the field map as a guide
    """
    field_map_json = json.dumps(field_map, indent=2, ensure_ascii=False)
    return (
        f"You are provided with a FIELD MAP that describes what data to extract from the document images.\n\n"
        f"FIELD MAP (use this as a guide to locate and extract data from the images):\n"
        f"{field_map_json}\n\n"
        f"INSTRUCTIONS:\n"
        f"- Use the field map above as a reference to identify where each field appears in the document images\n"
        f"- For each field in the map, locate the corresponding value in the images and extract it\n"
        f"- Match the field names exactly as specified in the map\n"
        f"- If a field from the map is not visible in the images, set it to null\n"
        f"- Extract only the fields specified in the map - do not add extra fields\n"
        f"- The descriptions in the map help you understand what to look for in the document"
    )


def build_vision_suggest_fields_instruction() -> str:
    """
    Build extraction instruction for suggesting/identifying all fields (when no field_map provided).

    Returns:
        Extraction instruction string
    """
    return (
        "ANALYZE the document images and IDENTIFY all relevant fields you can see.\n\n"
        "INSTRUCTIONS:\n"
        "- Examine the document images carefully and identify all data fields present\n"
        "- Extract ALL identifiable and relevant fields from the document\n"
        "- Identify common document fields such as: CNPJ, CPF, invoice numbers, dates, amounts, "
        "values, names, addresses, company names, plate numbers, quantities, etc.\n"
        "- Use descriptive field names in lowercase with underscores (e.g., cnpj, valor_total, data_emissao)\n"
        "- Only include fields that have actual values visible in the images\n"
        "- In addition to extracted_data, provide a 'suggested_fields' array with field names you identified\n"
        "- This helps the system understand what fields are available in this type of document"
    )


def build_vision_user_content(
    all_pages_images: List[str],
    extraction_instruction: str,
    has_field_map: bool = False
) -> List[Dict[str, Any]]:
    """
    Build user content for OpenAI Vision API with images and instructions.

    Args:
        all_pages_images: List of base64-encoded images
        extraction_instruction: Instruction for what to extract
        has_field_map: Whether a field map was provided (affects response format)

    Returns:
        List of content items (text and images) for OpenAI Vision API
    """
    if has_field_map:
        response_format = (
            "Return a JSON object with:\n"
            "- 'extracted_data': A JSON object containing all fields from the field map with their extracted values\n"
            "  (use null for fields not found in the images)"
        )
    else:
        response_format = (
            "Return a JSON object with:\n"
            "- 'extracted_data': A JSON object containing all fields you identified with their extracted values\n"
            "- 'suggested_fields': An array of field names you identified (e.g., ['cnpj', 'valor_total', 'data_emissao'])\n"
            "  This helps understand what fields are available in this document type"
        )

    content = [
        {
            "type": "text",
            "text": (
                "You are analyzing a PDF document that is already in the correct orientation "
                "(readable left to right). "
                f"Extract all identifiable data from the document images below.\n\n"
                f"{extraction_instruction}\n\n"
                "IMPORTANT:\n"
                "- Only extract data that is ACTUALLY visible in the images\n"
                "- Do NOT invent or guess field values - only extract what you can clearly see\n"
                "- Read the document images carefully and match data to the appropriate fields\n"
                "- If a field is not visible, set it to null (do not omit it)\n\n"
                f"{response_format}"
            )
        }
    ]

    # Add all page images
    for page_num, base64_image in enumerate(all_pages_images, 1):
        if base64_image:
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{base64_image}",
                    "detail": "high"
                }
            })
            content.append({
                "type": "text",
                "text": f"Page {page_num}"
            })

    return content

