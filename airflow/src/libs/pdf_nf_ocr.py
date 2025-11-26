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
        ocr_text = _extract_text_from_page(page)
        if not ocr_text:
            return None

        nf_raw = _extract_nf_from_text(ocr_text)
        if not nf_raw:
            return None

        # Trim leading zeros; keep single "0" if the string was all zeros.
        nf_trimmed = nf_raw.lstrip("0") or "0"
        return nf_trimmed
    finally:
        doc.close()


def _extract_text_from_page(page) -> str:
    """Render a page to image and run OCR, returning raw text."""
    try:
        # Use a small upscale factor to improve OCR quality but keep it fast.
        mat = fitz.Matrix(2.0, 2.0)  # type: ignore[attr-defined]
        pix = page.get_pixmap(matrix=mat)
        img_data = pix.tobytes("png")
        image = Image.open(io.BytesIO(img_data))
    except Exception as exc:  # pragma: no cover - defensive fallback
        logger.error("Failed to render PDF page for OCR: %s", exc)
        return ""

    try:
        # Prefer Portuguese + English models; fall back to English only.
        text = pytesseract.image_to_string(
            image, lang="por+eng", config="--oem 3 --psm 6"
        )
    except Exception:
        text = pytesseract.image_to_string(image, lang="eng", config="--oem 3 --psm 6")

    return text or ""


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



