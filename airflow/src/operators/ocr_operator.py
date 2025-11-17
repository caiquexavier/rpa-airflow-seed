"""OCR PDF operator - Processes PDF files using OCR service."""
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from airflow.exceptions import AirflowException
from airflow.hooks.base import BaseHook
from airflow.models import BaseOperator
from airflow.utils.context import Context

from services.saga import get_saga_from_context, build_saga_event, send_saga_event_to_api, log_saga
from libs.rpa_robot_executor import build_api_url

logger = logging.getLogger(__name__)


class OcrOperator(BaseOperator):
    """
    Operator for processing PDF files using OCR service.
    
    Args:
        folder_path: Path to directory containing PDF files to process
        fields: List of field names to extract from PDFs
        rpa_api_conn_id: Connection ID for RPA API (default: "rpa_api")
        api_endpoint: API endpoint for OCR service (default: "/ocr/pdf/read")
        timeout: Request timeout in seconds (default: 300)
    """

    def __init__(
        self,
        folder_path: str,
        fields: Optional[List[str]] = None,
        rpa_api_conn_id: str = "rpa_api",
        api_endpoint: str = "/ocr/pdf/read",
        timeout: int = 300,
        task_id: Optional[str] = None,
        **kwargs
    ):
        super().__init__(task_id=task_id, **kwargs)
        self.folder_path = Path(folder_path).resolve()
        self.fields = fields
        self.rpa_api_conn_id = rpa_api_conn_id
        self.api_endpoint = api_endpoint
        self.timeout = timeout

    def execute(self, context: Context) -> Dict[str, Any]:
        """Process PDF files in folder using OCR service."""
        logger.info("Starting OcrOperator for folder: %s", self.folder_path)
        
        # Get SAGA from context
        saga = get_saga_from_context(context)
        
        if not self.folder_path.exists() or not self.folder_path.is_dir():
            raise AirflowException(f"Folder path {self.folder_path} does not exist or is not a directory.")
        
        # Find all PDF files
        pdf_files = sorted(self.folder_path.glob("*.pdf"))
        if not pdf_files:
            logger.warning("No PDF files found at %s", self.folder_path)
            if saga:
                self._update_saga_with_event(saga, context, success=True, files_processed=0)
            return {"files_processed": 0, "results": []}
        
        # Build API URL
        conn = BaseHook.get_connection(self.rpa_api_conn_id)
        api_url = build_api_url(conn.schema, conn.host, conn.port, self.api_endpoint)
        
        # Process each PDF file
        results = []
        processed_count = 0
        failed_count = 0
        
        for pdf_file in pdf_files:
            try:
                result = self._process_pdf(pdf_file, api_url)
                results.append(result)
                processed_count += 1
                logger.info("Successfully processed PDF: %s", pdf_file.name)
            except Exception as e:
                failed_count += 1
                logger.error("Failed to process PDF %s: %s", pdf_file.name, e)
                results.append({
                    "file_path": str(pdf_file),
                    "error": str(e),
                    "success": False
                })
        
        logger.info("OcrOperator processed %d files successfully, %d failed", processed_count, failed_count)
        
        # Update SAGA with OCR operation event
        if saga:
            self._update_saga_with_event(
                saga, 
                context, 
                success=(failed_count == 0), 
                files_processed=processed_count,
                files_failed=failed_count
            )
        
        return {
            "files_processed": processed_count,
            "files_failed": failed_count,
            "results": results
        }
    
    def _process_pdf(self, pdf_file: Path, api_url: str) -> Dict[str, Any]:
        """
        Process a single PDF file using OCR service - pure function.
        
        Args:
            pdf_file: Path to PDF file
            api_url: Full API URL for OCR endpoint
            
        Returns:
            Dictionary with OCR results
        """
        # Build request payload
        payload = {
            "file_path": str(pdf_file.absolute()),
            "fields": self.fields
        }
        
        # Make API request
        try:
            response = requests.post(
                api_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=self.timeout
            )
            response.raise_for_status()
            
            result = response.json()
            result["success"] = True
            return result
        except requests.exceptions.RequestException as e:
            logger.error("API request failed for %s: %s", pdf_file.name, e)
            raise AirflowException(f"Failed to process PDF {pdf_file.name}: {e}") from e
    
    def _update_saga_with_event(
        self, 
        saga: dict, 
        context: Context, 
        success: bool, 
        files_processed: int,
        files_failed: int = 0
    ) -> None:
        """Update SAGA with OCR operation event and push to XCom."""
        if not saga or not saga.get("saga_id"):
            logger.warning("SAGA missing saga_id, skipping event update")
            return
        
        # Ensure events list exists
        if "events" not in saga:
            saga["events"] = []
        
        # Build event for OCR operation
        event = build_saga_event(
            event_type="TaskCompleted" if success else "TaskFailed",
            event_data={
                "step": "ocr_pdf",
                "status": "SUCCESS" if success else "FAILED",
                "files_processed": files_processed,
                "files_failed": files_failed,
                "folder_path": str(self.folder_path),
                "fields": self.fields
            },
            context=context,
            task_id=self.task_id
        )
        saga["events"].append(event)
        
        # Send event to rpa-api for persistence
        send_saga_event_to_api(saga, event, rpa_api_conn_id=self.rpa_api_conn_id)
        
        # Update events_count
        saga["events_count"] = len(saga["events"])
        
        # Update current_state
        if success:
            saga["current_state"] = "RUNNING"
        
        # Push updated SAGA back to XCom
        task_instance = context.get('task_instance')
        if task_instance:
            task_instance.xcom_push(key="saga", value=saga)
            task_instance.xcom_push(key="rpa_payload", value=saga)  # Backward compatibility
        
        # Log SAGA
        log_saga(saga, task_id=self.task_id)

