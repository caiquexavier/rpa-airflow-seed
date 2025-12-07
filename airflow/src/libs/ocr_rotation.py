"""OCR Rotation and Deskew Pipeline - Pure functions for robust document rotation correction.

This module provides a clean, composable pipeline for:
- Coarse rotation detection (Tesseract OSD)
- Fine deskew correction (OpenCV)
- Multi-engine OCR (Tesseract + PaddleOCR/EasyOCR)
"""

from __future__ import annotations

import gc
import io
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np

try:
    import fitz  # PyMuPDF
    FITZ_AVAILABLE = True
except ImportError:
    FITZ_AVAILABLE = False

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False

try:
    from paddleocr import PaddleOCR
    PADDLEOCR_AVAILABLE = True
except ImportError:
    PADDLEOCR_AVAILABLE = False

try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False

logger = logging.getLogger(__name__)

# Constants
VALID_ROTATIONS = {0, 90, 180, 270}
OSD_MIN_CONFIDENCE = 2.0
SKEW_ANGLE_THRESHOLD = 0.5  # Ignore skew angles smaller than this


@dataclass
class RotationInfo:
    """Information about applied rotation."""
    angle: float
    source: str  # "osd", "best_of_four", or "manual"


@dataclass
class OcrResult:
    """OCR result from a single engine."""
    engine_name: str
    text: str
    confidence: Optional[float]
    rotation_applied: float  # Total rotation (coarse + fine) in degrees


@dataclass
class ProcessedDocumentResult:
    """Final result of document processing."""
    text: str
    engine_used: str
    coarse_rotation_angle: float
    deskew_angle: float
    all_engine_results: list[OcrResult]


def pil_to_numpy(image: Image.Image) -> np.ndarray:
    """Convert PIL Image to numpy array."""
    if not PIL_AVAILABLE:
        raise RuntimeError("PIL/Pillow not available")
    return np.array(image)


def numpy_to_pil(image: np.ndarray) -> Image.Image:
    """Convert numpy array to PIL Image."""
    if not PIL_AVAILABLE:
        raise RuntimeError("PIL/Pillow not available")
    return Image.fromarray(image)


def rotate_image_opencv(image: np.ndarray, angle: float, border_value: int = 255) -> np.ndarray:
    """Rotate image by angle degrees using OpenCV. Falls back to PIL if OpenCV unavailable.
    
    Args:
        image: Input image as numpy array
        angle: Rotation angle in degrees (positive = counterclockwise)
        border_value: Value for border pixels (default: 255 for white)
    
    Returns:
        Rotated image as numpy array
    """
    if CV2_AVAILABLE:
        # Use OpenCV for better quality rotation
        # Convert angle to radians (OpenCV uses radians)
        angle_rad = np.deg2rad(angle)
        
        # Get image dimensions
        height, width = image.shape[:2]
        center = (width / 2, height / 2)
        
        # Calculate rotation matrix
        rotation_matrix = cv2.getRotationMatrix2D(center, -angle, 1.0)
        
        # Calculate new dimensions to avoid cropping
        cos = np.abs(rotation_matrix[0, 0])
        sin = np.abs(rotation_matrix[0, 1])
        new_width = int((height * sin) + (width * cos))
        new_height = int((height * cos) + (width * sin))
        
        # Adjust rotation matrix for new dimensions
        rotation_matrix[0, 2] += (new_width / 2) - center[0]
        rotation_matrix[1, 2] += (new_height / 2) - center[1]
        
        # Apply rotation with border replication
        if len(image.shape) == 2:
            # Grayscale
            border_mode = cv2.BORDER_CONSTANT
        else:
            # Color
            border_mode = cv2.BORDER_CONSTANT
        
        rotated = cv2.warpAffine(
            image,
            rotation_matrix,
            (new_width, new_height),
            flags=cv2.INTER_LINEAR,
            borderMode=border_mode,
            borderValue=border_value
        )
        
        return rotated
    else:
        # Fallback to PIL rotation
        if not PIL_AVAILABLE:
            raise RuntimeError("Neither OpenCV nor PIL available for rotation")
        
        logger.debug("OpenCV not available, using PIL for rotation")
        pil_image = numpy_to_pil(image)
        # PIL rotates counterclockwise, so use negative angle
        rotated_pil = pil_image.rotate(-angle, expand=True, fillcolor=border_value)
        return pil_to_numpy(rotated_pil)


