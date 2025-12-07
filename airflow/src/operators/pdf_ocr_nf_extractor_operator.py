"""PDF OCR NF-E Extractor Operator - Extracts NF-E numbers from rotated PNG images using OCR."""

from __future__ import annotations

import logging
import re
import shutil
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


def extract_nf_e_from_text(text: str) -> Optional[str]:
    """Extract NF-e number from OCR text using multiple patterns.
    
    Args:
        text: OCR text from image
        
    Returns:
        NF-e number as string, or None if not found
    """
    if not text:
        return None
    
    # Normalize whitespace for simpler matching
    cleaned = " ".join(text.split())
    
    # Pattern 1: Look for NF-e labels followed by numbers
    # Patterns: NF-e, NFE, NF E, Nota Fiscal, etc.
    label_patterns = [
        r"NF[\s\-_]*E?[\s\-_]*:?\s*(\d{5,15})",  # NF-e: 4921183, NF E 4921183, etc.
        r"Nota[\s\-_]*Fiscal[\s\-_]*E?[\s\-_]*:?\s*(\d{5,15})",  # Nota Fiscal: 4921183
        r"N[º°]?[\s\-_]*NF[\s\-_]*E?[\s\-_]*:?\s*(\d{5,15})",  # Nº NF-e: 4921183
        r"Número[\s\-_]*NF[\s\-_]*E?[\s\-_]*:?\s*(\d{5,15})",  # Número NF-e: 4921183
    ]
    
    for pattern in label_patterns:
        matches = re.findall(pattern, cleaned, re.IGNORECASE)
        if matches:
            # Return the longest match (most likely to be complete NF-e)
            nf_e = max(matches, key=len)
            logger.debug("Found NF-e using label pattern: %s", nf_e)
            return nf_e
    
    # Pattern 2: Look for numbers in a box or prominent area
    # Often NF-e appears in a box or highlighted area
    # Look for sequences of 5-15 digits that might be NF-e
    # Prefer longer sequences (7-9 digits are common for NF-e)
    
    # Find all digit sequences of 5-15 characters
    digit_sequences = re.findall(r"\b(\d{5,15})\b", cleaned)
    
    if digit_sequences:
        # Filter and prioritize:
        # 1. Sequences of 7-9 digits (most common NF-e length)
        # 2. Longer sequences (10-15 digits)
        # 3. Shorter sequences (5-6 digits) as last resort
        
        # Sort by length, prioritizing 7-9 digit sequences
        def priority_key(seq: str) -> tuple:
            length = len(seq)
            if 7 <= length <= 9:
                return (0, length)  # Highest priority
            elif length >= 10:
                return (1, length)  # Medium priority
            else:
                return (2, length)  # Lower priority
        
        sorted_sequences = sorted(digit_sequences, key=priority_key)
        
        # Return the highest priority sequence
        nf_e = sorted_sequences[0]
        logger.debug("Found NF-e using digit sequence pattern: %s (from %d candidates)", nf_e, len(digit_sequences))
        return nf_e
    
    return None


def extract_nf_e_from_image(image_path: Path) -> Optional[str]:
    """Extract NF-e number from PNG image using OCR.
    
    Args:
        image_path: Path to PNG image
        
    Returns:
        NF-e number as string, or None if not found
    """
    if not PIL_AVAILABLE or not TESSERACT_AVAILABLE:
        logger.warning("PIL or Tesseract not available, cannot extract NF-e from %s", image_path.name)
        return None
    
    try:
        # Load image
        image = Image.open(str(image_path))
        
        try:
            # Run OCR with Portuguese + English
            # Use PSM 6 (assume uniform block of text) for better results
            try:
                text = pytesseract.image_to_string(
                    image, lang="por+eng", config="--oem 3 --psm 6"
                )
            except Exception:
                # Fallback to Portuguese only
                try:
                    text = pytesseract.image_to_string(
                        image, lang="por", config="--oem 3 --psm 6"
                    )
                except Exception:
                    # Fallback to English only
                    text = pytesseract.image_to_string(
                        image, lang="eng", config="--oem 3 --psm 6"
                    )
            
            logger.debug("OCR extracted %d characters from %s", len(text), image_path.name)
            
            # Extract NF-e from text
            nf_e = extract_nf_e_from_text(text)
            
            if nf_e:
                logger.info("Extracted NF-e %s from %s", nf_e, image_path.name)
            else:
                logger.warning("Could not extract NF-e from %s", image_path.name)
            
            return nf_e
            
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
        """Process PNG images: extract NF-e and copy to processado folder."""
        if not files:
            return []

        processed_files: List[str] = []

        for image_path in files:
            image_path = Path(image_path)
            try:
                # Extract NF-e number
                nf_e = extract_nf_e_from_image(image_path)
                
                if not nf_e:
                    logger.warning(
                        "Could not extract NF-e from %s, skipping file",
                        image_path.name,
                    )
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

