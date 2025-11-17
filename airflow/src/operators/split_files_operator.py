"""Split PDF files operator."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Sequence

from airflow.exceptions import AirflowException
from airflow.models import BaseOperator
from airflow.utils.context import Context
from pypdf import PdfReader, PdfWriter

from services.saga import get_saga_from_context, build_saga_event, send_saga_event_to_api, log_saga

logger = logging.getLogger(__name__)


class SplitFilesOperator(BaseOperator):
    """
    Custom Airflow operator that splits multi-page PDF files into single-page PDFs.

    Args:
        folder_path: Path to the directory containing PDF files to split.
        output_dir: Optional directory where the split files will be stored.
            Defaults to the input `folder_path`.
        overwrite: Whether to overwrite existing files when splitting (default: True).
        include_single_page: Whether to copy PDFs that already have a single page
            to the output directory (default: False).
        task_id: Airflow task id (required by BaseOperator but exposed for completeness).
    """

    def __init__(
        self,
        folder_path: str,
        output_dir: str | None = None,
        overwrite: bool = True,
        include_single_page: bool = False,
        task_id: str | None = None,
        **kwargs,
    ) -> None:
        super().__init__(task_id=task_id, **kwargs)
        self.folder_path = Path(folder_path)
        self.output_dir = Path(output_dir) if output_dir else self.folder_path
        self.overwrite = overwrite
        self.include_single_page = include_single_page

    def execute(self, context: Context) -> List[str]:
        """
        Execute the operator logic.

        Returns:
            List of file paths for the generated PDF files.
        """
        logger.info("Starting SplitFilesOperator for folder: %s", self.folder_path)
        
        # Get SAGA from context
        saga = get_saga_from_context(context)
        
        if not self.folder_path.exists() or not self.folder_path.is_dir():
            raise AirflowException(f"Folder path {self.folder_path} does not exist or is not a directory.")

        pdf_files = sorted(self.folder_path.glob("*.pdf"))
        if not pdf_files:
            logger.warning("No PDF files found at %s", self.folder_path)
            # Still update SAGA even if no files found
            if saga:
                self._update_saga_with_event(saga, context, success=True, files_count=0)
            return []

        generated_files: List[str] = []
        self.output_dir.mkdir(parents=True, exist_ok=True)

        for pdf_file in pdf_files:
            generated_files.extend(self._split_pdf(pdf_file))

        logger.info("SplitFilesOperator generated %d files.", len(generated_files))
        
        # Update SAGA with split operation event
        if saga:
            self._update_saga_with_event(saga, context, success=True, files_count=len(generated_files))
        
        return generated_files
    
    def _update_saga_with_event(
        self, 
        saga: dict, 
        context: Context, 
        success: bool, 
        files_count: int
    ) -> None:
        """Update SAGA with split operation event and push to XCom."""
        if not saga or not saga.get("saga_id"):
            logger.warning("SAGA missing saga_id, skipping event update")
            return
        
        # Ensure events list exists
        if "events" not in saga:
            saga["events"] = []
        
        # Build event for split operation
        event = build_saga_event(
            event_type="TaskCompleted" if success else "TaskFailed",
            event_data={
                "step": "split_pdf_files",
                "status": "SUCCESS" if success else "FAILED",
                "files_generated": files_count,
                "input_folder": str(self.folder_path),
                "output_folder": str(self.output_dir)
            },
            context=context,
            task_id=self.task_id
        )
        saga["events"].append(event)
        
        # Send event to rpa-api for persistence
        send_saga_event_to_api(saga, event, rpa_api_conn_id="rpa_api")
        
        # Update events_count
        saga["events_count"] = len(saga["events"])
        
        # Update current_state
        if success:
            saga["current_state"] = "RUNNING"  # Still in progress, not completed yet
        
        # Push updated SAGA back to XCom
        task_instance = context.get('task_instance')
        if task_instance:
            task_instance.xcom_push(key="saga", value=saga)
            task_instance.xcom_push(key="rpa_payload", value=saga)  # Backward compatibility
        
        # Log SAGA
        log_saga(saga, task_id=self.task_id)

    def _split_pdf(self, pdf_path: Path) -> Sequence[str]:
        """Split a single PDF file into multiple single-page PDFs."""
        logger.debug("Processing PDF file: %s", pdf_path)
        reader = PdfReader(str(pdf_path))
        num_pages = len(reader.pages)

        if num_pages <= 1:
            if self.include_single_page:
                target_path = self.output_dir / pdf_path.name
                logger.debug("Copying single-page PDF to %s", target_path)
                self._write_pdf(reader.pages[0:1], target_path)
                return [str(target_path)]
            logger.debug("Skipping single-page PDF: %s", pdf_path)
            return []

        output_paths = []
        for index, page in enumerate(reader.pages, start=1):
            target_path = self.output_dir / f"{pdf_path.stem}_page_{index}.pdf"
            if target_path.exists() and not self.overwrite:
                raise AirflowException(f"Target file {target_path} exists. Set overwrite=True to replace.")
            self._write_pdf([page], target_path)
            output_paths.append(str(target_path))

        logger.info(
            "Split %s into %d files stored in %s", pdf_path.name, len(output_paths), self.output_dir
        )
        return output_paths

    def _write_pdf(self, pages: Sequence, target_path: Path) -> None:
        """Write given pages to the target PDF path."""
        writer = PdfWriter()
        for page in pages:
            writer.add_page(page)

        with target_path.open("wb") as target_file:
            writer.write(target_file)