def coarse_rotate(image: np.ndarray) -> tuple[np.ndarray, RotationInfo]:
    """Detect and apply coarse rotation using Tesseract OSD.
    
    Args:
        image: Input image as numpy array
    
    Returns:
        Tuple of (rotated_image, rotation_info)
    """
    if not TESSERACT_AVAILABLE or not PIL_AVAILABLE:
        logger.warning("Tesseract or PIL not available, skipping coarse rotation")
        return image, RotationInfo(angle=0.0, source="manual")
    
    try:
        # Convert to PIL for Tesseract
        pil_image = numpy_to_pil(image)
        
        # Try OSD detection
        try:
            osd_result = pytesseract.image_to_osd(pil_image, output_type=pytesseract.Output.DICT)
            osd_rotate = int(osd_result.get("rotate", 0))
            osd_conf = float(osd_result.get("script_conf", 0))
            
            logger.debug("OSD raw result: rotate=%d, confidence=%.2f", osd_rotate, osd_conf)
            
            if osd_conf > OSD_MIN_CONFIDENCE and osd_rotate in VALID_ROTATIONS:
                # Tesseract returns clockwise rotation, convert to counterclockwise
                rotation_angle = (360 - osd_rotate) % 360
                logger.info("OSD detected rotation: %d° (confidence: %.2f)", rotation_angle, osd_conf)
                
                if rotation_angle != 0:
                    if not CV2_AVAILABLE:
                        logger.warning("OpenCV not available, cannot apply OSD rotation. Falling back to best-of-four.")
                        # Fall through to best-of-four
                    else:
                        try:
                            rotated = rotate_image_opencv(image, rotation_angle)
                            logger.info("Applied OSD rotation: %d°", rotation_angle)
                            return rotated, RotationInfo(angle=float(rotation_angle), source="osd")
                        except Exception as e:
                            logger.warning("Failed to apply OSD rotation %d°: %s. Falling back to best-of-four.", rotation_angle, e)
                            # Fall through to best-of-four
                else:
                    logger.info("OSD detected no rotation needed (0°)")
                    return image, RotationInfo(angle=0.0, source="osd")
            else:
                logger.debug("OSD confidence too low (%.2f <= %.2f) or invalid rotation (%d)", 
                           osd_conf, OSD_MIN_CONFIDENCE, osd_rotate)
        except Exception as e:
            logger.debug("OSD detection failed: %s", e)
        
        # Fallback: best-of-four rotations
        logger.info("OSD failed or low confidence, trying best-of-four rotations")
        return _best_of_four_rotations(image)
        
    except Exception as e:
        logger.warning("Coarse rotation failed: %s", e)
        return image, RotationInfo(angle=0.0, source="manual")


