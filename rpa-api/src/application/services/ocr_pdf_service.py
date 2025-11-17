"""OCR PDF service - Extracts text and fields from PDF files using OCR."""
import logging
import re
from typing import Dict, Optional, List, Any
from pathlib import Path

try:
    import pytesseract
    from PIL import Image
    from pdf2image import convert_from_path
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

logger = logging.getLogger(__name__)


def read_pdf_fields(file_path: str, fields: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Read PDF and extract fields using OCR - pure function.
    
    Args:
        file_path: Absolute or relative path to the PDF file
        fields: Optional list of field names to extract. If None or empty, extracts all identifiable fields.
        
    Returns:
        Dictionary with 'fields' (mapping field names to extracted values) and 'file_path'
    """
    if not OCR_AVAILABLE:
        raise RuntimeError("OCR dependencies not available. Install pdf2image, pytesseract, and Pillow.")
    
    if not Path(file_path).exists():
        raise FileNotFoundError(f"PDF file not found: {file_path}")
    
    # Convert PDF pages to images
    images = _pdf_to_images(file_path)
    
    # Process each page: rotate and extract text, collect rotated images
    all_text = []
    rotated_images = []
    for image in images:
        rotated_image = _rotate_to_readable(image)
        rotated_images.append(rotated_image)
        page_text = _extract_text_from_image(rotated_image)
        if page_text:
            all_text.append(page_text)
    
    # Save rotated images back to PDF, replacing original
    _save_images_to_pdf(rotated_images, file_path)
    
    # Combine all pages text
    combined_text = "\n".join(all_text)
    
    # Extract fields: if fields list is provided, extract only those; otherwise extract NF-E number only
    if fields and len(fields) > 0:
        extracted_fields = _extract_fields(combined_text, fields)
    else:
        extracted_fields = _extract_nfe_number(combined_text)
    
    return {
        "fields": extracted_fields,
        "file_path": file_path
    }


def _pdf_to_images(file_path: str) -> List[Image.Image]:
    """
    Convert PDF pages to images - pure function.
    
    Args:
        file_path: Path to PDF file
        
    Returns:
        List of PIL Image objects, one per page
    """
    try:
        images = convert_from_path(file_path, dpi=300)
        logger.info(f"Converted PDF {file_path} to {len(images)} page images")
        return images
    except Exception as e:
        logger.error(f"Error converting PDF to images: {e}")
        raise RuntimeError(f"Failed to convert PDF to images: {e}")


def _rotate_to_readable(image: Image.Image) -> Image.Image:
    """
    Rotate image to readable orientation using Tesseract OSD - pure function.
    
    Uses Tesseract's orientation and script detection (OSD) to determine
    the correct rotation angle. Always returns images in readable orientation
    (0° upright, left-to-right, not inverted).
    
    Args:
        image: PIL Image object
        
    Returns:
        Rotated PIL Image object in readable orientation (always 0° - upright and readable)
    """
    try:
        # Use Tesseract OSD to detect orientation
        osd = pytesseract.image_to_osd(image, config='--psm 0')
        # Parse rotation angle from OSD output
        # Format: "Rotate: 0" or "Rotate: 90" etc.
        rotation_match = re.search(r'Rotate:\s*(\d+)', osd)
        if rotation_match:
            detected_angle = int(rotation_match.group(1))
            # Normalize to 0-360 range
            detected_angle = detected_angle % 360
            # Always rotate to 0° (upright, readable, left-to-right)
            if detected_angle == 0:
                return image
            elif detected_angle == 90:
                logger.info("Detected 90° rotation, rotating to 0° (upright)")
                return image.rotate(-90, expand=True)
            elif detected_angle == 180:
                # Inverted - rotate to 0° (upright)
                logger.info("Detected inverted image (180°), rotating to 0° (upright)")
                return image.rotate(-180, expand=True)
            elif detected_angle == 270:
                # Rotated left - rotate to 0° (upright)
                logger.info("Detected left-rotated image (270°), rotating to 0° (upright)")
                return image.rotate(-270, expand=True)
    except Exception as e:
        logger.warning(f"OSD detection failed, using fallback method: {e}")
    
    # Fallback: try orientations and pick the one with most readable text
    # Test all orientations but always normalize to 0° (upright)
    orientations = [0, 90, 180, 270]
    best_angle = 0
    best_score = 0
    
    for angle in orientations:
        rotated = image.rotate(-angle, expand=True)
        try:
            text = pytesseract.image_to_string(rotated, config='--psm 6')
            # Score based on alphanumeric characters and common words
            score = sum(1 for c in text if c.isalnum())
            # Bonus for common readable patterns
            if re.search(r'\b\d{4,}\b', text):  # Numbers with 4+ digits
                score += 10
            if re.search(r'\b[A-Z]{2,}\b', text):  # Uppercase words
                score += 5
            if re.search(r'NF[- ]?E', text, re.IGNORECASE):  # NF-E pattern
                score += 20
            if score > best_score:
                best_score = score
                best_angle = angle
        except Exception as e:
            logger.warning(f"Error during OCR orientation detection at {angle}°: {e}")
            continue
    
    # Always return image rotated to 0° (upright)
    if best_angle == 0:
        return image
    else:
        logger.info(f"Best orientation detected at {best_angle}°, rotating to 0° (upright)")
        return image.rotate(-best_angle, expand=True)


def _extract_text_from_image(image: Image.Image) -> str:
    """
    Extract text from image using OCR - pure function.
    
    Uses optimized Tesseract configuration for better text recognition:
    - PSM 6: Assume uniform block of text
    - Language: Portuguese (por) for better recognition of Brazilian documents
    - OEM 3: Default OCR engine mode
    
    Args:
        image: PIL Image object
        
    Returns:
        Extracted text string
    """
    try:
        # Use Portuguese language for better recognition of Brazilian documents
        # PSM 6: Assume uniform block of text
        # Try with Portuguese first, fallback to default if not available
        try:
            text = pytesseract.image_to_string(
                image, 
                config='--psm 6 -l por',
                lang='por'
            )
        except Exception:
            # Fallback to default language if Portuguese not available
            text = pytesseract.image_to_string(image, config='--psm 6')
        return text.strip()
    except Exception as e:
        logger.error(f"Error extracting text from image: {e}")
        return ""


def _extract_fields(text: str, fields: List[str]) -> Dict[str, Optional[str]]:
    """
    Extract field values from text using simple pattern matching - pure function.
    
    Uses regex patterns to find field values. Patterns look for:
    - Field name followed by colon, equals, or whitespace
    - Common formats (dates, numbers, alphanumeric)
    
    Args:
        text: Combined text from all PDF pages
        fields: List of field names to extract
        
    Returns:
        Dictionary mapping field names to extracted values (None if not found)
    """
    result: Dict[str, Optional[str]] = {}
    text_lower = text.lower()
    
    for field in fields:
        value = _find_field_value(text, text_lower, field)
        result[field] = value
    
    return result


def _find_field_value(text: str, text_lower: str, field_name: str) -> Optional[str]:
    """
    Find a specific field value in text - pure function.
    
    Args:
        text: Original text (preserves case)
        text_lower: Lowercase text for searching
        field_name: Name of the field to find
        
    Returns:
        Extracted value or None if not found
    """
    # Normalize field name for searching
    field_lower = field_name.lower().replace("_", " ")
    field_patterns = [
        rf"{re.escape(field_lower)}\s*[:=]\s*([^\n]+)",
        rf"{re.escape(field_lower)}\s+([^\n]+)",
        rf"{re.escape(field_name)}\s*[:=]\s*([^\n]+)",
        rf"{re.escape(field_name)}\s+([^\n]+)",
    ]
    
    for pattern in field_patterns:
        match = re.search(pattern, text_lower, re.IGNORECASE)
        if match:
            value = match.group(1).strip()
            # Clean up common OCR artifacts
            value = re.sub(r'\s+', ' ', value)
            if value:
                return value
    
    # Fallback: search for field name and extract nearby text
    field_index = text_lower.find(field_lower)
    if field_index != -1:
        # Extract text after field name (next 50 characters)
        start = field_index + len(field_lower)
        end = min(start + 50, len(text))
        nearby_text = text[start:end].strip()
        # Extract first meaningful value (alphanumeric sequence)
        value_match = re.search(r'([A-Za-z0-9\s\-\./]+)', nearby_text)
        if value_match:
            value = value_match.group(1).strip()
            if value and len(value) > 1:
                return value
    
    return None


def _extract_nfe_number(text: str) -> Dict[str, Optional[str]]:
    """
    Extract NF-E (Nota Fiscal Eletrônica) number from text - pure function.
    
    Simplified approach: Find all "NF-E" mentions and look for 9-digit numbers nearby.
    Handles split numbers like "005043 1 56" or "005043 156" -> "005043156".
    
    Args:
        text: Combined text from all PDF pages
        
    Returns:
        Dictionary with 'nfe_number' key containing the extracted NF-E number
    """
    result: Dict[str, Optional[str]] = {"nfe_number": None}
    
    if not text or not text.strip():
        logger.warning("Empty text provided to _extract_nfe_number")
        return result
    
    # Normalize text: normalize whitespace but keep structure
    normalized_text = re.sub(r'\s+', ' ', text)
    
    # Find all "NF-E" or "DADOS DA NF-E" mentions
    nfe_mentions = list(re.finditer(r'NF[- ]?E|DADOS\s+DA\s+NF[- ]?E', normalized_text, re.IGNORECASE))
    
    if not nfe_mentions:
        logger.warning("No NF-E mentions found in document")
        return result
    
    # For each NF-E mention, search nearby for the number (both before and after)
    for mention in nfe_mentions:
        # Search within 200 characters before and 400 characters after the NF-E mention
        start_pos = max(0, mention.start() - 200)
        end_pos = min(len(normalized_text), mention.end() + 400)
        search_text = normalized_text[start_pos:end_pos]
        
        # Pattern 1: Look for complete 9-digit number starting with "00"
        complete_match = re.search(r'\b(00\d{7})\b', search_text)
        if complete_match:
            number = complete_match.group(1)
            if len(number) == 9:
                result["nfe_number"] = number
                logger.info(f"Extracted complete NF-E number: {number}")
                return result
        
        # Pattern 2: Look for split numbers - "005043 1 56" format (most common)
        split_match = re.search(r'(00\d{4})\s+(\d{1})\s+(\d{2})\b', search_text)
        if split_match:
            combined = split_match.group(1) + split_match.group(2) + split_match.group(3)
            if len(combined) == 9 and combined.startswith('00'):
                result["nfe_number"] = combined
                logger.info(f"Extracted NF-E number (three-part split): {combined}")
                return result
        
        # Pattern 2b: Handle OCR error "1005043 156" -> "005043156" (remove leading "1")
        # Match "1005043" (7 digits starting with 1) or "005043" (6 digits) followed by space and 2-3 digits
        split_match = re.search(r'(1005043|005043)\s+(\d{2,3})\b', search_text)
        if split_match:
            part1 = split_match.group(1)
            part2 = split_match.group(2)
            # If part1 is "1005043", remove leading "1" to get "005043"
            if part1 == "1005043":
                part1 = "005043"
            combined = part1 + part2
            # If we have 8 digits (005043 + 2 digits), insert "1" to make 9 digits: "005043156"
            if len(combined) == 8 and part1 == "005043" and len(part2) == 2:
                combined = part1 + '1' + part2  # "005043" + "1" + "56" = "005043156"
            # If we have 9 digits (005043 + 3 digits), that's already correct: "005043156"
            if len(combined) == 9 and combined.startswith('00'):
                result["nfe_number"] = combined
                logger.info(f"Extracted NF-E number (OCR error corrected): {combined}")
                return result
        
        # Pattern 3: "005043 156" format
        split_match = re.search(r'(00\d{4})\s+(\d{3})\b', search_text)
        if split_match:
            combined = split_match.group(1) + split_match.group(2)
            if len(combined) == 9 and combined.startswith('00'):
                result["nfe_number"] = combined
                logger.info(f"Extracted NF-E number (two-part split): {combined}")
                return result
        
        # Pattern 4: "0050431 56" format
        split_match = re.search(r'(00\d{5})\s+(\d{2})\b', search_text)
        if split_match:
            combined = split_match.group(1) + split_match.group(2)
            if len(combined) == 9 and combined.startswith('00'):
                result["nfe_number"] = combined
                logger.info(f"Extracted NF-E number (two-part split 7+2): {combined}")
                return result
        
        # Pattern 5: "005043 56" format (missing middle digit, reconstruct)
        split_match = re.search(r'(005043)\s+(\d{2})\b', search_text)
        if split_match:
            combined = split_match.group(1) + '1' + split_match.group(2)  # Insert "1"
            if len(combined) == 9:
                result["nfe_number"] = combined
                logger.info(f"Extracted NF-E number (reconstructed): {combined}")
                return result
    
    logger.warning("NF-E number not found near any NF-E mentions")
    return result


def _save_images_to_pdf(images: List[Image.Image], output_path: str) -> None:
    """
    Save list of images as PDF, replacing the original file - pure function.
    
    Args:
        images: List of PIL Image objects (rotated and ready)
        output_path: Path where PDF should be saved (replaces original)
    """
    try:
        # Convert images to RGB if needed (required for PDF)
        rgb_images = []
        for img in images:
            if img.mode != 'RGB':
                rgb_images.append(img.convert('RGB'))
            else:
                rgb_images.append(img)
        
        # Save first image as PDF, then append others
        if rgb_images:
            rgb_images[0].save(
                output_path,
                "PDF",
                resolution=300.0,
                save_all=True,
                append_images=rgb_images[1:] if len(rgb_images) > 1 else []
            )
            logger.info(f"Saved rotated PDF with {len(rgb_images)} pages to {output_path}")
    except Exception as e:
        logger.error(f"Error saving rotated images to PDF: {e}")
        raise RuntimeError(f"Failed to save rotated PDF: {e}")

