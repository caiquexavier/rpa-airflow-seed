"""PDF OCR NF-E Extractor Operator - Extracts NF-E numbers from rotated PNG images using OCR."""

from __future__ import annotations

import logging
import re
import shutil
from pathlib import Path
from typing import List, Optional

try:
    from PIL import Image, ImageOps
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


def extract_nf_e_from_text(text: str) -> Optional[str]:
    """Extract NF-e number from OCR text - look for NF-E label followed by number.
    
    Args:
        text: OCR text from image (should be from NF-E box region)
        
    Returns:
        NF-e number as string with leading zeros trimmed, or None if not found
    """
    if not text:
        return None
    
    # Normalize whitespace and convert to uppercase for matching
    cleaned = " ".join(text.split())
    cleaned_upper = cleaned.upper()
    
    # Pattern 1: Look for "NF-E" or "NFE" followed by number (most specific)
    # Common patterns: "NF-E 4921183", "NFE 4921183", "NF-E: 4921183", etc.
    # Try to find NF-E label first, then extract the number that follows
    nf_e_patterns = [
        r"NF[\s\-_]*E[\s\-_]*:?[\s\-_]*(\d{5,15})",  # NF-E: 4921183, NF E 4921183, etc.
        r"NF[\s\-_]*E[\s\-_]*(\d{5,15})",  # NF-E4921183 (no space or colon)
        r"NF[\s\-_]*E[\s\-_]*SERIE[\s\-_]*:?[\s\-_]*\d+[\s\-_]*(\d{5,15})",  # NF-E SERIE: 1 4921183
    ]
    
    for pattern in nf_e_patterns:
        matches = re.findall(pattern, cleaned_upper, re.IGNORECASE)
        if matches:
            # Get the first match and trim leading zeros
            nf_e = matches[0].lstrip("0")
            if not nf_e:
                nf_e = "0"
            
            # Validate length (NF-e numbers are typically 6-9 digits, but allow 5-15)
            if 5 <= len(nf_e) <= 15:
                logger.debug("Found NF-e using pattern '%s': %s", pattern, nf_e)
                return nf_e
    
    # Pattern 2: Look for lines that contain "NF" and a number (less specific)
    lines = cleaned.split('\n')
    for line in lines:
        line_upper = line.upper()
        if 'NF' in line_upper or 'NFE' in line_upper:
            # Extract numbers from this line
            numbers = re.findall(r'\d{5,15}', line)
            for num in numbers:
                nf_e = num.lstrip("0")
                if not nf_e:
                    nf_e = "0"
                if 5 <= len(nf_e) <= 15:
                    logger.debug("Found NF-e from line containing NF: %s", nf_e)
                    return nf_e
    
    # Pattern 3: If no NF-E label found, extract digits and validate
    # This is a fallback but should be avoided - prefer ROI that finds NF-E label
    digits_only = re.sub(r"\D", "", cleaned)
    
    if digits_only:
        # Trim leading zeros
        nf_e = digits_only.lstrip("0")
        if not nf_e:
            nf_e = "0"
        
        # Validate length (NF-e numbers are typically 5-15 digits)
        if 5 <= len(nf_e) <= 15:
            logger.debug("Found NF-e using digit extraction (no NF-E label found): %s (original: %s)", 
                        nf_e, digits_only)
            return nf_e
    
    return None


