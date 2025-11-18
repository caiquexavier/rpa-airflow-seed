"""GPT PDF Extractor operator - Processes PDF files using unified GPT service for rotation and extraction."""
import json
import logging
import shutil
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


class GptPdfExtractorOperator(BaseOperator):
    """
    Operator for processing PDF files using unified GPT service.
    
    This operator:
    1. Calls unified GPT service endpoint `/rpa/pdf/rotate-and-extract` to rotate PDF and extract all data in one operation
    2. Saves the rotated PDF files to output directory
    3. Logs extracted data to Airflow logs
    
    The operator sends requests matching GptPdfRotateExtractInput DTO:
    - file_path: Absolute path to PDF file
    - output_path: Path where rotated PDF should be saved
    - fields: Optional list of field names to extract (None = extract all identifiable fields)
    
    Expected response (GptPdfRotateExtractOutput):
    - status: "SUCCESS" or "FAIL"
    - rotated_file_path: Path to the rotated PDF file
    - extracted_data: Dictionary with extracted field values
    
    Args:
        folder_path: Path to directory containing PDF files to process
        output_dir: Path to directory where rotated PDFs will be saved
        fields: Optional list of field names to extract. If None, extracts all identifiable fields
        rpa_api_conn_id: Connection ID for RPA API (default: "rpa_api")
        endpoint: API endpoint for unified rotate-and-extract service (default: "/rpa/pdf/rotate-and-extract")
        timeout: Request timeout in seconds (default: 300)
    """

    def __init__(
        self,
        folder_path: str,
        output_dir: str,
        fields: Optional[List[str]] = None,
        rpa_api_conn_id: str = "rpa_api",
        endpoint: str = "/rpa/pdf/rotate-and-extract",
        timeout: int = 300,
        task_id: Optional[str] = None,
        **kwargs
    ):
        super().__init__(task_id=task_id, **kwargs)
        self.folder_path = Path(folder_path).resolve()
        self.output_dir = Path(output_dir).resolve()
        self.fields = fields
        self.rpa_api_conn_id = rpa_api_conn_id
        self.endpoint = endpoint
        self.timeout = timeout

    def execute(self, context: Context) -> Dict[str, Any]:
        """Process PDF files using unified GPT service for rotation and extraction."""
        logger.info("Starting GptPdfExtractorOperator for folder: %s", self.folder_path)
        
        # Get SAGA from context
        saga = get_saga_from_context(context)
        
        if not self.folder_path.exists() or not self.folder_path.is_dir():
            raise AirflowException(f"Folder path {self.folder_path} does not exist or is not a directory.")
        
        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Find all PDF files
        pdf_files = sorted(self.folder_path.glob("*.pdf"))
        if not pdf_files:
            logger.warning("No PDF files found at %s", self.folder_path)
            if saga:
                self._update_saga_with_event(saga, context, success=True, files_processed=0)
            return {"files_processed": 0, "results": []}
        
        # Build API URL
        conn = BaseHook.get_connection(self.rpa_api_conn_id)
        api_url = build_api_url(conn.schema, conn.host, conn.port, self.endpoint)
        
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
        
        logger.info("GptPdfExtractorOperator processed %d files successfully, %d failed", processed_count, failed_count)
        
        # Update SAGA with PDF extraction operation event
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
        Process a single PDF file using unified GPT service.
        
        Args:
            pdf_file: Path to PDF file
            api_url: Full API URL for rotate-and-extract endpoint
            
        Returns:
            Dictionary with extraction results
        """
        file_path = str(pdf_file.absolute())
        output_file_path = str(self.output_dir / pdf_file.name)
        
        logger.info("Processing PDF %s with unified GPT service (endpoint: %s)", pdf_file.name, api_url)
        
        try:
            # Build payload matching GptPdfRotateExtractInput DTO
            payload = {
                "file_path": file_path,
                "output_path": output_file_path,
                "fields": self.fields if self.fields else None
            }
            
            logger.debug("Request payload: file_path=%s, output_path=%s, fields=%s", 
                        file_path, output_file_path, self.fields)
            
            response = requests.post(
                api_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=self.timeout
            )
            response.raise_for_status()
            result = response.json()
            
            # Validate response structure (GptPdfRotateExtractOutput)
            status = result.get("status", "FAIL")
            rotated_file_path = result.get("rotated_file_path")
            extracted_data = result.get("extracted_data", {})
            
            if not rotated_file_path:
                logger.warning("Service did not return rotated_file_path, using expected output path")
                rotated_file_path = output_file_path
            
            # Normalize paths for comparison
            rotated_path = Path(rotated_file_path).resolve()
            expected_path = Path(output_file_path).resolve()
            
            # Verify rotated file exists at the returned path
            if not rotated_path.exists():
                logger.warning("Rotated file not found at returned path: %s, checking expected path: %s", 
                             rotated_file_path, output_file_path)
                if expected_path.exists():
                    rotated_file_path = str(expected_path)
                    rotated_path = expected_path
                else:
                    raise AirflowException(
                        f"Rotated PDF not found at returned path {rotated_file_path} or expected path {output_file_path}"
                    )
            
            # Move file if service saved it to a different location (defensive)
            if rotated_path != expected_path:
                logger.info("Moving rotated PDF from %s to %s", rotated_file_path, output_file_path)
                shutil.move(str(rotated_path), output_file_path)
                rotated_file_path = output_file_path
            
            # Verify final file exists
            if not Path(output_file_path).exists():
                raise AirflowException(f"Rotated PDF not found at final output path: {output_file_path}")
            
            # ENFORCE LOG: Log extracted data to Airflow logs
            extracted_json = json.dumps(extracted_data, indent=2, ensure_ascii=False)
            logger.info("=" * 80)
            logger.info("EXTRACTED DATA FOR %s:", pdf_file.name)
            logger.info("=" * 80)
            logger.info("\n%s", extracted_json)
            logger.info("=" * 80)
            
            success = status == "SUCCESS"
            if not success:
                logger.warning("Service returned status: %s (expected SUCCESS)", status)
            
            return {
                "file_path": file_path,
                "rotated_file_path": output_file_path,
                "success": success,
                "status": status,
                "extracted_data": extracted_data
            }
            
        except requests.exceptions.HTTPError as e:
            error_msg = f"HTTP error processing PDF {pdf_file.name}"
            if hasattr(e.response, 'text'):
                error_msg += f": {e.response.text}"
            logger.error("%s: %s", error_msg, e)
            raise AirflowException(f"{error_msg}: {e}") from e
        except requests.exceptions.RequestException as e:
            logger.error("Request error processing PDF %s: %s", pdf_file.name, e)
            raise AirflowException(f"Failed to process PDF {pdf_file.name}: {e}") from e
        except KeyError as e:
            logger.error("Missing expected field in response for PDF %s: %s", pdf_file.name, e)
            raise AirflowException(f"Invalid response structure for PDF {pdf_file.name}: missing {e}") from e
    
    def _update_saga_with_event(
        self, 
        saga: dict, 
        context: Context, 
        success: bool, 
        files_processed: int,
        files_failed: int = 0
    ) -> None:
        """Update SAGA with GPT PDF extraction operation event and push to XCom."""
        if not saga or not saga.get("saga_id"):
            logger.warning("SAGA missing saga_id, skipping event update")
            return
        
        # Ensure events list exists
        if "events" not in saga:
            saga["events"] = []
        
        # Build event for GPT PDF extraction operation
        event = build_saga_event(
            event_type="TaskCompleted" if success else "TaskFailed",
            event_data={
                "step": "gpt_pdf_extract",
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

