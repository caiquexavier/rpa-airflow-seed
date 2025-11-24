"""GPT PDF service - Extract PDF data with GPT Vision (rotation handled elsewhere)."""
import logging
import re
import shutil
from pathlib import Path
from typing import Dict, Any, Tuple, Optional

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


def gpt_pdf_extractor(
    file_path: str,
    output_path: Optional[str] = None,
    field_map: Optional[Dict[str, str]] = None,
) -> Tuple[str, Dict[str, Any]]:
    """
    Extract all identifiable data from a PDF using GPT Vision.

    IMPORTANT: This function ALWAYS converts PDF pages to images before calling GPT.
    It never uses text extraction - only Vision API.

    Rotation/orientation should be handled upstream (e.g., via Airflow plugin).

    Steps:
    1. Render every PDF page to an image (REQUIRED)
    2. Ask GPT Vision to extract requested fields from images
    3. Copy the PDF to an organized folder (doc_transportes/nf_e) if those fields are present

    Args:
        file_path: Path to the PDF file
        output_path: Optional output path for organized file
        field_map: Optional dictionary mapping field names to descriptions/instructions.
                   Example: {'cnpj': 'Brazilian company registration number', 'valor_total': 'Total amount'}.
                   If provided, GPT uses this as a guide to extract specific fields.
                   If None or empty, GPT will identify and suggest all fields it finds.

    Returns:
        Tuple of (organized_file_path, extracted_data_dict)

    Raises:
        RuntimeError: If required libraries are not available or image conversion fails
        FileNotFoundError: If PDF file does not exist
    """
    # Validate required dependencies
    if not FITZ_AVAILABLE:
        raise RuntimeError("PyMuPDF (fitz) not available. Install pymupdf to render PDF pages.")
    
    if not PIL_AVAILABLE:
        raise RuntimeError("PIL/Pillow not available. Install Pillow to convert PDF pages to images.")

    if not Path(file_path).exists():
        raise FileNotFoundError(f"PDF file not found: {file_path}")

    logger.info("Extracting PDF data with GPT Vision (always using image conversion): %s", file_path)

    if output_path is None:
        output_path = file_path
    else:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(file_path)
    try:
        if len(doc) == 0:
            logger.warning("PDF has no pages, skipping processing")
            return file_path, {}

        # STEP 1: ALWAYS convert all PDF pages to images (REQUIRED)
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

        # STEP 2: Call GPT Vision with images (never use text extraction)
        logger.info("Calling GPT Vision API with %s page image(s)", len(all_pages_images))
        if field_map:
            logger.info("Using field_map with %s predefined fields", len(field_map))
        else:
            logger.info("No field_map provided - GPT will identify and suggest all fields found")
        
        extracted_data = extract_fields_with_vision(all_pages_images, field_map=field_map)
        organized_file_path = _organize_file_by_extracted_fields(
            file_path=file_path,
            extracted_data=extracted_data,
            target_path=output_path,
        )

        return organized_file_path, extracted_data

    finally:
        doc.close()


def _render_page_to_base64_image(page, image_rotation: int = 0) -> Optional[str]:
    """
    Render PDF page to base64-encoded PNG image for GPT Vision API.
    
    This function is REQUIRED - all PDF pages must be converted to images before
    calling GPT. This ensures GPT Vision is always used, never text extraction.
    
    Renders the page at its CURRENT rotation, then rotates the IMAGE (not the page).
    This ensures we're showing GPT what the page actually looks like at different orientations.
    
    Args:
        page: PyMuPDF page object (at its current rotation)
        image_rotation: Rotation to apply to the rendered IMAGE (0, 90, 180, 270)
        
    Returns:
        Base64-encoded image string or None if conversion failed
        
    Raises:
        RuntimeError: If PIL is not available (should be checked before calling)
    """
    import base64
    import io
    
    if not PIL_AVAILABLE:
        logger.error("PIL not available, cannot render page to image")
        raise RuntimeError("PIL/Pillow is required for PDF to image conversion")
    
    try:
        # Render page at its CURRENT rotation (don't modify page rotation)
        mat = fitz.Matrix(2.0, 2.0)  # 2x zoom for better quality
        pix = page.get_pixmap(matrix=mat)
        img_data = pix.tobytes("png")
        
        # If we need to rotate the image, do it on the PIL Image, not the page
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


def _organize_file_by_extracted_fields(
    file_path: str,
    extracted_data: Dict[str, Any],
    target_path: Optional[str] = None
) -> str:
    """
    Copy PDF file to the same directory using detected doc_transportes/nf_e.
    
    Output file pattern: {doc_transportes}_{nf_e}.pdf inside the existing directory.
    """
    try:
        # Only use doc_transportes for file naming - no fallbacks
        doc_transportes = extracted_data.get("doc_transportes")
        nf_e = extracted_data.get("nf_e") or extracted_data.get("nf") or extracted_data.get("nota_fiscal")
        
        if not doc_transportes or not nf_e:
            logger.warning(
                "Cannot rename PDF: missing required fields. doc_transportes=%s, nf_e=%s. "
                "Available fields: %s",
                doc_transportes,
                nf_e,
                list(extracted_data.keys()),
            )
            return file_path
        
        doc_transportes = str(doc_transportes).strip()
        nf_e = str(nf_e).strip()
        nf_e_trimmed = nf_e.lstrip('0') or '0'
        
        doc_transportes_clean = _sanitize_for_filename(doc_transportes)
        nf_e_clean = _sanitize_for_filename(nf_e_trimmed)
        
        original_file = Path(file_path)
        try:
            original_file = original_file.resolve()
        except (OSError, RuntimeError):
            original_file = Path(file_path).absolute()
        
        target_dir = (
            Path(target_path).parent.resolve()
            if target_path
            else original_file.parent.resolve()
        )
        
        if not original_file.exists():
            logger.warning("Source file does not exist for organization: %s", original_file)
            return file_path
        
        new_filename = f"{doc_transportes_clean}_{nf_e_clean}.pdf"
        new_file_path = target_dir / new_filename
        
        if new_file_path.exists():
            logger.info("Target file already exists (%s). Overwriting.", new_file_path)
            new_file_path.unlink()
        
        shutil.copy2(str(original_file), str(new_file_path))
        if new_file_path.exists() and new_file_path.stat().st_size > 0:
            logger.info("✓ File copied to %s", new_file_path)
            return str(new_file_path.absolute())
        
        logger.error("Failed to verify copied file at %s", new_file_path)
        return file_path
    
    except Exception as e:
        logger.error("Failed to organize file based on extracted fields: %s", e)
        logger.warning("Returning original file path: %s", file_path)
        return file_path


def _normalize_date_string(value: str) -> str:
    """Normalize doc_transportes into YYYYMMDD-ish string by keeping digits."""
    digits_only = re.sub(r'\D', '', value)
    return digits_only or value.strip()


def _sanitize_for_filename(value: str) -> str:
    """Remove characters that are invalid for filenames."""
    sanitized = re.sub(r'[<>:"/\\|?*\s]+', '_', value)
    return sanitized.strip('_') or "arquivo"


