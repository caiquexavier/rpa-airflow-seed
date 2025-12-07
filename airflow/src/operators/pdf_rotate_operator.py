"""PDF Rotate Operator - Simple OCR-based rotation for PNG images."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional

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

from airflow.exceptions import AirflowException
from airflow.models import BaseOperator
from airflow.utils.context import Context

from services.saga import (
    build_saga_event,
    get_saga_from_context,
    log_saga,
    send_saga_event_to_api,
)

logger = logging.getLogger(__name__)

# Constants
VALID_ROTATIONS = {0, 90, 180, 270}
OSD_MIN_CONFIDENCE = 2.0


def detect_rotation_osd(image: Image.Image) -> tuple[int, float]:
    """Detect rotation using Tesseract OSD.
    
    Args:
        image: PIL Image to analyze
        
    Returns:
        Tuple of (rotation_angle, confidence)
        rotation_angle: 0, 90, 180, or 270 degrees (counterclockwise)
        confidence: OSD confidence score
    """
    if not TESSERACT_AVAILABLE:
        return (0, 0.0)
    
    try:
        osd_result = pytesseract.image_to_osd(image, output_type=pytesseract.Output.DICT)
        osd_rotate = int(osd_result.get("rotate", 0))
        osd_conf = float(osd_result.get("script_conf", 0))
        
        if osd_conf > OSD_MIN_CONFIDENCE and osd_rotate in VALID_ROTATIONS:
            # Tesseract returns clockwise rotation, convert to counterclockwise
            rotation_angle = (360 - osd_rotate) % 360
            return (rotation_angle, osd_conf)
        
        return (0, osd_conf)
    except Exception as e:
        logger.debug("OSD detection failed: %s", e)
        return (0, 0.0)


def check_document_orientation(image: Image.Image) -> dict:
    """Check if document is correctly oriented by analyzing header/footer positions.
    
    Returns a dict with orientation indicators including aspect ratio check.
    """
    if not TESSERACT_AVAILABLE:
        return {"is_correct": True, "headers_at_top": 0, "footers_at_top": 0, "headers_at_end": 0, "is_landscape": True}
    
    try:
        # Check aspect ratio - documents should be landscape (width > height)
        width, height = image.size
        is_landscape = width > height
        
        text = pytesseract.image_to_string(image, lang="por+eng", config="--oem 3 --psm 6")
        text_lower = text.strip().lower()
        words = text_lower.split()
        
        if len(words) < 10:
            return {"is_correct": True, "headers_at_top": 0, "footers_at_top": 0, "headers_at_end": 0, "is_landscape": is_landscape}
        
        header_keywords = ['comprovante', 'entrega', 'unilever', 'transportadora', 'dados', 'nf-e', 'nota', 'fiscal']
        footer_keywords = ['conferente', 'assinatura', 'nome', 'telefone', 'retorno', 'mercadorias', 'não', 'entregues']
        
        # Check first 40 words (more for better detection)
        first_words = ' '.join(words[:40])
        headers_at_top = sum(1 for kw in header_keywords if kw in first_words)
        footers_at_top = sum(1 for kw in footer_keywords if kw in first_words)
        
        # Check last 40 words
        headers_at_end = 0
        if len(words) >= 40:
            last_words = ' '.join(words[-40:])
            headers_at_end = sum(1 for kw in header_keywords if kw in last_words)
        
        # Document is correct if:
        # 1. Headers are at top (>= 2)
        # 2. Footers are NOT at top
        # 3. Document is landscape orientation (width > height)
        is_correct = headers_at_top >= 2 and footers_at_top == 0 and is_landscape
        
        return {
            "is_correct": is_correct,
            "headers_at_top": headers_at_top,
            "footers_at_top": footers_at_top,
            "headers_at_end": headers_at_end,
            "is_landscape": is_landscape
        }
    except Exception as e:
        logger.debug("Orientation check failed: %s", e)
        return {"is_correct": True, "headers_at_top": 0, "footers_at_top": 0, "headers_at_end": 0, "is_landscape": True}


def detect_rotation_best_of_four(image: Image.Image) -> int:
    """Detect rotation ensuring all documents end up in same correct position.
    
    Strategy:
    1. Check if original (0°) is already correct (landscape + headers at top)
    2. If correct, return 0°
    3. Test 90° and 270° (portrait rotations) - prefer the one that makes it landscape
    4. Only use 180° as absolute last resort
    
    Args:
        image: PIL Image to analyze
        
    Returns:
        Best rotation angle: 0, 90, 180, or 270 degrees (counterclockwise)
    """
    if not TESSERACT_AVAILABLE:
        return 0
    
    # STEP 1: Check if original image (0°) is already correctly oriented
    orientation_0 = check_document_orientation(image)
    if orientation_0["is_correct"]:
        logger.info("Document at 0° is already correctly oriented (landscape, headers at top: %d)", 
                   orientation_0["headers_at_top"])
        return 0
    
    # STEP 2: Original is not correct, test rotations
    logger.info("Document at 0° is not correctly oriented (landscape: %s, headers at top: %d), testing rotations", 
               orientation_0["is_landscape"], orientation_0["headers_at_top"])
    
    best_rotation = 0
    best_score = -1.0
    rotation_results = {}
    
    # Test rotations: 90, 270 first (portrait rotations), then 180 (last resort)
    for rotation in [90, 270, 180]:
        try:
            test_image = image.rotate(-rotation, expand=True, fillcolor='white')
            
            # Check orientation after rotation
            orientation = check_document_orientation(test_image)
            
            # Get OCR confidence
            try:
                data = pytesseract.image_to_data(test_image, lang="por+eng", config="--oem 3 --psm 6", output_type=pytesseract.Output.DICT)
                confidences = [int(conf) for conf in data.get("conf", []) if conf != "-1" and int(conf) > 0]
                avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
            except Exception:
                avg_confidence = 0.0
            
            # Score based on orientation correctness
            score = 0.0
            
            # CRITICAL: Must be landscape AND have headers at top AND no footers at top
            if orientation["is_landscape"] and orientation["headers_at_top"] >= 2 and orientation["footers_at_top"] == 0:
                # Perfect score for correct orientation
                score = 200.0 + (orientation["headers_at_top"] * 30.0) + avg_confidence
                logger.info("Rotation %d°: CORRECT orientation (landscape, headers at top: %d, footers at top: %d, confidence: %.1f)", 
                           rotation, orientation["headers_at_top"], orientation["footers_at_top"], avg_confidence)
            elif orientation["is_landscape"] and orientation["headers_at_top"] >= 1:
                # Partial score if landscape with some headers
                score = 50.0 + (orientation["headers_at_top"] * 10.0) + avg_confidence * 0.5
                logger.debug("Rotation %d°: PARTIAL (landscape, headers at top: %d)", 
                            rotation, orientation["headers_at_top"])
            else:
                # Low score if not correct
                score = avg_confidence * 0.3
                logger.debug("Rotation %d°: INCORRECT (landscape: %s, headers at top: %d, footers at top: %d)", 
                            rotation, orientation["is_landscape"], orientation["headers_at_top"], orientation["footers_at_top"])
            
            # HEAVY penalty for 180° - only use if others don't work
            if rotation == 180:
                score = score * 0.2  # Reduce score by 80%
                logger.warning("Rotation 180°: Applying heavy penalty (score reduced to %.1f)", score)
            
            # Penalty if portrait (not landscape)
            if not orientation["is_landscape"]:
                score = score * 0.1  # Heavy penalty for portrait
                logger.debug("Rotation %d°: Portrait orientation penalty applied", rotation)
            
            rotation_results[rotation] = {
                "score": score,
                "orientation": orientation,
                "confidence": avg_confidence
            }
            
            if score > best_score:
                best_score = score
                best_rotation = rotation
                
        except Exception as e:
            logger.debug("Rotation %d° test failed: %s", rotation, e)
            continue
    
    # STEP 3: Final decision - ensure we get correct orientation
    if best_rotation != 0:
        best_result = rotation_results[best_rotation]
        # Only accept if it produces correct orientation (landscape + headers at top)
        if best_result["orientation"]["is_correct"]:
            logger.info("Best rotation: %d° (correct orientation: landscape, headers at top, score: %.1f)", 
                       best_rotation, best_score)
            return best_rotation
        else:
            # Best rotation doesn't produce correct orientation
            logger.warning("Best rotation %d° doesn't produce correct orientation (landscape: %s, headers: %d). Checking 0°", 
                          best_rotation, best_result["orientation"]["is_landscape"], best_result["orientation"]["headers_at_top"])
            
            # If 0° is landscape (even if headers not perfect), prefer it
            if orientation_0["is_landscape"]:
                logger.info("Preferring 0° (landscape orientation) over incorrect rotation %d°", best_rotation)
                return 0
    
    # If no good rotation found, return 0° (no rotation)
    logger.info("No good rotation found, returning 0° (no rotation)")
    return 0


def validate_rotation(image: Image.Image, rotation: int) -> bool:
    """Validate rotation using orientation check.
    
    Args:
        image: PIL Image to validate
        rotation: Rotation angle to validate
        
    Returns:
        True if rotation produces correct orientation, False otherwise
    """
    if rotation == 0:
        return True
    
    try:
        test_image = image.rotate(-rotation, expand=True, fillcolor='white')
        orientation = check_document_orientation(test_image)
        
        # Reject 180° unless absolutely perfect
        if rotation == 180:
            if not orientation["is_correct"] or orientation["footers_at_top"] > 0:
                logger.warning("Rotation 180°: Does not produce correct orientation, rejecting")
                return False
        
        return orientation["is_correct"]
    except Exception as e:
        logger.debug("Rotation validation failed: %s", e)
        if rotation == 180:
            return False
        return True


def detect_rotation(image: Image.Image) -> int:
    """Detect required rotation for image using OCR.
    
    Conservative approach: heavily penalizes 180° rotations to avoid upside-down documents.
    
    Args:
        image: PIL Image to analyze
        
    Returns:
        Rotation angle: 0, 90, 180, or 270 degrees (counterclockwise)
    """
    # Try OSD first
    rotation, confidence = detect_rotation_osd(image)
    
    if rotation != 0 and confidence > OSD_MIN_CONFIDENCE:
        logger.info("OSD detected rotation: %d° (confidence: %.2f)", rotation, confidence)
        
        # Reject 180° from OSD - too risky
        if rotation == 180:
            logger.warning("OSD detected 180° rotation - REJECTING to avoid upside-down documents")
            rotation = 0
        else:
            # For 90/270, check if rotation produces correct orientation (landscape + headers at top)
            try:
                test_image = image.rotate(-rotation, expand=True, fillcolor='white')
                orientation = check_document_orientation(test_image)
                
                # Must be landscape AND have headers at top
                if orientation["is_correct"]:
                    logger.info("OSD rotation %d° produces correct orientation (landscape, headers at top), accepting", rotation)
                    return rotation
                else:
                    logger.warning("OSD rotation %d° does not produce correct orientation (landscape: %s, headers: %d), rejecting", 
                                  rotation, orientation["is_landscape"], orientation["headers_at_top"])
                    rotation = 0
            except Exception as e:
                logger.debug("OSD rotation validation failed: %s, rejecting", e)
                rotation = 0
        
        if rotation != 0:
            return rotation
        else:
            logger.info("OSD rotation rejected, falling back to best-of-four")
    
    # Fallback to best-of-four
    logger.info("OSD failed or low confidence, trying best-of-four rotations")
    rotation = detect_rotation_best_of_four(image)
    
    if rotation != 0:
        logger.info("Best-of-four selected rotation: %d°", rotation)
        # Always validate, especially for 180°
        if not validate_rotation(image, rotation):
            logger.warning("Best-of-four rotation %d° failed validation", rotation)
            # Try 0° first as fallback
            if validate_rotation(image, 0):
                logger.info("Falling back to 0° (no rotation)")
                return 0
            # If 0° also fails validation, try other rotations (90, 270) before 180°
            for alt_rotation in [90, 270]:
                if validate_rotation(image, alt_rotation):
                    logger.info("Falling back to %d° rotation", alt_rotation)
                    return alt_rotation
            # Last resort: return 0 even if validation is uncertain
            logger.warning("All rotations failed validation, defaulting to 0°")
            return 0
    
    # Return the detected rotation (could be 0 if no rotation needed)
    return rotation


class PdfRotateOperator(BaseOperator):
    """Operator that rotates PNG images to readable position using OCR."""

    def __init__(
        self,
        folder_path: str,
        output_dir: Optional[str] = None,
        overwrite: bool = True,
        subdirectory: str = "rotated",
        task_id: Optional[str] = None,
        **kwargs,
    ) -> None:
        super().__init__(task_id=task_id, **kwargs)
        self.folder_path = Path(folder_path)
        base_output_dir = Path(output_dir) if output_dir else self.folder_path
        self.output_dir = base_output_dir / subdirectory
        self.overwrite = overwrite

    def execute(self, context: Context) -> List[str]:
        """Execute PNG image rotation."""
        logger.info("Starting PdfRotateOperator for folder: %s", self.folder_path)

        saga = get_saga_from_context(context)

        if not self.folder_path.exists() or not self.folder_path.is_dir():
            raise AirflowException(
                f"Folder path {self.folder_path} does not exist or is not a directory."
            )

        png_files = sorted(self.folder_path.glob("*.png"))
        if not png_files:
            logger.warning("No PNG files found at %s", self.folder_path)
            if saga:
                self._update_saga_with_event(saga, context, success=True, files_count=0)
            return []

        if not PIL_AVAILABLE:
            raise RuntimeError("PIL/Pillow not available. Install Pillow to rotate PNG images.")

        if not TESSERACT_AVAILABLE:
            raise RuntimeError("Tesseract OCR not available. Install pytesseract and tesseract-ocr.")

        is_same_folder = self.folder_path.resolve() == self.output_dir.resolve()
        
        if not is_same_folder:
            self._clean_output_folder()

        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        rotated_paths = self._rotate_images(png_files)
        generated_files = [str(path) for path in rotated_paths]

        logger.info(
            "PdfRotateOperator produced %d rotated PNG image(s) from %d input file(s).",
            len(generated_files),
            len(png_files),
        )

        if saga:
            self._update_saga_with_event(
                saga, context, success=True, files_count=len(generated_files)
            )

        return generated_files

    def _clean_output_folder(self) -> None:
        """Clean the output folder by removing all PNG files."""
        if not self.output_dir.exists():
            return

        png_files = list(self.output_dir.glob("*.png"))
        if not png_files:
            return

        logger.info("Cleaning output folder: removing %d PNG file(s)", len(png_files))
        for png_file in png_files:
            try:
                png_file.unlink()
            except Exception as e:
                logger.warning("Failed to remove file %s: %s", png_file.name, e)

    def _rotate_images(self, files: List[Path]) -> List[Path]:
        """Rotate PNG images to readable position using OCR."""
        if not files:
            return []

        rotated_paths: List[Path] = []

        for image_path in files:
            image_path = Path(image_path)
            try:
                rotated_path = self._rotate_single_image(image_path)
                rotated_paths.append(rotated_path)
                logger.info("Successfully rotated PNG: %s -> %s", image_path.name, rotated_path.name)
            except Exception as e:
                logger.error("Failed to rotate PNG %s: %s", image_path.name, e)
                continue

        return rotated_paths

    def _rotate_single_image(self, image_path: Path) -> Path:
        """Rotate a single PNG image to readable position using OCR."""
        logger.info("Rotating PNG image: %s", image_path.name)

        if not image_path.exists():
            raise FileNotFoundError(f"PNG image not found: {image_path}")

        # Clean filename: remove _split or split_ patterns
        original_name = image_path.name
        # Remove _split pattern (e.g., "split_471586.png" -> "471586.png")
        cleaned_name = original_name.replace("_split", "").replace("split_", "")
        # Also handle cases where rotate_ prefix already exists
        if cleaned_name.startswith("rotate_"):
            cleaned_name = cleaned_name.replace("rotate_", "", 1)
        
        output_filename = f"rotate_{cleaned_name}"
        output_path = self.output_dir / output_filename

        # Load image
        image = Image.open(str(image_path))
        try:
            # Detect rotation with error handling
            try:
                rotation_angle = detect_rotation(image)
                logger.info("Detected rotation angle: %d°", rotation_angle)
            except Exception as e:
                logger.error("Rotation detection failed for %s: %s. Using 0° (no rotation)", image_path.name, e)
                rotation_angle = 0
            
            # Apply rotation if needed
            if rotation_angle != 0:
                logger.info("Applying rotation: %d°", rotation_angle)
                try:
                    image = image.rotate(-rotation_angle, expand=True, fillcolor='white')
                except Exception as e:
                    logger.error("Failed to apply rotation %d° to %s: %s", rotation_angle, image_path.name, e)
                    raise
            
            # Save rotated image
            output_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                image.save(str(output_path), format='PNG', optimize=False)
            except Exception as e:
                logger.error("Failed to save rotated image %s: %s", output_path, e)
                raise
            
            if not output_path.exists():
                raise RuntimeError(f"Failed to save rotated PNG to {output_path}")
            if output_path.stat().st_size == 0:
                raise RuntimeError(f"Rotated PNG file is empty: {output_path}")
            
            logger.info("Saved rotated PNG: %s (%d bytes)", output_path.name, output_path.stat().st_size)
            return output_path
            
        finally:
            image.close()

    def _update_saga_with_event(
        self,
        saga: dict,
        context: Context,
        success: bool,
        files_count: int,
    ) -> None:
        """Update SAGA with PDF rotation event and push to XCom."""
        if not saga or not saga.get("saga_id"):
            return
        
        if "events" not in saga:
            saga["events"] = []
        
        event = build_saga_event(
            event_type="TaskCompleted" if success else "TaskFailed",
            event_data={
                "step": "pdf_rotate",
                "status": "SUCCESS" if success else "FAILED",
                "files_generated": files_count,
                "input_folder": str(self.folder_path),
                "output_folder": str(self.output_dir)
            },
            context=context,
            task_id=self.task_id
        )
        saga["events"].append(event)
        
        send_saga_event_to_api(saga, event, rpa_api_conn_id="rpa_api")
        
        saga["events_count"] = len(saga["events"])
        
        if success:
            saga["current_state"] = "RUNNING"
        
        task_instance = context.get('task_instance')
        if task_instance:
            task_instance.xcom_push(key="saga", value=saga)
            task_instance.xcom_push(key="rpa_payload", value=saga)
        
        log_saga(saga, task_id=self.task_id)