def _best_of_four_rotations(image: np.ndarray) -> tuple[np.ndarray, RotationInfo]:
    """Test all four rotations and choose the best one based on OCR text quality.
    
    Uses a composite score considering text length, word count, and character diversity
    to determine the most plausible orientation.
    
    Args:
        image: Input image as numpy array
    
    Returns:
        Tuple of (best_rotated_image, rotation_info)
    """
    if not TESSERACT_AVAILABLE or not PIL_AVAILABLE:
        return image, RotationInfo(angle=0.0, source="manual")
    
    best_rotation = 0
    best_score = -1.0
    
    for rotation in [0, 90, 180, 270]:
        try:
            if rotation == 0:
                test_image = image.copy()
            else:
                test_image = rotate_image_opencv(image, rotation)
            
            # Quick OCR test
            pil_test = numpy_to_pil(test_image)
            text = pytesseract.image_to_string(pil_test, lang="por+eng", config="--oem 3 --psm 6")
            text_clean = text.strip()
            
            # Calculate composite score: text length + word count + character diversity
            text_length = len(text_clean)
            word_count = len(text_clean.split()) if text_clean else 0
            # Character diversity: ratio of alphanumeric to total characters
            alnum_chars = sum(1 for c in text_clean if c.isalnum())
            char_diversity = alnum_chars / len(text_clean) if text_clean else 0.0
            
            # Composite score: prioritize text length, then word count, then diversity
            score = text_length * 1.0 + word_count * 2.0 + char_diversity * 100.0
            
            if score > best_score:
                best_score = score
                best_rotation = rotation
            
            if rotation != 0:
                del test_image
        except Exception as e:
            logger.debug("Rotation %d° test failed: %s", rotation, e)
            continue
    
    if best_rotation != 0:
        rotated = rotate_image_opencv(image, best_rotation)
        logger.info("Best-of-four selected rotation: %d° (score: %.1f)", best_rotation, best_score)
        return rotated, RotationInfo(angle=float(best_rotation), source="best_of_four")
    else:
        return image, RotationInfo(angle=0.0, source="best_of_four")


def deskew_image(image: np.ndarray) -> tuple[np.ndarray, float]:
    """Detect and correct fine skew in image using OpenCV.
    
    Uses multiple contours and aggregates their angles for more robust skew detection.
    Falls back to single contour if aggregation fails.
    
    Args:
        image: Input image as numpy array (should be grayscale or color)
    
    Returns:
        Tuple of (deskewed_image, skew_angle_in_degrees)
    """
    if not CV2_AVAILABLE:
        logger.warning("OpenCV not available, skipping deskew")
        return image, 0.0
    
    try:
        # Convert to grayscale if needed
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        else:
            gray = image.copy()
        
        # Binarize using Otsu's method (invert to make text white on black)
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        
        # Find contours
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            logger.debug("No contours found, skipping deskew")
            return image, 0.0
        
        # Filter contours by area (ignore very small ones)
        min_area = (image.shape[0] * image.shape[1]) * 0.001  # 0.1% of image area
        significant_contours = [c for c in contours if cv2.contourArea(c) > min_area]
        
        if not significant_contours:
            logger.debug("No significant contours found, skipping deskew")
            return image, 0.0
        
        # Try to aggregate angles from multiple contours for robustness
        angles = []
        for contour in significant_contours[:10]:  # Limit to top 10 to avoid noise
            try:
                rect = cv2.minAreaRect(contour)
                angle = rect[2]
                # Normalize angle to [-45, 45] range
                if angle < -45:
                    angle += 90
                elif angle > 45:
                    angle -= 90
                # Only consider reasonable angles
                if abs(angle) < 45:
                    angles.append(angle)
            except Exception:
                continue
        
        if not angles:
            logger.debug("Could not extract angles from contours, skipping deskew")
            return image, 0.0
        
        # Use median angle for robustness (less sensitive to outliers)
        angles_sorted = sorted(angles)
        median_idx = len(angles_sorted) // 2
        if len(angles_sorted) % 2 == 0:
            angle = (angles_sorted[median_idx - 1] + angles_sorted[median_idx]) / 2.0
        else:
            angle = angles_sorted[median_idx]
        
        # Ignore very small angles
        if abs(angle) < SKEW_ANGLE_THRESHOLD:
            logger.debug("Skew angle too small (%.2f°), skipping deskew", angle)
            return image, 0.0
        
        logger.info("Detected skew angle: %.2f° (from %d contours), applying correction", angle, len(angles))
        
        # Rotate to correct skew (negative angle to deskew)
        deskewed = rotate_image_opencv(image, -angle)
        
        return deskewed, float(angle)
        
    except Exception as e:
        logger.warning("Deskew detection failed: %s", e)
        return image, 0.0


