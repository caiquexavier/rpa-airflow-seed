"""PDF Split Operator - Splits multi-page PDF files into single-page PNG images."""

from __future__ import annotations

import gc
import logging
from pathlib import Path
from typing import List, Optional, Sequence

try:
    import fitz
    FITZ_AVAILABLE = True
except ImportError:
    FITZ_AVAILABLE = False

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

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

# High DPI for full quality images
FULL_DPI = 300


class PdfSplitOperator(BaseOperator):
    """Operator that splits multi-page PDF files into single-page PNG images."""

    def __init__(
        self,
        folder_path: str,
        output_dir: Optional[str] = None,
        overwrite: bool = True,
        include_single_page: bool = False,
        subdirectory: str = "split",
        dpi: int = FULL_DPI,
        task_id: Optional[str] = None,
        **kwargs,
    ) -> None:
        super().__init__(task_id=task_id, **kwargs)
        self.folder_path = Path(folder_path)
        base_output_dir = Path(output_dir) if output_dir else self.folder_path
        # Create subdirectory for split image files
        self.output_dir = base_output_dir / subdirectory
        self.overwrite = overwrite
        self.include_single_page = include_single_page
        self.dpi = dpi

    def execute(self, context: Context) -> List[str]:
        """Execute PDF splitting to PNG images."""
        logger.info("Starting PdfSplitOperator for folder: %s", self.folder_path)

        saga = get_saga_from_context(context)

        if not FITZ_AVAILABLE:
            raise RuntimeError("PyMuPDF (fitz) not available. Install pymupdf to split PDF files.")
        
        if not PIL_AVAILABLE:
            raise RuntimeError("PIL/Pillow not available. Install Pillow to save PNG images.")

        if not self.folder_path.exists() or not self.folder_path.is_dir():
            raise AirflowException(
                f"Folder path {self.folder_path} does not exist or is not a directory."
            )

        pdf_files = sorted(self.folder_path.glob("*.pdf"))
        if not pdf_files:
            logger.warning("No PDF files found at %s", self.folder_path)
            if saga:
                self._update_saga_with_event(saga, context, success=True, files_count=0)
            return []

        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Clean up any existing PDF files in output folder (should only contain PNG files)
        self._clean_pdf_files_from_output()
        
        output_paths = self._split_pdfs_to_images(list(map(Path, pdf_files)))
        generated_files = [str(path) for path in output_paths]

        logger.info(
            "PdfSplitOperator produced %d PNG image(s) from %d input PDF file(s) at %d DPI.",
            len(generated_files),
            len(pdf_files),
            self.dpi,
        )

        if saga:
            self._update_saga_with_event(
                saga, context, success=True, files_count=len(generated_files)
            )

        return generated_files

    def _split_pdfs_to_images(self, files: Sequence[Path]) -> List[Path]:
        """Split PDFs into single-page PNG images."""
        if not files:
            return []

        output_paths: List[Path] = []
        for pdf_path in files:
            logger.debug("Splitting PDF file to images: %s", pdf_path)
            doc = fitz.open(str(pdf_path))
            try:
                num_pages = len(doc)

                if num_pages <= 1:
                    if self.include_single_page:
                        target_path = self.output_dir / f"split_{pdf_path.stem}.png"
                        self._convert_page_to_image(doc[0], target_path)
                        output_paths.append(target_path)
                        logger.info("Single-page PDF %s saved to %s", pdf_path.name, target_path)
                    continue

                for index, page in enumerate(doc, start=1):
                    target_path = self.output_dir / f"split_{pdf_path.stem}_{index}.png"
                    self._convert_page_to_image(page, target_path)
                    output_paths.append(target_path)

                logger.info(
                    "Split %s into %d PNG image(s) stored in %s",
                    pdf_path.name,
                    num_pages,
                    self.output_dir,
                )
            finally:
                doc.close()

        return output_paths

    def _clean_pdf_files_from_output(self) -> None:
        """Remove any PDF files from output folder (should only contain PNG files)."""
        if not self.output_dir.exists():
            return
        
        pdf_files = list(self.output_dir.glob("*.pdf"))
        if pdf_files:
            logger.info("Cleaning output folder: removing %d PDF file(s) (only PNG files should be present)", len(pdf_files))
            for pdf_file in pdf_files:
                try:
                    pdf_file.unlink()
                    logger.debug("Removed PDF file: %s", pdf_file.name)
                except Exception as e:
                    logger.warning("Failed to remove PDF file %s: %s", pdf_file.name, e)

    def _convert_page_to_image(self, page, target_path: Path) -> None:
        """Convert a PDF page to PNG image at full DPI."""
        if target_path.exists() and not self.overwrite:
            raise AirflowException(
                f"Target file {target_path} exists. Set overwrite=True to replace."
            )

        try:
            # Calculate zoom based on DPI (72 is default PDF DPI)
            zoom = self.dpi / 72.0
            mat = fitz.Matrix(zoom, zoom)
            
            # Render page to pixmap at full DPI
            pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB, alpha=False, annots=False)
            img_data = pix.tobytes("png")
            width, height = pix.width, pix.height
            
            # Save PNG image
            with target_path.open("wb") as target_file:
                target_file.write(img_data)
            
            # Clean up memory
            pix = None
            gc.collect()
            
            logger.debug(
                "Converted page to PNG: %s (%dx%d pixels at %d DPI)",
                target_path.name,
                width,
                height,
                self.dpi
            )
        except Exception as e:
            logger.error("Failed to convert page to PNG image: %s", e)
            raise RuntimeError(f"Failed to convert page to PNG: {e}") from e

    def _update_saga_with_event(
        self,
        saga: dict,
        context: Context,
        success: bool,
        files_count: int,
    ) -> None:
        """Update SAGA with PDF split event and push to XCom."""
        if not saga or not saga.get("saga_id"):
            return
        
        if "events" not in saga:
            saga["events"] = []
        
        event = build_saga_event(
            event_type="TaskCompleted" if success else "TaskFailed",
            event_data={
                "step": "pdf_split",
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

