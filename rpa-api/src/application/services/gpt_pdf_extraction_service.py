"""GPT PDF/PNG extraction service - Extract data from PDF or PNG files with GPT Vision."""
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


def extract_png_data(
    png_file_path: str,
    field_map: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    Extract data from already rotated PNG image file using GPT Vision.
    
    This function:
    1. Reads PNG image directly (assumes already correctly rotated)
    2. Converts to base64 for GPT Vision API
    3. Extracts data from image using GPT Vision
    
    IMPORTANT: This function assumes the PNG is already correctly rotated.
    
    Args:
        png_file_path: Path to the rotated PNG image file
        field_map: Optional dictionary mapping field names to descriptions/instructions.
                   If provided, GPT uses this as a guide to extract specific fields.
                   If None or empty, GPT will identify and suggest all fields it finds.
    
    Returns:
        Dictionary with extracted data
    
    Raises:
        RuntimeError: If required libraries are not available or extraction fails
        FileNotFoundError: If PNG file does not exist
    """
    if not PIL_AVAILABLE:
        raise RuntimeError("PIL/Pillow not available. Install Pillow to process PNG images.")

    if not Path(png_file_path).exists():
        raise FileNotFoundError(f"PNG file not found: {png_file_path}")

    logger.info("Extracting data from rotated PNG: %s", png_file_path)

    try:
        # Read PNG image and convert to base64
        image = Image.open(png_file_path)
        
        # Convert to RGB if necessary (for consistency)
        if image.mode == 'RGBA':
            # Create white background for RGBA images
            rgb_image = Image.new('RGB', image.size, (255, 255, 255))
            rgb_image.paste(image, mask=image.split()[3])  # Use alpha channel as mask
            image = rgb_image
        elif image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Convert image to base64
        img_buffer = io.BytesIO()
        image.save(img_buffer, format='PNG')
        img_data = img_buffer.getvalue()
        base64_image = base64.b64encode(img_data).decode('utf-8')
        
        # Close image
        image.close()
        
        logger.info("Converted PNG to base64 for GPT Vision extraction")
        
        # Extract data from image using GPT Vision
        logger.info("Calling GPT Vision API with PNG image")
        if field_map:
            logger.info("Using field_map with %s predefined fields", len(field_map))
        else:
            logger.info("No field_map provided - GPT will identify and suggest all fields found")
        
        extracted_data = extract_fields_with_vision([base64_image], field_map=field_map)
        
        logger.info("Successfully extracted data from PNG")
        return extracted_data

    except Exception as e:
        logger.error(f"Failed to process PNG image: {e}")
        raise RuntimeError(f"Failed to extract data from PNG: {e}") from e


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


def extract_data_from_file(
    file_path: str,
    field_map: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    Extract data from file (PDF or PNG) using GPT Vision.
    Automatically detects file type and uses appropriate extraction method.
    
    Args:
        file_path: Path to the file (PDF or PNG)
        field_map: Optional dictionary mapping field names to descriptions/instructions.
    
    Returns:
        Dictionary with extracted data
    
    Raises:
        RuntimeError: If file type is not supported or extraction fails
        FileNotFoundError: If file does not exist
    """
    file_path_obj = Path(file_path)
    
    if not file_path_obj.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    # Detect file type by extension
    file_ext = file_path_obj.suffix.lower()
    
    if file_ext == '.png':
        logger.info("Detected PNG file, using PNG extraction")
        return extract_png_data(file_path, field_map=field_map)
    elif file_ext == '.pdf':
        logger.info("Detected PDF file, using PDF extraction")
        return extract_pdf_data(file_path, field_map=field_map)
    else:
        raise RuntimeError(f"Unsupported file type: {file_ext}. Only .png and .pdf are supported.")


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