def run_ocr_tesseract(image: np.ndarray, lang: str = "por+eng", rotation_applied: float = 0.0) -> OcrResult:
    """Run OCR using Tesseract.
    
    Args:
        image: Input image as numpy array
        lang: Language code for Tesseract
        rotation_applied: Total rotation applied so far (for result tracking)
    
    Returns:
        OcrResult with Tesseract output
    """
    if not TESSERACT_AVAILABLE or not PIL_AVAILABLE:
        return OcrResult(
            engine_name="tesseract",
            text="",
            confidence=None,
            rotation_applied=rotation_applied
        )
    
    try:
        pil_image = numpy_to_pil(image)
        
        # Run OCR
        text = pytesseract.image_to_string(pil_image, lang=lang, config="--oem 3 --psm 6")
        
        # Calculate confidence from OCR data
        try:
            data = pytesseract.image_to_data(pil_image, lang=lang, output_type=pytesseract.Output.DICT)
            confidences = [int(conf) for conf in data.get("conf", []) if conf != "-1"]
            avg_confidence = sum(confidences) / len(confidences) if confidences else None
        except Exception:
            avg_confidence = None
        
        return OcrResult(
            engine_name="tesseract",
            text=text.strip(),
            confidence=avg_confidence,
            rotation_applied=rotation_applied
        )
    except Exception as e:
        logger.warning("Tesseract OCR failed: %s", e)
        return OcrResult(
            engine_name="tesseract",
            text="",
            confidence=None,
            rotation_applied=rotation_applied
        )


def run_ocr_paddleocr(image: np.ndarray, lang: str = "por", rotation_applied: float = 0.0) -> OcrResult:
    """Run OCR using PaddleOCR.
    
    Args:
        image: Input image as numpy array
        lang: Language code for PaddleOCR (e.g., "por", "en")
        rotation_applied: Total rotation applied so far (for result tracking)
    
    Returns:
        OcrResult with PaddleOCR output
    """
    if not PADDLEOCR_AVAILABLE:
        return OcrResult(
            engine_name="paddleocr",
            text="",
            confidence=None,
            rotation_applied=rotation_applied
        )
    
    try:
        # Initialize PaddleOCR (lazy initialization - could be optimized)
        ocr = PaddleOCR(use_angle_cls=True, lang=lang, show_log=False)
        
        # Run OCR
        result = ocr.ocr(image, cls=True)
        
        # Extract text and confidence
        text_parts = []
        confidences = []
        
        if result and result[0]:
            for line in result[0]:
                if line and len(line) >= 2:
                    text_parts.append(line[1][0])  # Text
                    confidences.append(line[1][1])  # Confidence
        
        text = "\n".join(text_parts)
        avg_confidence = sum(confidences) / len(confidences) * 100 if confidences else None
        
        return OcrResult(
            engine_name="paddleocr",
            text=text.strip(),
            confidence=avg_confidence,
            rotation_applied=rotation_applied
        )
    except Exception as e:
        logger.warning("PaddleOCR failed: %s", e)
        return OcrResult(
            engine_name="paddleocr",
            text="",
            confidence=None,
            rotation_applied=rotation_applied
        )