def extract_nf_e_from_image(image_path: Path) -> Optional[str]:
    """Extract NF-e number from PNG image using OCR with intelligent NF-E box detection.
    
    Strategy:
    1. Try multiple ROI regions (right side, upper right) where NF-E box typically appears
    2. Use pytesseract image_to_data to find "NF-E" text and its bounding box
    3. Extract number near the NF-E label
    4. Fallback to full-page OCR if ROI doesn't work
    
    Args:
        image_path: Path to PNG image
        
    Returns:
        NF-e number as string with leading zeros trimmed, or None if not found
    """
    if not PIL_AVAILABLE or not TESSERACT_AVAILABLE:
        logger.warning("PIL or Tesseract not available, cannot extract NF-e from %s", image_path.name)
        return None
    
    try:
        # Load image
        image = Image.open(str(image_path))
        
        try:
            # Get image dimensions
            img_width, img_height = image.size
            logger.debug("Image dimensions: %dx%d", img_width, img_height)
            
            # Define multiple ROI regions to try (right side of document where NF-E box appears)
            # Try different regions to handle varying document layouts
            roi_regions = [
                # Primary: Upper right quadrant (typical NF-E box location)
                {
                    "name": "upper_right",
                    "x_start": int(img_width * 0.6),  # 60% from left
                    "x_end": img_width,
                    "y_start": 0,
                    "y_end": int(img_height * 0.4),  # Top 40%
                },
                # Secondary: Right side middle
                {
                    "name": "right_middle",
                    "x_start": int(img_width * 0.65),
                    "x_end": img_width,
                    "y_start": int(img_height * 0.2),
                    "y_end": int(img_height * 0.5),
                },
                # Tertiary: Right side upper (more specific)
                {
                    "name": "right_upper",
                    "x_start": int(img_width * 0.7),
                    "x_end": img_width,
                    "y_start": int(img_height * 0.1),
                    "y_end": int(img_height * 0.35),
                },
            ]
            
            # Try each ROI region
            for roi in roi_regions:
                x_start = max(0, min(roi["x_start"], img_width - 1))
                x_end = min(roi["x_end"], img_width)
                y_start = max(0, min(roi["y_start"], img_height - 1))
                y_end = min(roi["y_end"], img_height)
                
                # Ensure valid crop box
                if x_start >= x_end or y_start >= y_end:
                    continue
                
                # Crop ROI region
                crop_box = (x_start, y_start, x_end, y_end)
                roi_image = image.crop(crop_box)
                
                try:
                    # Preprocess: Convert to grayscale
                    if roi_image.mode != "L":
                        roi_image = roi_image.convert("L")
                    
                    # Enhance contrast for better OCR accuracy
                    roi_image = ImageOps.autocontrast(roi_image)
                    
                    # Try multiple PSM modes for better extraction
                    psm_modes = ["6", "8", "11"]  # Uniform block, single word, sparse text
                    
                    for psm_mode in psm_modes:
                        try:
                            # Try with Portuguese + English first
                            try:
                                text = pytesseract.image_to_string(
                                    roi_image, lang="por+eng", config=f"--oem 3 --psm {psm_mode}"
                                )
                            except Exception:
                                # Fallback to Portuguese only
                                try:
                                    text = pytesseract.image_to_string(
                                        roi_image, lang="por", config=f"--oem 3 --psm {psm_mode}"
                                    )
                                except Exception:
                                    # Fallback to English only
                                    text = pytesseract.image_to_string(
                                        roi_image, lang="eng", config=f"--oem 3 --psm {psm_mode}"
                                    )
                            
                            if not text or not text.strip():
                                continue
                            
                            logger.debug(
                                "OCR from %s ROI (PSM %s): %s",
                                roi["name"], psm_mode, text[:150]
                            )
                            
                            # Extract NF-e from text
                            nf_e = extract_nf_e_from_text(text)
                            
                            if nf_e:
                                logger.info(
                                    "Extracted NF-e %s from %s using %s ROI (PSM %s, region: %d,%d-%d,%d)",
                                    nf_e, image_path.name, roi["name"], psm_mode,
                                    x_start, y_start, x_end, y_end
                                )
                                return nf_e
                                
                        except Exception as e:
                            logger.debug("PSM %s failed for %s ROI of %s: %s", 
                                       psm_mode, roi["name"], image_path.name, e)
                            continue
                            
                finally:
                    roi_image.close()
            
            # Fallback: Try full-page OCR if ROI regions didn't work
            logger.info("ROI extraction failed for %s, trying full-page OCR", image_path.name)
            
            # Preprocess full image
            full_image = image.copy()
            if full_image.mode != "L":
                full_image = full_image.convert("L")
            full_image = ImageOps.autocontrast(full_image)
            
            try:
                # Try full-page OCR
                try:
                    text = pytesseract.image_to_string(
                        full_image, lang="por+eng", config="--oem 3 --psm 6"
                    )
                except Exception:
                    text = pytesseract.image_to_string(
                        full_image, lang="por", config="--oem 3 --psm 6"
                    )
                
                if text:
                    logger.debug("Full-page OCR extracted %d characters: %s", 
                               len(text), text[:200])
                    nf_e = extract_nf_e_from_text(text)
                    if nf_e:
                        logger.info("Extracted NF-e %s from %s using full-page OCR", 
                                  nf_e, image_path.name)
                        return nf_e
                        
            finally:
                full_image.close()
            
            logger.warning("Could not extract NF-e from %s after trying all methods", image_path.name)
            return None
            
        finally:
            image.close()
            
    except Exception as e:
        logger.error("Failed to extract NF-e from %s: %s", image_path.name, e)
        return None


