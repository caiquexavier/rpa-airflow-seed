"""Standalone test script for PDF rotation function from pdf_functions_operator.py"""

import io
import logging
import os
import re
from pathlib import Path
from typing import Optional

try:
    import fitz  # PyMuPDF
    from PIL import Image
    import pytesseract

    OCR_AVAILABLE = True
except ImportError as e:
    OCR_AVAILABLE = False
    print(f"Warning: OCR libraries not available: {e}")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class RotationTester:
    """Standalone test class that replicates rotation logic from PdfFunctionsOperator."""
    
    def __init__(self, output_dir: Path, osd_confidence_threshold: float = 3.0):
        self.output_dir = output_dir
        self.osd_confidence_threshold = osd_confidence_threshold
    
    def rotate_pdfs(self, files: list[Path]) -> list[Path]:
        """Rotate PDFs until they are readable (based on OCR scoring)."""
        if not files:
            return []

        if not OCR_AVAILABLE:
            logger.warning("OCR not available. Skipping rotation step.")
            return list(files)

        rotated_files: list[Path] = []
        for pdf_path in files:
            logger.info("Rotating PDF file: %s", pdf_path)
            doc = fitz.open(str(pdf_path))
            try:
                if len(doc) == 0:
                    logger.warning("PDF %s has no pages. Skipping rotation.", pdf_path)
                    continue

                changed = False
                for index in range(len(doc)):
                    page = doc[index]
                    current_rotation = page.rotation % 360
                    dpi = self._calculate_dpi(page.rect)
                    best_rotation = self._detect_best_rotation(page, dpi)
                    logger.info(f"  Page {index + 1}: current={current_rotation}°, detected_best={best_rotation}°")
                    
                    # best_rotation is the clockwise rotation the PAGE needs to be readable
                    # PyMuPDF set_rotation sets absolute rotation, so we set it directly
                    # But we need to account for current rotation: if page is at 90° and needs 0°, set to 0°
                    if best_rotation != 0:
                        # best_rotation is the target absolute rotation for the page
                        # So we set it directly (PyMuPDF handles the rotation correctly)
                        if best_rotation != current_rotation:
                            page.set_rotation(best_rotation)
                            changed = True
                            logger.info(f"  Page {index + 1}: Applied rotation from {current_rotation}° to {best_rotation}°")
                        else:
                            logger.info(f"  Page {index + 1}: Already at optimal rotation {best_rotation}°")
                    else:
                        # If 0° is best but page is rotated, rotate it back to 0°
                        if current_rotation != 0:
                            page.set_rotation(0)
                            changed = True
                            logger.info(f"  Page {index + 1}: Rotating from {current_rotation}° back to 0° (optimal)")
                        else:
                            logger.info(f"  Page {index + 1}: No rotation needed (already at 0°)")

                target_path = self.output_dir / pdf_path.name
                if not changed:
                    logger.info("No rotation changes detected for %s", pdf_path)
                self._save_document(doc, target_path)
                rotated_files.append(target_path)
            finally:
                doc.close()

        return rotated_files

    def _detect_best_rotation(self, page, dpi: int) -> int:
        """Detect the best rotation angle for a PDF page by testing OCR at different angles."""
        if not OCR_AVAILABLE:
            return 0

        zoom = dpi / 72.0
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False, colorspace=fitz.csRGB)
        base_image = self._image_from_pixmap(pix)

        rotations = [0, 90, 180, 270]
        osd_rotation = self._detect_rotation_via_osd(base_image)
        if osd_rotation is not None and osd_rotation not in rotations:
            rotations.append(osd_rotation)
        elif osd_rotation is not None:
            rotations = [osd_rotation] + [r for r in rotations if r != osd_rotation]

        scores: dict[int, float] = {}
        try:
            for rotation in rotations:
                if rotation == 0:
                    test_image = base_image.copy()
                else:
                    # Key insight: We test what rotation the IMAGE needs to be readable
                    # If rotating image 90° CCW (PIL rotate(90)) makes it readable,
                    # that means the page content is rotated 90° CW, so we rotate page 90° CCW (or 270° CW)
                    # But PyMuPDF rotates clockwise, so 90° CCW = 270° CW
                    # Actually simpler: if image needs X° CCW to read, page needs X° CW to fix
                    # PIL rotate(angle) = CCW, so rotate(90) = 90° CCW
                    # If that scores well, page needs 90° CW rotation = set_rotation(90)
                    # So we use positive rotation directly: rotate(rotation) tests "page needs rotation° CW"
                    test_image = base_image.rotate(rotation, expand=True)
                score = self._score_image(test_image)
                scores[rotation] = score
                logger.info(f"    Testing: if image rotated {rotation}° CCW is readable → page needs {rotation}° CW: score={score}")
                if rotation != 0:
                    test_image.close()
        finally:
            base_image.close()

        base_score = scores.get(0, 0.0)
        min_improvement = max(base_score * 0.1, 5)
        best_rotation = max(scores.items(), key=lambda item: item[1])[0]
        best_score = scores.get(best_rotation, base_score)

        logger.info(f"    Scoring results - Base (0°): {base_score}, Best: {best_rotation}° (score={best_score}), Min improvement needed: {min_improvement}")
        
        # Only apply rotation if it significantly improves readability
        if best_rotation != 0 and best_score >= base_score + min_improvement:
            logger.info(f"    ✓ Rotation {best_rotation}° will be applied (improvement: {best_score - base_score:.1f})")
            return best_rotation
        else:
            if best_rotation != 0:
                logger.info(f"    ✗ Rotation {best_rotation}° not applied (improvement {best_score - base_score:.1f} < min {min_improvement})")
            else:
                logger.info(f"    ✓ No rotation needed (0° is optimal)")
        return 0

    @staticmethod
    def _calculate_dpi(page_rect) -> int:
        """Calculate adaptive DPI based on page size."""
        area = page_rect.width * page_rect.height
        return 200 if area > 1_000_000 else (250 if area > 500_000 else 300)

    @staticmethod
    def _image_from_pixmap(pix: "fitz.Pixmap") -> Image.Image:
        """Create an RGB PIL.Image from a pixmap, ensuring proper mode."""
        image = Image.open(io.BytesIO(pix.tobytes("png")))
        if image.mode == "RGB":
            return image
        converted = image.convert("RGB")
        image.close()
        return converted

    @staticmethod
    def _score_image(image: Image.Image) -> int:
        """Score how readable an image is using OCR output."""
        if not OCR_AVAILABLE:
            return 0

        # Try multiple PSM modes for better detection
        texts = []
        for psm in [6, 3, 11]:
            try:
                text_por = pytesseract.image_to_string(
                    image, lang="por", config=f"--oem 3 --psm {psm}"
                )
                if text_por.strip():
                    texts.append(text_por)
                else:
                    text_eng = pytesseract.image_to_string(
                        image, lang="eng", config=f"--oem 3 --psm {psm}"
                    )
                    if text_eng.strip():
                        texts.append(text_eng)
            except Exception:
                continue
        
        if not texts:
            return 0
        
        # Use the text with most content
        text = max(texts, key=len)
        
        # More aggressive scoring
        words = len(re.findall(r"[A-Za-z]{2,}", text))  # Reduced from 3 to 2
        numbers = len(re.findall(r"\d{3,}", text))  # Reduced from 4 to 3
        alphanumeric = len(re.findall(r"[A-Za-z0-9]", text))
        
        # Bonus for longer sequences
        long_words = len(re.findall(r"[A-Za-z]{5,}", text))
        long_numbers = len(re.findall(r"\d{5,}", text))
        
        score = words * 10 + numbers * 5 + alphanumeric + long_words * 5 + long_numbers * 3
        
        # Log first 100 chars for debugging
        text_preview = text[:100].replace('\n', ' ').strip()
        if text_preview:
            logger.debug(f"      OCR preview: {text_preview}...")
        
        return score

    def _detect_rotation_via_osd(self, image: Image.Image) -> Optional[int]:
        """Use Tesseract OSD to determine the required rotation, if confidence is high."""
        if not OCR_AVAILABLE:
            return None

        try:
            osd_result = pytesseract.image_to_osd(image, config="--psm 0")
        except Exception as exc:
            logger.debug("OSD detection failed: %s", exc)
            return None

        angle_match = re.search(r"Orientation in degrees:\s+(\d+)", osd_result)
        rotate_match = re.search(r"Rotate:\s+(\d+)", osd_result)
        confidence_match = re.search(r"Orientation confidence:\s+([\d\.]+)", osd_result)

        if not angle_match or not rotate_match:
            return None

        try:
            rotation = int(rotate_match.group(1)) % 360
            confidence = float(confidence_match.group(1)) if confidence_match else 0.0
        except ValueError:
            return None

        if confidence < self.osd_confidence_threshold:
            return None

        rotation = rotation if rotation in (0, 90, 180, 270) else 0
        return rotation

    def _save_document(self, doc: "fitz.Document", target_path: Path) -> None:
        """Persist document to disk using a temporary file to avoid in-place save errors."""
        temp_path = target_path.with_name(f"{target_path.stem}__tmp{target_path.suffix}")
        doc.save(str(temp_path), incremental=False)
        temp_path.replace(target_path)