def run_ocr_easyocr(image: np.ndarray, lang: list[str] = None, rotation_applied: float = 0.0) -> OcrResult:
    """Run OCR using EasyOCR.
    
    Args:
        image: Input image as numpy array
        lang: List of language codes (e.g., ["pt", "en"])
        rotation_applied: Total rotation applied so far (for result tracking)
    
    Returns:
        OcrResult with EasyOCR output
    """
    if not EASYOCR_AVAILABLE:
        return OcrResult(
            engine_name="easyocr",
            text="",
            confidence=None,
            rotation_applied=rotation_applied
        )
    
    try:
        if lang is None:
            lang = ["pt", "en"]
        
        # Initialize EasyOCR reader (lazy initialization - could be optimized)
        reader = easyocr.Reader(lang, gpu=False, verbose=False)
        
        # Run OCR
        results = reader.readtext(image)
        
        # Extract text and confidence
        text_parts = []
        confidences = []
        
        for detection in results:
            text_parts.append(detection[1])  # Text
            confidences.append(detection[2])  # Confidence
        
        text = "\n".join(text_parts)
        avg_confidence = sum(confidences) / len(confidences) * 100 if confidences else None
        
        return OcrResult(
            engine_name="easyocr",
            text=text.strip(),
            confidence=avg_confidence,
            rotation_applied=rotation_applied
        )
    except Exception as e:
        logger.warning("EasyOCR failed: %s", e)
        return OcrResult(
            engine_name="easyocr",
            text="",
            confidence=None,
            rotation_applied=rotation_applied
        )


def select_best_ocr_result(results: list[OcrResult]) -> OcrResult:
    """Select the best OCR result from multiple engines.
    
    Selection rules:
    1. Prefer non-empty text
    2. If multiple have non-empty text, prefer highest confidence
    3. If confidence unavailable, prefer longest text
    4. Tie-break: prefer Tesseract
    
    Args:
        results: List of OcrResult objects
    
    Returns:
        Best OcrResult
    """
    if not results:
        return OcrResult(engine_name="none", text="", confidence=None, rotation_applied=0.0)
    
    # Filter to non-empty results
    non_empty = [r for r in results if r.text.strip()]
    
    if not non_empty:
        # Return first result if all are empty
        return results[0]
    
    # If only one non-empty, return it
    if len(non_empty) == 1:
        return non_empty[0]
    
    # Prefer results with confidence values
    with_confidence = [r for r in non_empty if r.confidence is not None]
    
    if with_confidence:
        # Sort by confidence (descending), then by text length
        best = max(with_confidence, key=lambda r: (r.confidence or 0, len(r.text)))
        return best
    
    # No confidence values, use text length
    best = max(non_empty, key=lambda r: len(r.text))
    
    # Tie-break: prefer Tesseract
    tesseract_results = [r for r in non_empty if r.engine_name == "tesseract" and len(r.text) == len(best.text)]
    if tesseract_results:
        return tesseract_results[0]
    
    return best


def process_image_with_verification(
    image: np.ndarray,
    lang: str = "por+eng",
    use_paddleocr: bool = True,
    use_easyocr: bool = False,
    require_landscape: bool = True,
    check_inverted: bool = True
) -> tuple[ProcessedDocumentResult, bool, bool]:
    """Process image with business logic verification (landscape requirement, inverted check).
    
    Args:
        image: Input image as numpy array
        lang: Language code for OCR
        use_paddleocr: Whether to use PaddleOCR as secondary engine
        use_easyocr: Whether to use EasyOCR as secondary engine
        require_landscape: Whether to require landscape orientation
        check_inverted: Whether to check for inverted text patterns
    
    Returns:
        Tuple of (ProcessedDocumentResult, is_landscape, is_inverted)
    """
    result = process_image(image, lang, use_paddleocr, use_easyocr)
    
    # Check landscape requirement (on processed image after rotation)
    is_landscape = False
    if require_landscape:
        # Get the processed image dimensions (after rotation/deskew)
        # Note: We need to check the final image, but we only have the result
        # For now, check original - in practice, this should check the rotated image
        height, width = image.shape[:2]
        # Account for rotation: if rotation was 90 or 270, dimensions swap
        if result.coarse_rotation_angle in (90, 270):
            width, height = height, width
        is_landscape = width > height
    
    # Check for inverted text (simplified check)
    is_inverted = False
    if check_inverted and result.text:
        # Simple heuristic: check if header keywords appear at end
        text_lower = result.text.lower()
        header_keywords = ['comprovante', 'entrega', 'unilever', 'transportadora']
        footer_keywords = ['nome', 'conferente', 'assinatura']
        
        words = text_lower.split()
        if len(words) >= 20:
            first_30 = ' '.join(words[:30])
            last_30 = ' '.join(words[-30:])
            
            header_at_end = sum(1 for kw in header_keywords if kw in last_30)
            footer_at_start = sum(1 for kw in footer_keywords if kw in first_30)
            
            if header_at_end >= 1 and footer_at_start >= 1:
                is_inverted = True
                logger.warning("Inverted text pattern detected")
    
    return result, is_landscape, is_inverted


