"""NF-e OCR utilities for PDFs.

Minimal helpers to extract NF-e like numeric values from PDF files using OCR.
Designed as pure functions to be reused by operators.
"""

from __future__ import annotations

import io
import logging
import re
from pathlib import Path
from typing import Optional

try:
    import fitz  # type: ignore[import]  # PyMuPDF

    FITZ_AVAILABLE = True
except Exception:  # pragma: no cover - Airflow image should include fitz
    FITZ_AVAILABLE = False

try:
    from PIL import Image  # type: ignore[import]

    PIL_AVAILABLE = True
except Exception:  # pragma: no cover
    PIL_AVAILABLE = False

try:
    import pytesseract  # type: ignore[import]

    TESSERACT_AVAILABLE = True
except Exception:  # pragma: no cover
    TESSERACT_AVAILABLE = False

logger = logging.getLogger(__name__)


def extract_nf_value_from_pdf(pdf_path: Path) -> Optional[str]:
    """Extract NF-e numeric value from the first page of the given PDF.

    Returns the NF-e value as a numeric string with leading zeros trimmed,
    or None if nothing that looks like an NF-e number could be found.
    
    Improved implementation based on pdf_ocr.py patterns:
    - First tries direct text extraction (faster, more accurate)
    - Falls back to OCR with multiple rotation angles if needed
    - Better memory management and error handling
    """
    if not FITZ_AVAILABLE or not PIL_AVAILABLE or not TESSERACT_AVAILABLE:
        logger.warning(
            "OCR dependencies (fitz/Pillow/pytesseract) missing; "
            "NF-e extraction will be skipped for %s",
            pdf_path,
        )
        return None

    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    doc = fitz.open(pdf_path)  # type: ignore[arg-type]
    try:
        if len(doc) == 0:
            return None

        page = doc[0]
        
        # FIRST: Try to extract text directly from PDF (faster and more accurate)
        direct_text = _extract_text_from_pdf_direct(page)
        if direct_text:
            logger.debug("Extracted text directly from PDF: %d characters", len(direct_text))
            nf_raw = _extract_nf_from_text(direct_text)
            if nf_raw:
                nf_trimmed = nf_raw.lstrip("0") or "0"
                logger.info("NF-e found in direct text extraction: %s", nf_trimmed)
                return nf_trimmed
        
        # FALLBACK: Try OCR with multiple rotation angles
        logger.debug("Direct text extraction failed or no NF-e found, trying OCR with rotations...")
        rotation_angles = [0, 270, 180, 90]  # Order: try original first, then common rotations
        
        for rotation in rotation_angles:
            try:
                ocr_text = _extract_text_from_page_with_rotation(page, rotation)
                if not ocr_text:
                    continue
                
                nf_raw = _extract_nf_from_text(ocr_text)
                if nf_raw:
                    nf_trimmed = nf_raw.lstrip("0") or "0"
                    logger.info(
                        "NF-e found via OCR with rotation %d°: %s", 
                        rotation, 
                        nf_trimmed
                    )
                    return nf_trimmed
            except Exception as exc:
                logger.debug("OCR failed for rotation %d°: %s", rotation, exc)
                continue
        
        logger.warning("NF-e value not found in PDF %s after trying all rotation angles", pdf_path.name)
        return None
    finally:
        doc.close()


def _extract_text_from_pdf_direct(page) -> Optional[str]:
    """Try to extract text directly from PDF (if it contains selectable text).
    
    This is faster and more accurate than OCR when the PDF has text layers.
    Based on pdf_ocr.py pattern.
    """
    try:
        text = page.get_text()
        if text and text.strip():
            logger.debug("Extracted %d characters directly from PDF", len(text))
            return text.strip()
        return None
    except Exception as exc:
        logger.debug("Direct text extraction failed: %s", exc)
        return None


def _extract_text_from_page(page, rotation: int = 0) -> str:
    """Render a page to image and run OCR, returning raw text.
    
    Improved version with rotation support and better memory management.
    """
    return _extract_text_from_page_with_rotation(page, rotation)


def _extract_text_from_page_with_rotation(page, rotation: int = 0) -> str:
    """Render a page to image with optional rotation and run OCR, returning raw text.
    
    Improved implementation based on pdf_ocr.py patterns:
    - Higher DPI (300) for better OCR quality
    - Proper rotation handling
    - Better memory management
    - Multiple language fallbacks
    """
    import gc
    
    try:
        # Use higher DPI (300) for better OCR quality (matching pdf_ocr.py)
        # Calculate zoom based on DPI (72 is default PDF DPI)
        dpi = 300
        zoom = dpi / 72.0
        mat = fitz.Matrix(zoom, zoom)  # type: ignore[attr-defined]
        
        pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB, alpha=False, annots=False)  # type: ignore[attr-defined]
        img_data = pix.tobytes("png")
        
        # Convert to PIL Image
        image = Image.open(io.BytesIO(img_data))
        
        # Clean up pixmap immediately
        pix = None
        gc.collect()
        
        # Apply rotation if needed
        if rotation != 0:
            image = image.rotate(-rotation, expand=True, fillcolor='white')
        
        logger.debug(
            "Converted PDF page to image: %dx%d pixels (rotation: %d°)",
            image.size[0],
            image.size[1],
            rotation
        )
    except Exception as exc:
        logger.error("Failed to render PDF page for OCR: %s", exc)
        return ""

    try:
        # Try multiple language combinations for better accuracy
        # Prefer Portuguese + English models; fall back to English only.
        try:
            text = pytesseract.image_to_string(
                image, lang="por+eng", config="--oem 3 --psm 6"
            )
        except Exception:
            try:
                text = pytesseract.image_to_string(
                    image, lang="por", config="--oem 3 --psm 6"
                )
            except Exception:
                text = pytesseract.image_to_string(image, lang="eng", config="--oem 3 --psm 6")
        
        # Clean up image memory
        image.close()
        del image
        gc.collect()
        
        return text or ""
    except Exception as exc:
        logger.error("OCR failed: %s", exc)
        if 'image' in locals():
            image.close()
        gc.collect()
        return ""


def _extract_nf_from_text(text: str) -> Optional[str]:
    """Extract an NF-e style numeric value from OCR text.

    Heuristics:
    - Look for patterns like 'NF', 'NF-e', 'NF_e', 'NFE', 'NF E', etc. near numbers.
    - Fall back to the longest standalone digit sequence if no labeled value found.
    """
    if not text:
        return None

    # Normalise whitespace for simpler matching
    cleaned = " ".join(text.split())

    # Patterns that indicate NF-e labels - case-insensitive.
    label_pattern = r"(?:N[\s\-_]*F[\s\-_]*E?|NFE|NF[-_ ]?E)"

    # First try: label followed by a reasonably long number.
    labeled_regex = re.compile(
        rf"{label_pattern}\D{{0,15}}(\d{{5,}})", flags=re.IGNORECASE
    )
    labeled_matches = labeled_regex.findall(cleaned)
    if labeled_matches:
        # Choose the longest candidate to favour full NF-e values.
        return max(labeled_matches, key=len)

    # Fallback: any stand-alone numeric sequence of length >= 5.
    generic_regex = re.compile(r"\b(\d{5,})\b")
    generic_matches = generic_regex.findall(cleaned)
    if generic_matches:
        return max(generic_matches, key=len)

    return None



