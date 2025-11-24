"""GPT PDF Extractor operator - Processes PDF files using GPT extraction API."""
import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

import requests
from airflow.exceptions import AirflowException
from airflow.hooks.base import BaseHook
from airflow.models import BaseOperator
from airflow.utils.context import Context

from services.saga import get_saga_from_context, build_saga_event, send_saga_event_to_api, log_saga
from libs.rpa_robot_executor import build_api_url
from libs.pdf_field_map import get_pdf_field_map

logger = logging.getLogger(__name__)


class GptPdfExtractorOperator(BaseOperator):
    """
    Operator for processing PDF files using unified GPT service.
    
    This operator:
    1. Calls the GPT extraction endpoint `/rpa/pdf/extract-gpt`
    2. Uploads extracted data / logs result for each PDF
    3. Assumes rotation has already been handled upstream (e.g., PdfFunctionsOperator)
    
    Args:
        folder_path: Path to directory containing PDF files to process
        output_dir: Path to directory where rotated PDFs will be saved
        field_map: Optional dictionary mapping field names to descriptions/instructions.
                  If None, uses the default PDF field map. If empty dict, GPT will identify all fields.
        rpa_api_conn_id: Connection ID for RPA API (default: "rpa_api")
        endpoint: API endpoint for GPT extraction service (default: "/rpa/pdf/extract-gpt")
        timeout: Request timeout in seconds (default: 300)
        save_extracted_data: If True, saves extracted JSON to rpa_extracted_data table via rpa-api (default: False)
    """

    def __init__(
        self,
        folder_path: str,
        output_dir: str,
        field_map: Optional[Dict[str, str]] = None,
        rpa_api_conn_id: str = "rpa_api",
        endpoint: str = "/rpa/pdf/extract-gpt",
        timeout: int = 300,
        save_extracted_data: bool = False,
        task_id: Optional[str] = None,
        **kwargs
    ):
        super().__init__(task_id=task_id, **kwargs)
        self.folder_path = Path(folder_path).resolve()
        self.output_dir = Path(output_dir).resolve()
        # Use provided field_map or default PDF field map
        self.field_map = field_map if field_map is not None else get_pdf_field_map()
        self.rpa_api_conn_id = rpa_api_conn_id
        self.endpoint = endpoint
        self.timeout = timeout
        self.save_extracted_data = save_extracted_data

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
                if saga and result.get("success") and result.get("extracted_data"):
                    self._store_extracted_data_in_saga(saga, result["extracted_data"])
                    # Save to rpa_extracted_data table if enabled
                    if self.save_extracted_data:
                        self._save_extracted_data_to_api(saga, result["extracted_data"])
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
        Process a single PDF file using GPT extraction service.

        Args:
            pdf_file: Path to PDF file
            api_url: Full API URL for extraction endpoint

        Returns:
            Dictionary with extraction results
        """
        file_path = str(pdf_file.absolute())
        output_file_path = str(self.output_dir / pdf_file.name)
        
        logger.info("Processing PDF %s with GPT extraction service (endpoint: %s)", pdf_file.name, api_url)
        
        try:
            payload = {
                "file_path": file_path,
                "output_path": output_file_path,
                "field_map": self.field_map if self.field_map else None
            }
            
            logger.debug("Request payload: file_path=%s, output_path=%s, field_map_size=%s", 
                        file_path, output_file_path, len(self.field_map) if self.field_map else 0)
            
            response = requests.post(
                api_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=self.timeout
            )
            response.raise_for_status()
            result = response.json()
            
            status = result.get("status", "FAIL")
            extracted_data = result.get("extracted") or result.get("extracted_data", {})
            organized_file_path = result.get("organized_file_path") or output_file_path
            
            # Log extracted data to Airflow logs for observability
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
                "output_file_path": organized_file_path,
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
                "field_map_size": len(self.field_map) if self.field_map else 0
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

    def _store_extracted_data_in_saga(self, saga: Dict[str, Any], extracted_data: Dict[str, Any]) -> None:
        """
        Persist extracted data payloads inside saga.data.extracted_data keyed by nf_e.
        Avoids duplicates by skipping inserts when the nf_e key already exists.
        """
        if not saga or not extracted_data:
            return

        nf_value = extracted_data.get("nf_e")
        if nf_value is None:
            logger.warning("Extracted data missing nf_e field; skipping saga persistence")
            return

        nf_key = str(nf_value).strip()
        if not nf_key:
            logger.warning("Extracted data contains empty nf_e value; skipping saga persistence")
            return

        saga.setdefault("data", {})
        extracted_bucket = saga["data"].setdefault("extracted_data", {})

        if not isinstance(extracted_bucket, dict):
            logger.warning(
                "Unexpected saga.data.extracted_data type %s; resetting to dict for keyed storage",
                type(extracted_bucket).__name__,
            )
            extracted_bucket = {}
            saga["data"]["extracted_data"] = extracted_bucket

        if nf_key in extracted_bucket:
            logger.info("Saga already has extracted data for NF-e %s; skipping duplicate insert", nf_key)
            return

        extracted_bucket[nf_key] = extracted_data
        logger.info("Stored extracted data for NF-e %s into saga.data.extracted_data", nf_key)

    def _save_extracted_data_to_api(self, saga: Dict[str, Any], extracted_data: Dict[str, Any]) -> None:
        """
        Save extracted data to rpa_extracted_data table via rpa-api.
        
        Only saves if save_extracted_data=True and saga has valid saga_id.
        Preserves existing duplicate-removal logic by checking nf_e before saving.
        """
        if not self.save_extracted_data:
            return
        
        saga_id = saga.get("saga_id")
        if not saga_id:
            logger.warning("Cannot save extracted data: saga missing saga_id")
            return
        
        if not extracted_data:
            logger.warning("Cannot save extracted data: extracted_data is empty")
            return
        
        # Apply same duplicate-removal logic as _store_extracted_data_in_saga
        nf_value = extracted_data.get("nf_e")
        if nf_value is None:
            logger.warning("Extracted data missing nf_e field; skipping API persistence")
            return
        
        nf_key = str(nf_value).strip()
        if not nf_key:
            logger.warning("Extracted data contains empty nf_e value; skipping API persistence")
            return
        
        # Check if already saved (via saga.data.extracted_data)
        saga.setdefault("data", {})
        extracted_bucket = saga["data"].get("extracted_data", {})
        if isinstance(extracted_bucket, dict) and nf_key in extracted_bucket:
            logger.info("Extracted data for NF-e %s already exists in saga; skipping API save", nf_key)
            return
        
        try:
            conn = BaseHook.get_connection(self.rpa_api_conn_id)
            api_url = build_api_url(conn.schema, conn.host, conn.port, "/api/v1/extracted-data/")
            
            payload = {
                "saga_id": saga_id,
                "metadata": extracted_data
            }
            
            response = requests.post(
                api_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=self.timeout
            )
            response.raise_for_status()
            
            result = response.json()
            record_id = result.get("id")
            logger.info("Successfully saved extracted data for NF-e %s to rpa_extracted_data (id=%s)", nf_key, record_id)
        except requests.exceptions.HTTPError as e:
            error_msg = f"HTTP error saving extracted data for NF-e {nf_key}"
            if hasattr(e.response, 'text'):
                error_msg += f": {e.response.text}"
            logger.error("%s: %s", error_msg, e)
            # Don't raise - allow operator to continue even if API save fails
        except requests.exceptions.RequestException as e:
            logger.error("Request error saving extracted data for NF-e %s: %s", nf_key, e)
            # Don't raise - allow operator to continue even if API save fails
        except Exception as e:
            logger.error("Unexpected error saving extracted data for NF-e %s: %s", nf_key, e)
            # Don't raise - allow operator to continue even if API save fails