def load_image_from_path(path: Path) -> np.ndarray:
    """Load image from file path and convert to numpy array.
    
    Args:
        path: Path to image file (PNG, JPEG, etc.)
    
    Returns:
        Image as numpy array (RGB format)
    
    Raises:
        FileNotFoundError: If file doesn't exist
        RuntimeError: If PIL is not available or image cannot be loaded
    """
    if not PIL_AVAILABLE:
        raise RuntimeError("PIL/Pillow not available")
    
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Image file not found: {path}")
    
    try:
        pil_image = Image.open(str(path))
        # Convert to RGB if needed (handles RGBA, P, etc.)
        if pil_image.mode != "RGB":
            pil_image = pil_image.convert("RGB")
        return pil_to_numpy(pil_image)
    except Exception as e:
        raise RuntimeError(f"Failed to load image from {path}: {e}") from e


def extract_images_from_pdf(pdf_path: Path, dpi: int = 300) -> list[np.ndarray]:
    """Extract all pages from PDF as images.
    
    Args:
        pdf_path: Path to PDF file
        dpi: Resolution for image conversion (default: 300)
    
    Returns:
        List of images as numpy arrays (one per page)
    
    Raises:
        FileNotFoundError: If PDF doesn't exist
        RuntimeError: If required libraries are not available
    """
    if not FITZ_AVAILABLE:
        raise RuntimeError("PyMuPDF (fitz) not available")
    if not PIL_AVAILABLE:
        raise RuntimeError("PIL/Pillow not available")
    
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    
    images = []
    doc = fitz.open(str(pdf_path))
    
    try:
        for page_index in range(len(doc)):
            page = doc[page_index]
            
            # Convert page to image
            zoom = dpi / 72.0
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB, alpha=False, annots=False)
            img_data = pix.tobytes("png")
            
            # Convert to numpy array
            pil_image = Image.open(io.BytesIO(img_data))
            if pil_image.mode != "RGB":
                pil_image = pil_image.convert("RGB")
            image_array = pil_to_numpy(pil_image)
            images.append(image_array)
            
            # Clean up
            pix = None
            gc.collect()
        
        return images
    finally:
        doc.close()