def test_rotate_function():
    """Test the rotate function with files from downloads directory."""
    
    # Define paths
    workspace_root = Path(__file__).parent
    # Test with already processed files that might be incorrectly rotated
    downloads_dir = workspace_root / "shared" / "data" / "processar"
    output_dir = workspace_root / "shared" / "data" / "processar"
    
    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Get PDF files - prioritize split files (_1.pdf, _2.pdf) if they exist, otherwise all PDFs
    split_files = sorted(downloads_dir.glob("*_[0-9].pdf"))
    if split_files:
        pdf_files = split_files
        logger.info("Found split PDF files (likely already processed), testing rotation on these:")
    else:
        pdf_files = sorted(downloads_dir.glob("*.pdf"))
        logger.info("No split files found, testing all PDFs:")
    
    if not pdf_files:
        logger.error(f"No PDF files found in {downloads_dir}")
        return []
    
    logger.info(f"Found {len(pdf_files)} PDF file(s) to test rotation:")
    for pdf_file in pdf_files:
        logger.info(f"  - {pdf_file.name}")
    
    # Create tester instance
    tester = RotationTester(output_dir=output_dir)
    
    # Execute rotation
    logger.info("\n" + "="*60)
    logger.info("Testing rotation function")
    logger.info("="*60 + "\n")
    
    try:
        rotated_files = tester.rotate_pdfs(pdf_files)
        
        logger.info("\n" + "="*60)
        logger.info("Rotation test completed!")
        logger.info("="*60)
        logger.info(f"\nProcessed {len(rotated_files)} file(s):")
        for rotated_file in rotated_files:
            file_path = Path(rotated_file)
            if file_path.exists():
                size_mb = file_path.stat().st_size / (1024 * 1024)
                logger.info(f"  ✓ {file_path.name} ({size_mb:.2f} MB) -> {file_path}")
            else:
                logger.warning(f"  ✗ {rotated_file} (file not found)")
        
        return rotated_files
        
    except Exception as e:
        logger.error(f"Rotation test failed: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    test_rotate_function()
