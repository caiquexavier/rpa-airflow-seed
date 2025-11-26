"""PDF rotation plugin using OCR heuristics."""

from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path
from typing import Optional

try:
    import fitz  # PyMuPDF

    FITZ_AVAILABLE = True
except ImportError:  # pragma: no cover - Airflow image should include fitz
    FITZ_AVAILABLE = False

try:
    from PIL import Image

    PIL_AVAILABLE = True
except ImportError:  # pragma: no cover
    PIL_AVAILABLE = False

try:
    import pytesseract

    TESSERACT_AVAILABLE = True
except ImportError:  # pragma: no cover
    TESSERACT_AVAILABLE = False

logger = logging.getLogger(__name__)


def rotate_pdf_with_ocr(pdf_path: Path, output_path: Optional[Path] = None) -> Path:
    """Rotate a PDF to the correct orientation using OCR-based heuristics."""
    if not FITZ_AVAILABLE:
        raise RuntimeError("PyMuPDF (fitz) is required for rotation but is not installed.")

    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    output_path = Path(output_path) if output_path else pdf_path
    output_path.parent.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(pdf_path)
    try:
        if len(doc) == 0:
            logger.warning("PDF %s has no pages; skipping rotation", pdf_path)
            return output_path

        first_page = doc[0]
        current_rotation = first_page.rotation % 360
        best_rotation = _determine_rotation_with_ocr(first_page)
        rotation_needed = (best_rotation - current_rotation) % 360

        logger.info(
            "[PDF rotation] %s current=%s target=%s needed=%s",
            pdf_path.name,
            current_rotation,
            best_rotation,
            rotation_needed,
        )

        if rotation_needed != 0 or current_rotation != best_rotation:
            for idx, page in enumerate(doc, start=1):
                original = page.rotation % 360
                new_rotation = (original + rotation_needed) % 360
                if new_rotation != best_rotation:
                    logger.debug(
                        "Page %s rotation mismatch (%s vs %s); forcing target",
                        idx,
                        new_rotation,
                        best_rotation,
                    )
                    new_rotation = best_rotation
                page.set_rotation(new_rotation)
                if page.rotation % 360 != new_rotation:
                    logger.warning(
                        "Page %s failed rotation assignment (expected %s)",
                        idx,
                        new_rotation,
                    )
                    page.set_rotation(best_rotation)

        temp_path = output_path.with_suffix(output_path.suffix + ".tmp")
        try:
            doc.save(
                temp_path,
                garbage=4,
                deflate=True,
                incremental=False,
                encryption=fitz.PDF_ENCRYPT_KEEP,
            )
            shutil.move(temp_path, output_path)
        except Exception as exc:  # pragma: no cover - defensive cleanup
            if temp_path.exists():
                try:
                    os.remove(temp_path)
                except OSError:
                    pass
            raise RuntimeError(f"Failed to save rotated PDF: {exc}") from exc

        logger.info("Rotated PDF saved to %s", output_path)
        return output_path

    finally:
        doc.close()


def _determine_rotation_with_ocr(page) -> int:
    """Determine best rotation for a PyMuPDF page using OCR heuristics."""
    if not (TESSERACT_AVAILABLE and PIL_AVAILABLE):
        logger.warning("OCR dependencies missing; defaulting to 0° rotation")
        return 0

    import io

    logger.info("Converting PDF page to image for rotation detection...")

    try:
        mat = fitz.Matrix(2.0, 2.0)
        pix = page.get_pixmap(matrix=mat)
        img_data = pix.tobytes("png")
        base_image = Image.open(io.BytesIO(img_data))
        logger.info(
            "Converted page to image: %sx%s pixels",
            base_image.size[0],
            base_image.size[1],
        )
    except Exception as exc:
        logger.error("Failed to convert page to image: %s", exc)
        return 0

    # 1) Try a direct OSD pass on the original image. If confidence is good,
    #    trust Tesseract's suggested rotation.
    try:
        base_osd = pytesseract.image_to_osd(
            base_image, output_type=pytesseract.Output.DICT
        )
        base_rotate = int(base_osd.get("rotate", 0))
        base_conf = float(base_osd.get("script_conf", 0))
        logger.info(
            "Base OSD rotation=%s confidence=%.2f", base_rotate, base_conf
        )
        if base_conf > 2.0 and base_rotate in (0, 90, 180, 270):
            # Tesseract's rotate value is the angle required to deskew the text.
            # We want the final upright orientation.
            best_rotation = (360 - base_rotate) % 360
            logger.info(
                "Using direct OSD-based rotation: %s° (from rotate=%s)",
                best_rotation,
                base_rotate,
            )
            return best_rotation
    except Exception as exc:
        logger.debug("Direct OSD rotation detection failed: %s", exc)

    # 2) Fallback: evaluate candidate rotations and score them.
    rotations = [0, 90, 180, 270]
    rotation_scores: dict[int, int] = {}
    logger.info("Testing rotations with OCR to find readable position...")

    for rotation in rotations:
        try:
            test_image = (
                base_image if rotation == 0 else base_image.rotate(-rotation, expand=True)
            )
            try:
                ocr_text = pytesseract.image_to_string(
                    test_image, lang="por+eng", config="--oem 3 --psm 6"
                )
            except Exception:
                ocr_text = pytesseract.image_to_string(
                    test_image, lang="eng", config="--oem 3 --psm 6"
                )

            text_clean = ocr_text.strip()
            word_count = len(text_clean.split()) if text_clean else 0
            char_count = len([c for c in text_clean if c.isalnum()])
            has_numbers = any(c.isdigit() for c in text_clean)
            has_letters = any(c.isalpha() for c in text_clean)

            osd_rotation = None
            osd_confidence = 0.0
            try:
                osd = pytesseract.image_to_osd(
                    test_image, output_type=pytesseract.Output.DICT
                )
                osd_rotation = int(osd.get("rotate", 0))
                osd_confidence = float(osd.get("script_conf", 0))
                logger.debug(
                    "Rotation %s° OSD rotate=%s confidence=%.2f",
                    rotation,
                    osd_rotation,
                    osd_confidence,
                )
            except Exception as osd_exc:
                logger.debug("OSD detection failed for rotation %s°: %s", rotation, osd_exc)

            # Base score from visible text.
            score = word_count * 5 + char_count
            if has_numbers:
                score += 30
            if has_letters:
                score += 30
            if word_count > 5:
                score += 40

            # Use OSD to strongly prefer orientations that appear upright.
            if osd_rotation is not None and osd_confidence > 1.0:
                # Effective upright angle combining our trial rotation and OSD's suggestion.
                upright_angle = (rotation + osd_rotation) % 360
                if upright_angle == 0:
                    score += 5000
                    logger.info(
                        "Rotation %s° looks upright via combined OSD (conf=%.2f)",
                        rotation,
                        osd_confidence,
                    )
                else:
                    # Penalise angles that are far from upright.
                    score -= int(abs(upright_angle) * 5)

            rotation_scores[rotation] = score
            logger.info(
                "Rotation %s° -> %s words, %s chars, score %s",
                rotation,
                word_count,
                char_count,
                score,
            )
        except Exception as exc:
            logger.warning("Failed OCR rotation test (%s°): %s", rotation, exc)
            rotation_scores[rotation] = 0

    best_rotation, best_score = max(rotation_scores.items(), key=lambda item: item[1])
    logger.info(
        "OCR determined best rotation: %s° (score: %s)",
        best_rotation,
        best_score,
    )
    return best_rotation


