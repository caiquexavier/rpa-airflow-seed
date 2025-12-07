"""GPT PDF extraction service - Extract PDF data with GPT Vision."""
import logging
import base64
import io
from pathlib import Path
from typing import Dict, Any, Optional

try:
    import fitz  # PyMuPDF
    FITZ_AVAILABLE = True
except ImportError:
    FITZ_AVAILABLE = False

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

from ...infrastructure.llm.pdf_extractor import extract_fields_with_vision

logger = logging.getLogger(__name__)

# Higher DPI for better GPT Vision quality
DPI_SCALE = 3.0  # 3x zoom = ~216 DPI


def extract_pdf_data(
    rotated_file_path: str,
    field_map: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    Extract data from already rotated PDF file using GPT Vision.
    
    This function:
    1. Converts rotated PDF pages to PNG images at high DPI
    2. Extracts data from images using GPT Vision
    
    IMPORTANT: This function assumes the PDF is already correctly rotated.
    Use rotate_pdf_file() from gpt_pdf_rotation_service first if rotation is needed.
    
    Args:
        rotated_file_path: Path to the rotated PDF file
        field_map: Optional dictionary mapping field names to descriptions/instructions.
                   If provided, GPT uses this as a guide to extract specific fields.
                   If None or empty, GPT will identify and suggest all fields it finds.
    
    Returns:
        Dictionary with extracted data
    
    Raises:
        RuntimeError: If required libraries are not available or extraction fails
        FileNotFoundError: If PDF file does not exist
    """
    if not FITZ_AVAILABLE:
        raise RuntimeError("PyMuPDF (fitz) not available. Install pymupdf to render PDF pages.")
    
    if not PIL_AVAILABLE:
        raise RuntimeError("PIL/Pillow not available. Install Pillow to convert PDF pages to images.")

    if not Path(rotated_file_path).exists():
        raise FileNotFoundError(f"Rotated PDF file not found: {rotated_file_path}")

    logger.info("Extracting data from rotated PDF: %s", rotated_file_path)

    doc = fitz.open(rotated_file_path)
    try:
        if len(doc) == 0:
            logger.warning("PDF has no pages, skipping extraction")
            return {}

        # Convert all pages to images for GPT Vision extraction
        logger.info("Converting %s page(s) to images for GPT Vision extraction", len(doc))
        all_pages_images: list[str] = []
        failed_pages: list[int] = []
        
        for page_index in range(len(doc)):
            page = doc[page_index]
            base64_image = _render_page_to_base64_image(page)
            if base64_image:
                all_pages_images.append(base64_image)
                logger.info("Converted page %s/%s to image for GPT Vision", page_index + 1, len(doc))
            else:
                failed_pages.append(page_index + 1)
                logger.error("Failed to convert page %s to image", page_index + 1)

        # Validate that we have at least one image before calling GPT
        if not all_pages_images:
            error_msg = (
                f"CRITICAL: Failed to convert any PDF pages to images. "
                f"All {len(doc)} page(s) failed conversion. Cannot proceed with GPT Vision extraction."
            )
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        
        if failed_pages:
            logger.warning(
                "Some pages failed image conversion (pages: %s), but proceeding with %s successful page(s)",
                failed_pages,
                len(all_pages_images)
            )

        # Extract data from images using GPT Vision
        logger.info("Calling GPT Vision API with %s page image(s)", len(all_pages_images))
        if field_map:
            logger.info("Using field_map with %s predefined fields", len(field_map))
        else:
            logger.info("No field_map provided - GPT will identify and suggest all fields found")
        
        extracted_data = extract_fields_with_vision(all_pages_images, field_map=field_map)
        
        logger.info("Successfully extracted data from PDF")
        return extracted_data

    finally:
        doc.close()


def _render_page_to_base64_image(page, image_rotation: int = 0) -> Optional[str]:
    """
    Render PDF page to base64-encoded PNG image for GPT Vision API.
    
    Uses high DPI for better quality. Renders the page at its CURRENT rotation,
    then optionally rotates the IMAGE if needed.
    
    Args:
        page: PyMuPDF page object (at its current rotation)
        image_rotation: Rotation to apply to the rendered IMAGE (0, 90, 180, 270)
    
    Returns:
        Base64-encoded image string or None if conversion failed
    """
    if not PIL_AVAILABLE:
        logger.error("PIL not available, cannot render page to image")
        raise RuntimeError("PIL/Pillow is required for PDF to image conversion")
    
    try:
        # Render page at its CURRENT rotation with high DPI
        mat = fitz.Matrix(DPI_SCALE, DPI_SCALE)
        pix = page.get_pixmap(matrix=mat)
        img_data = pix.tobytes("png")
        
        # If we need to rotate the image, do it on the PIL Image
        if image_rotation != 0:
            image = Image.open(io.BytesIO(img_data))
            # Rotate image (counter-clockwise, so we use negative)
            rotated_image = image.rotate(-image_rotation, expand=True)
            # Convert back to bytes
            img_buffer = io.BytesIO()
            rotated_image.save(img_buffer, format='PNG')
            img_data = img_buffer.getvalue()
        
        # Convert to base64
        base64_image = base64.b64encode(img_data).decode('utf-8')
        
        return base64_image
    except Exception as e:
        logger.error(f"Failed to render page to image: {e}")
        return None