class PdfOcrNfExtractorOperator(BaseOperator):
    """Operator that extracts NF-e numbers from rotated PNG images using OCR and copies them to processado folder."""

    def __init__(
        self,
        rotated_folder_path: str,
        processado_folder_path: str,
        overwrite: bool = True,
        task_id: Optional[str] = None,
        **kwargs,
    ) -> None:
        super().__init__(task_id=task_id, **kwargs)
        self.rotated_folder_path = Path(rotated_folder_path)
        self.processado_folder_path = Path(processado_folder_path)
        self.overwrite = overwrite

    def execute(self, context: Context) -> List[str]:
        """Execute NF-e extraction and file copying."""
        logger.info(
            "Starting PdfOcrNfExtractorOperator: reading from %s, copying to %s",
            self.rotated_folder_path,
            self.processado_folder_path,
        )

        saga = get_saga_from_context(context)

        if not PIL_AVAILABLE:
            raise RuntimeError("PIL/Pillow not available. Install Pillow to process PNG images.")

        if not TESSERACT_AVAILABLE:
            raise RuntimeError(
                "Tesseract OCR not available. Install pytesseract and tesseract-ocr."
            )

        if not self.rotated_folder_path.exists() or not self.rotated_folder_path.is_dir():
            raise AirflowException(
                f"Rotated folder path {self.rotated_folder_path} does not exist or is not a directory."
            )

        # Ensure processado folder exists
        self.processado_folder_path.mkdir(parents=True, exist_ok=True)
        
        # Ensure "nao identificado" subfolder exists for unidentified files
        self.nao_identificado_path = self.processado_folder_path / "nao identificado"
        self.nao_identificado_path.mkdir(parents=True, exist_ok=True)

        # Find all PNG files in rotated folder
        png_files = sorted(self.rotated_folder_path.glob("*.png"))
        if not png_files:
            logger.warning("No PNG files found at %s", self.rotated_folder_path)
            if saga:
                self._update_saga_with_event(saga, context, success=True, files_count=0)
            return []

        # Process each PNG file
        processed_files = self._process_images(png_files)

        logger.info(
            "PdfOcrNfExtractorOperator processed %d file(s) from %d input file(s).",
            len(processed_files),
            len(png_files),
        )

        if saga:
            self._update_saga_with_event(
                saga, context, success=True, files_count=len(processed_files)
            )

        return processed_files

    def _process_images(self, files: List[Path]) -> List[str]:
        """Process PNG images: extract NF-e and copy to processado folder.
        
        Files with identified NF-e are saved as {nf_e}.png in processado folder.
        Files without identified NF-e are moved to processado/nao identificado/ folder.
        """
        if not files:
            return []

        processed_files: List[str] = []

        for image_path in files:
            image_path = Path(image_path)
            try:
                # Extract NF-e number
                nf_e = extract_nf_e_from_image(image_path)
                
                if not nf_e:
                    # Move to "nao identificado" folder instead of skipping
                    output_path = self.nao_identificado_path / image_path.name
                    
                    # Check if file already exists
                    if output_path.exists() and not self.overwrite:
                        logger.warning(
                            "Output file %s already exists in nao identificado folder, skipping %s",
                            output_path.name,
                            image_path.name,
                        )
                        continue
                    
                    shutil.copy2(image_path, output_path)
                    logger.info(
                        "Could not extract NF-e from %s, moved to nao identificado folder: %s",
                        image_path.name,
                        output_path,
                    )
                    processed_files.append(str(output_path))
                    continue

                # Create output filename: {nf_e}.png
                output_filename = f"{nf_e}.png"
                output_path = self.processado_folder_path / output_filename

                # Check if file already exists
                if output_path.exists() and not self.overwrite:
                    logger.warning(
                        "Output file %s already exists and overwrite=False, skipping %s",
                        output_filename,
                        image_path.name,
                    )
                    continue

                # Copy file to processado folder with new name
                shutil.copy2(image_path, output_path)

                logger.info(
                    "Copied %s -> %s (NF-e: %s)",
                    image_path.name,
                    output_filename,
                    nf_e,
                )

                processed_files.append(str(output_path))

            except Exception as e:
                logger.error("Failed to process PNG %s: %s", image_path.name, e)
                # Move failed files to nao identificado folder
                try:
                    output_path = self.nao_identificado_path / image_path.name
                    shutil.copy2(image_path, output_path)
                    logger.info("Moved failed file %s to nao identificado folder", image_path.name)
                    processed_files.append(str(output_path))
                except Exception as move_error:
                    logger.error("Failed to move file %s to nao identificado folder: %s", 
                               image_path.name, move_error)
                continue

        return processed_files

    def _update_saga_with_event(
        self,
        saga: dict,
        context: Context,
        success: bool,
        files_count: int,
    ) -> None:
        """Update SAGA with NF-e extraction event and push to XCom."""
        if not saga or not saga.get("saga_id"):
            return

        if "events" not in saga:
            saga["events"] = []

        event = build_saga_event(
            event_type="TaskCompleted" if success else "TaskFailed",
            event_data={
                "step": "pdf_ocr_nf_extract",
                "status": "SUCCESS" if success else "FAILED",
                "files_processed": files_count,
                "rotated_folder": str(self.rotated_folder_path),
                "processado_folder": str(self.processado_folder_path),
            },
            context=context,
            task_id=self.task_id,
        )
        saga["events"].append(event)

        send_saga_event_to_api(saga, event, rpa_api_conn_id="rpa_api")

        saga["events_count"] = len(saga["events"])

        if success:
            saga["current_state"] = "RUNNING"

        task_instance = context.get("task_instance")
        if task_instance:
            task_instance.xcom_push(key="saga", value=saga)
            task_instance.xcom_push(key="rpa_payload", value=saga)

        log_saga(saga, task_id=self.task_id)