def process_image(
    image: np.ndarray,
    lang: str = "por+eng",
    use_paddleocr: bool = True,
    use_easyocr: bool = False
) -> ProcessedDocumentResult:
    """Process a single image through the full pipeline: coarse rotation, deskew, multi-engine OCR.
    
    Args:
        image: Input image as numpy array
        lang: Language code for OCR
        use_paddleocr: Whether to use PaddleOCR as secondary engine
        use_easyocr: Whether to use EasyOCR as secondary engine (if PaddleOCR unavailable)
    
    Returns:
        ProcessedDocumentResult with final text and metadata
    """
    # Step 1: Coarse rotation
    rotated_image, rotation_info = coarse_rotate(image)
    total_rotation = rotation_info.angle
    
    # Step 2: Deskew
    deskewed_image, skew_angle = deskew_image(rotated_image)
    total_rotation += skew_angle
    
    # Step 3: Run multi-engine OCR
    ocr_results = []
    
    # Always run Tesseract
    tesseract_result = run_ocr_tesseract(deskewed_image, lang=lang, rotation_applied=total_rotation)
    ocr_results.append(tesseract_result)
    
    # Run secondary engine if available
    if use_paddleocr and PADDLEOCR_AVAILABLE:
        paddle_result = run_ocr_paddleocr(deskewed_image, lang="por", rotation_applied=total_rotation)
        ocr_results.append(paddle_result)
    elif use_easyocr and EASYOCR_AVAILABLE:
        easy_result = run_ocr_easyocr(deskewed_image, lang=["pt", "en"], rotation_applied=total_rotation)
        ocr_results.append(easy_result)
    
    # Step 4: Select best result
    best_result = select_best_ocr_result(ocr_results)
    
    logger.info(
        "Image processing complete: engine=%s, coarse_rotation=%.1f°, deskew=%.2f°, "
        "total_rotation=%.2f°, text_length=%d",
        best_result.engine_name,
        rotation_info.angle,
        skew_angle,
        total_rotation,
        len(best_result.text)
    )
    
    return ProcessedDocumentResult(
        text=best_result.text,
        engine_used=best_result.engine_name,
        coarse_rotation_angle=rotation_info.angle,
        deskew_angle=skew_angle,
        all_engine_results=ocr_results
    )


def process_document(
    path: Path,
    lang: str = "por+eng",
    use_paddleocr: bool = True,
    use_easyocr: bool = False
) -> ProcessedDocumentResult:
    """Process a document (PDF or image) through the full pipeline.
    
    Args:
        path: Path to PDF or image file
        lang: Language code for OCR
        use_paddleocr: Whether to use PaddleOCR as secondary engine
        use_easyocr: Whether to use EasyOCR as secondary engine
    
    Returns:
        ProcessedDocumentResult with final text and metadata
        For PDFs, text from all pages is joined with newlines
    """
    path = Path(path)
    
    # Determine if PDF or image
    is_pdf = path.suffix.lower() == ".pdf"
    
    if is_pdf:
        # Extract images from PDF
        page_images = extract_images_from_pdf(path, dpi=300)
        
        if not page_images:
            logger.warning("PDF %s has no pages", path.name)
            return ProcessedDocumentResult(
                text="",
                engine_used="none",
                coarse_rotation_angle=0.0,
                deskew_angle=0.0,
                all_engine_results=[]
            )
        
        # Process each page
        page_texts = []
        all_results = []
        total_coarse_rotation = 0.0
        total_deskew = 0.0
        
        for page_idx, page_image in enumerate(page_images):
            logger.info("Processing PDF page %d/%d", page_idx + 1, len(page_images))
            page_result = process_image(
                page_image,
                lang=lang,
                use_paddleocr=use_paddleocr,
                use_easyocr=use_easyocr
            )
            page_texts.append(page_result.text)
            all_results.extend(page_result.all_engine_results)
            total_coarse_rotation += page_result.coarse_rotation_angle
            total_deskew += page_result.deskew_angle
        
        # Combine results
        combined_text = "\n\n".join(page_texts)
        avg_coarse_rotation = total_coarse_rotation / len(page_images)
        avg_deskew = total_deskew / len(page_images)
        
        # Use the engine from the first page (or most common)
        engine_used = page_result.engine_used if page_images else "none"
        
        logger.info(
            "PDF processing complete: %d pages, engine=%s, avg_coarse_rotation=%.1f°, "
            "avg_deskew=%.2f°, total_text_length=%d",
            len(page_images),
            engine_used,
            avg_coarse_rotation,
            avg_deskew,
            len(combined_text)
        )
        
        return ProcessedDocumentResult(
            text=combined_text,
            engine_used=engine_used,
            coarse_rotation_angle=avg_coarse_rotation,
            deskew_angle=avg_deskew,
            all_engine_results=all_results
        )
    else:
        # Process single image
        image = load_image_from_path(path)
        return process_image(image, lang=lang, use_paddleocr=use_paddleocr, use_easyocr=use_easyocr)

