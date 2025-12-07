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
        "You are an expert PDF document analyzer with advanced vision capabilities. "
        "Your task is to accurately extract structured data from document images. "
        "CRITICAL RULES:\n"
        "- Only extract data that is ACTUALLY visible and clearly readable in the images\n"
        "- Do NOT invent, guess, estimate, or create example values\n"
        "- If a value is partially visible or unclear, extract what you can see and mark uncertainty\n"
        "- Pay close attention to numbers, dates, codes, and identifiers - accuracy is paramount\n"
        "- Read text carefully, including headers, footers, and all document sections\n"
        "- Always return valid JSON format\n"
        "- For Brazilian documents (NF-e, CT-e), pay special attention to:\n"
        "  * CNPJ/CPF numbers (14 or 11 digits)\n"
        "  * Invoice numbers (NF-e)\n"
        "  * Documento de Transporte (DT) numbers\n"
        "  * Dates in DD/MM/YYYY format\n"
        "  * Monetary values with proper decimal separators"
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
    
    # Check if nf_e is in the field map - provide special instructions
    has_nf_e = "nf_e" in field_map or "nf" in field_map or "nota_fiscal" in field_map
    
    nf_e_instructions = ""
    if has_nf_e:
        nf_e_instructions = (
            "\n\nCRITICAL - NF-e EXTRACTION:\n"
            "- NF-e (Nota Fiscal Eletrônica) is ESSENTIAL - search the ENTIRE document for it\n"
            "- Look for labels like: 'NF-e', 'NFE', 'Nota Fiscal', 'Nº NF-e', 'Número NF-e'\n"
            "- NF-e numbers are typically 5-15 digits long\n"
            "- Check headers, footers, QR codes, and all document sections\n"
            "- May appear near invoice numbers, document numbers, or in barcodes\n"
            "- Extract ALL digits exactly as shown (preserve leading zeros)\n"
            "- If you see multiple numbers, the NF-e is usually the longest numeric sequence\n"
            "- DO NOT return null for nf_e unless you've thoroughly searched the entire document\n"
        )
    
    return (
        f"You are provided with a FIELD MAP that describes what data to extract from the document images.\n\n"
        f"FIELD MAP (use this as a guide to locate and extract data from the images):\n"
        f"{field_map_json}\n\n"
        f"EXTRACTION INSTRUCTIONS:\n"
        f"1. CAREFULLY EXAMINE each document image - scan from top to bottom, left to right\n"
        f"2. For each field in the map above, locate the corresponding value in the images\n"
        f"3. Match field names EXACTLY as specified in the map (case-sensitive)\n"
        f"4. Extract values with HIGH PRECISION:\n"
        f"   - For numbers: extract all digits exactly as shown (no rounding or approximation)\n"
        f"   - For dates: extract in the format shown (typically DD/MM/YYYY)\n"
        f"   - For codes/IDs: extract exactly as displayed (preserve leading zeros if present)\n"
        f"   - For text: extract verbatim, preserving capitalization and special characters\n"
        f"5. SEARCH THOROUGHLY - check headers, body, footers, tables, sidebars, QR codes, barcodes\n"
        f"6. If a field from the map is NOT visible or NOT readable in the images, set it to null\n"
        f"7. Extract ONLY the fields specified in the map - do not add extra fields\n"
        f"8. The descriptions in the map help you understand what to look for and where\n"
        f"9. Double-check your extractions for accuracy before returning the JSON\n"
        f"{nf_e_instructions}\n"
        f"QUALITY CHECK:\n"
        f"- Verify all numeric values are complete (no missing digits)\n"
        f"- Ensure dates are in correct format\n"
        f"- Confirm codes and identifiers match exactly what's shown\n"
        f"- If uncertain about a value, extract what you can see clearly\n"
        f"- For critical fields like nf_e, search the ENTIRE document before giving up"
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
                "You are analyzing a PDF document that has been rotated to the correct orientation "
                "(readable left to right, top to bottom). "
                f"Extract all identifiable data from the document images below with HIGH ACCURACY.\n\n"
                f"{extraction_instruction}\n\n"
                "CRITICAL EXTRACTION RULES:\n"
                "- Only extract data that is ACTUALLY visible and clearly readable in the images\n"
                "- Do NOT invent, guess, estimate, or create example values\n"
                "- Read the document images systematically: scan from top to bottom, left to right\n"
                "- Pay attention to ALL sections: headers, body, footers, tables, sidebars, QR codes, barcodes\n"
                "- For numbers: extract ALL digits exactly as shown (preserve leading zeros)\n"
                "- For dates: extract in the format shown (typically DD/MM/YYYY for Brazilian documents)\n"
                "- For monetary values: extract with proper decimal separators (comma or period)\n"
                "- For codes/IDs: extract exactly as displayed (CNPJ, CPF, invoice numbers, etc.)\n"
                "- SEARCH THOROUGHLY: Check every section of the document before marking a field as null\n"
                "- For NF-e (Nota Fiscal Eletrônica): This is CRITICAL - search headers, footers, QR codes, barcodes, and all document sections\n"
                "- For doc_transportes: Look for transport document numbers, DT numbers, or similar identifiers\n"
                "- If a field is not visible or unclear after thorough search, set it to null (do not omit it, do not guess)\n"
                "- Double-check your extractions for completeness and accuracy\n\n"
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


def build_rotation_detection_instruction() -> str:
    """
    Build instruction for GPT to detect PDF page rotation/orientation.
    
    Returns:
        Instruction string for rotation detection
    """
    return (
        "You are a document orientation analyzer. Analyze this document image and determine the CORRECT rotation "
        "needed to make it readable with proper orientation.\n\n"
        "⚠️ CRITICAL: CHECK FOR INVERSION FIRST - THIS IS THE MOST COMMON ERROR ⚠️\n"
        "Many documents are UPSIDE DOWN (180° rotation needed). ALWAYS check for inversion BEFORE considering other rotations.\n\n"
        "STEP 1: DETECT IF DOCUMENT IS UPSIDE DOWN (180° ROTATION NEEDED)\n"
        "Perform these checks IN ORDER:\n\n"
        "A. WHERE IS THE MAIN HEADER/TITLE?\n"
        "   - Identify the main document title/header (usually largest text at top)\n"
        "   - CORRECT: Title/header should be at the TOP of the page\n"
        "   - WRONG: If title is at the BOTTOM → document is UPSIDE DOWN → return 180°\n"
        "   - WRONG: If you need to turn your head or flip the image to read it → return 180°\n\n"
        "B. WHERE IS THE LOGO/BRANDING?\n"
        "   - Look for company logos, branding elements, or header graphics\n"
        "   - CORRECT: Logo should be in TOP-LEFT or TOP area of the page\n"
        "   - WRONG: If logo is at BOTTOM-RIGHT or BOTTOM-LEFT → document is UPSIDE DOWN → return 180°\n"
        "   - WRONG: If logo appears inverted/upside down → return 180°\n\n"
        "C. CAN YOU READ THE TEXT NATURALLY?\n"
        "   - Try reading any text on the document\n"
        "   - CORRECT: You can read text naturally from left to right without tilting your head\n"
        "   - WRONG: If text appears upside down or you need to flip your head → return 180°\n"
        "   - WRONG: If letters/numbers appear inverted (e.g., '9' looks like '6', 'p' looks like 'b') → return 180°\n"
        "   - WRONG: If text is readable but requires rotating your head → document is rotated → check step 2\n\n"
        "D. WHERE ARE THE TABLE/SECTION HEADERS?\n"
        "   - Identify table headers or section titles\n"
        "   - CORRECT: Headers should be at the TOP, data/content BELOW\n"
        "   - WRONG: If headers are at BOTTOM and data is at TOP → document is UPSIDE DOWN → return 180°\n\n"
        "E. WHERE IS THE SIGNATURE/CONFIRMATION AREA?\n"
        "   - Look for signature lines, confirmation text, or footer information\n"
        "   - CORRECT: Should be at the BOTTOM of the document\n"
        "   - WRONG: If signature/confirmation is at the TOP → document is UPSIDE DOWN → return 180°\n\n"
        "F. CHECK NUMBERS AND TEXT ORIENTATION:\n"
        "   - Look for numbers, dates, or any alphanumeric text\n"
        "   - CORRECT: Numbers and text should be readable horizontally, not inverted\n"
        "   - WRONG: If numbers appear upside down or inverted → return 180°\n\n"
        "DECISION RULE: If ANY of checks A-F indicate the document is upside down, IMMEDIATELY return 180° rotation.\n"
        "Do NOT proceed to other rotation checks if the document is inverted.\n\n"
        "STEP 2: IF NOT INVERTED, CHECK FOR SIDEWAYS ROTATION (90° or 270°)\n"
        "Only perform this step if the document passed all inversion checks above.\n"
        "- 90° = Text rotated clockwise (needs clockwise rotation to fix)\n"
        "- 270° = Text rotated counter-clockwise (needs counter-clockwise rotation to fix)\n"
        "- 0° = Already correct orientation\n\n"
        "STEP 3: FINAL VALIDATION - VERIFY CORRECT ORIENTATION\n"
        "After determining rotation, mentally apply it and verify:\n"
        "✓ Main title/header is at the TOP\n"
        "✓ Logo/branding is in TOP-LEFT or TOP area\n"
        "✓ All text is readable from LEFT to RIGHT without head movement\n"
        "✓ Table/section headers are at TOP\n"
        "✓ Table data/content is BELOW headers\n"
        "✓ Numbers and text are horizontal and readable\n"
        "✓ Signature/confirmation area is at BOTTOM\n"
        "✓ Document flows naturally TOP to BOTTOM\n"
        "✓ NO text appears upside down or inverted\n\n"
        "ROTATION VALUES:\n"
        "- 0° = Document is already correct (no rotation needed)\n"
        "- 90° = Rotate clockwise 90° (text rotated right, needs clockwise correction)\n"
        "- 180° = Rotate 180° (document is UPSIDE DOWN - most common error)\n"
        "- 270° = Rotate counter-clockwise 90° (text rotated left, needs counter-clockwise correction)\n\n"
        "CONFIDENCE GUIDELINES:\n"
        "- 90-100: Perfect - all checks pass, document clearly correct\n"
        "- 70-89: Good - minor ambiguities but clearly correct\n"
        "- 50-69: Acceptable - some uncertainty, verify carefully\n"
        "- 0-49: Low confidence - be conservative\n\n"
        "Return JSON:\n"
        "- 'rotation': 0, 90, 180, or 270 (the rotation needed to make document correct)\n"
        "- 'confidence': 0-100\n"
        "- 'reasoning': MUST include:\n"
        "  * Step-by-step results of inversion checks (A through F above)\n"
        "  * Where the main header/title is located (top/bottom?)\n"
        "  * Where the logo is located (top-left/bottom-right/top-right/bottom-left?)\n"
        "  * Can text be read naturally left-to-right? (yes/no, why?)\n"
        "  * Where are table/section headers? (top/bottom?)\n"
        "  * Where is signature/confirmation? (top/bottom?)\n"
        "  * Final conclusion: why this specific rotation is correct"
    )
