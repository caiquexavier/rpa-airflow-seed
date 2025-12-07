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
    Operator for processing PDF files using unified GPT service with integrated rotation detection.
    
    This operator:
    1. Converts PDF pages to PNG images
    2. Detects and rotates PDFs to best readable position using GPT Vision
    3. Extracts data from rotated images using GPT Vision
    4. Saves renamed files with doc_transporte_nf_e.pdf naming convention
    
    Args:
        folder_path: Path to directory containing PDF files to process
        output_dir: Path to directory where processed PDFs will be saved
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
        """Process PDF files using unified GPT service with integrated rotation detection and extraction."""
        logger.info("Starting GptPdfExtractorOperator for folder: %s", self.folder_path)
        
        # Get SAGA from context
        saga = get_saga_from_context(context)
        
        if not self.folder_path.exists() or not self.folder_path.is_dir():
            raise AirflowException(f"Folder path {self.folder_path} does not exist or is not a directory.")
        
        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Read saga data and create folders for each doc_transportes
        doc_transportes_map = self._setup_output_folders(saga)
        
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
                result = self._process_pdf(pdf_file, api_url, doc_transportes_map)
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
    
    def _setup_output_folders(self, saga: Optional[Dict[str, Any]]) -> Dict[str, str]:
        """
        Read saga data and create folders for each doc_transportes.
        Also creates "Nao processados" folder for unprocessed files.
        
        Args:
            saga: Saga dictionary with data.doc_transportes_list
            
        Returns:
            Dictionary mapping nf_e values to doc_transportes values
        """
        nf_to_doc_map: Dict[str, str] = {}
        
        # Create "Nao processados" folder
        nao_processados_dir = self.output_dir / "Nao processados"
        nao_processados_dir.mkdir(parents=True, exist_ok=True)
        logger.info("Created 'Nao processados' folder: %s", nao_processados_dir)
        
        if not saga or not saga.get("data"):
            logger.warning("Saga data not available, will save all files to 'Nao processados'")
            return nf_to_doc_map
        
        doc_transportes_list = saga["data"].get("doc_transportes_list", [])
        if not doc_transportes_list:
            logger.warning("doc_transportes_list not found in saga data")
            return nf_to_doc_map
        
        logger.info("Setting up output folders for %d doc_transportes entries", len(doc_transportes_list))
        
        for doc_entry in doc_transportes_list:
            doc_transportes = doc_entry.get("doc_transportes")
            nf_e_list = doc_entry.get("nf_e", [])
            
            if not doc_transportes:
                logger.warning("Found doc_transportes entry without doc_transportes value, skipping")
                continue
            
            # Create folder for this doc_transportes
            doc_folder = self.output_dir / str(doc_transportes)
            doc_folder.mkdir(parents=True, exist_ok=True)
            logger.info("Created folder for doc_transportes %s: %s", doc_transportes, doc_folder)
            
            # Map each nf_e to its doc_transportes
            # CRITICAL: Clean nf_e values to match extraction cleaning logic
            for nf_e in nf_e_list:
                if nf_e:
                    nf_key = self._clean_nf_e_value(nf_e)
                    if nf_key:
                        nf_to_doc_map[nf_key] = str(doc_transportes)
                        logger.debug("Mapped nf_e %s to doc_transportes %s", nf_key, doc_transportes)
        
        logger.info("Created %d folder mappings (nf_e -> doc_transportes)", len(nf_to_doc_map))
        return nf_to_doc_map
    
    def _process_pdf(self, pdf_file: Path, api_url: str, doc_transportes_map: Dict[str, str]) -> Dict[str, Any]:
        """
        Process a single PDF file using GPT extraction service.

        Args:
            pdf_file: Path to PDF file
            api_url: Full API URL for extraction endpoint
            doc_transportes_map: Dictionary mapping nf_e values to doc_transportes values

        Returns:
            Dictionary with extraction results
        """
        file_path = str(pdf_file.absolute())
        # Temporary output path (will be renamed after extraction)
        temp_output_file_path = str(self.output_dir / pdf_file.name)
        
        logger.info("Processing PDF %s with GPT extraction service (endpoint: %s)", pdf_file.name, api_url)
        
        try:
            payload = {
                "file_path": file_path,
                "output_path": temp_output_file_path,
                "field_map": self.field_map if self.field_map else None
            }
            
            logger.debug("Request payload: file_path=%s, output_path=%s, field_map_size=%s", 
                        file_path, temp_output_file_path, len(self.field_map) if self.field_map else 0)
            
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
            service_output_path = result.get("organized_file_path") or result.get("rotated_file_path") or temp_output_file_path
            
            # Verify rotated file exists
            rotated_path_obj = Path(service_output_path)
            if not rotated_path_obj.exists():
                logger.warning(
                    "Rotated file does not exist at %s, using temp path %s",
                    service_output_path,
                    temp_output_file_path
                )
                service_output_path = temp_output_file_path
            else:
                logger.info("Rotated PDF file confirmed at: %s", service_output_path)
            
            # Clean nf_e value: remove all non-numeric characters
            if "nf_e" in extracted_data and extracted_data["nf_e"]:
                original_nf_e = extracted_data["nf_e"]
                cleaned_nf_e = self._clean_nf_e_value(original_nf_e)
                if cleaned_nf_e != original_nf_e:
                    logger.info(
                        "Cleaned nf_e value: '%s' -> '%s'",
                        original_nf_e,
                        cleaned_nf_e
                    )
                extracted_data["nf_e"] = cleaned_nf_e
            
            # Also try to extract doc_transportes from extracted_data if available
            # This helps with file organization even if not in saga mapping
            doc_transportes_from_data = (
                extracted_data.get("doc_transportes") or 
                extracted_data.get("doc_transporte") or 
                extracted_data.get("dt") or
                extracted_data.get("documento_transportes") or
                extracted_data.get("doc_transportes_numero")
            )
            if doc_transportes_from_data:
                doc_transportes_cleaned = str(doc_transportes_from_data).strip()
                # Clean to keep only digits/alphanumeric
                doc_transportes_cleaned = "".join(c for c in doc_transportes_cleaned if c.isalnum())
                if doc_transportes_cleaned:
                    extracted_data["doc_transportes"] = doc_transportes_cleaned
                    logger.info("Extracted doc_transportes from data: %s", doc_transportes_cleaned)
            
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
            
            # Determine final output path based on extracted nf_e
            final_output_path = self._determine_output_path(
                extracted_data, 
                doc_transportes_map, 
                Path(service_output_path)
            )
            
            return {
                "file_path": file_path,
                "output_file_path": str(final_output_path),
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

    def _clean_extracted_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Remove null and empty values from extracted data dictionary.
        Recursively cleans nested dictionaries.
        
        Args:
            data: Dictionary with extracted data (may contain null/empty values)
            
        Returns:
            Cleaned dictionary with only meaningful values
        """
        if not isinstance(data, dict):
            return data
        
        cleaned = {}
        for key, value in data.items():
            # Skip None values
            if value is None:
                continue
            
            # Skip empty strings
            if isinstance(value, str) and not value.strip():
                continue
            
            # Skip empty lists
            if isinstance(value, list) and len(value) == 0:
                continue
            
            # Skip empty dictionaries
            if isinstance(value, dict) and len(value) == 0:
                continue
            
            # Recursively clean nested dictionaries
            if isinstance(value, dict):
                cleaned_nested = self._clean_extracted_data(value)
                # Only add if cleaned nested dict is not empty
                if cleaned_nested:
                    cleaned[key] = cleaned_nested
            else:
                cleaned[key] = value
        
        return cleaned

    def _store_extracted_data_in_saga(self, saga: Dict[str, Any], extracted_data: Dict[str, Any]) -> None:
        """
        Persist extracted data payloads inside saga.data.extracted_data keyed by nf_e.
        Avoids duplicates by skipping inserts when the nf_e key already exists.
        Removes null and empty values before storing.
        """
        if not saga or not extracted_data:
            return

        # Clean extracted data: remove null and empty values
        cleaned_data = self._clean_extracted_data(extracted_data)
        
        if not cleaned_data:
            logger.warning("Extracted data is empty after cleaning; skipping saga persistence")
            return

        nf_value = cleaned_data.get("nf_e")
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

        extracted_bucket[nf_key] = cleaned_data
        logger.info("Stored cleaned extracted data for NF-e %s into saga.data.extracted_data", nf_key)

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
        
        # Clean extracted data: remove null and empty values
        cleaned_data = self._clean_extracted_data(extracted_data)
        
        if not cleaned_data:
            logger.warning("Extracted data is empty after cleaning; skipping API persistence")
            return
        
        # Apply same duplicate-removal logic as _store_extracted_data_in_saga
        nf_value = cleaned_data.get("nf_e")
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
                "metadata": cleaned_data
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
    
    def _clean_nf_e_value(self, nf_e_value: Any) -> str:
        """
        Clean nf_e value by removing all non-numeric characters.
        
        Args:
            nf_e_value: Original nf_e value (can be string, number, etc.)
            
        Returns:
            String containing only numeric characters, or empty string if no digits found
        """
        if nf_e_value is None:
            return ""
        
        # Convert to string and extract only digits
        nf_e_str = str(nf_e_value)
        cleaned = "".join(c for c in nf_e_str if c.isdigit())
        
        return cleaned
    
    def _determine_output_path(
        self, 
        extracted_data: Dict[str, Any], 
        doc_transportes_map: Dict[str, str],
        service_output_path: Path
    ) -> Path:
        """
        Determine final output path based on extracted nf_e and saga data.
        Files are saved rotated and renamed to doc_transportes_nf_e.pdf format.
        
        Args:
            extracted_data: Extracted data dictionary (should contain nf_e)
            doc_transportes_map: Dictionary mapping nf_e values to doc_transportes values
            service_output_path: Path where GPT service saved the rotated file
            
        Returns:
            Final Path where file should be saved (with proper name and folder)
        """
        import shutil
        
        # Clean and extract nf_e value
        nf_e_value = extracted_data.get("nf_e")
        if nf_e_value:
            nf_e_value = self._clean_nf_e_value(nf_e_value)
        
        # CRITICAL: Never use extracted doc_transportes values to create folders.
        # Only use doc_transportes_list values from saga data (via doc_transportes_map).
        
        if not nf_e_value:
            # NF-e not identified - try to extract from filename or use fallback
            # Check if filename contains a number that might be nf_e
            filename_stem = service_output_path.stem
            logger.warning(
                "NF-e not identified in extracted data for %s. "
                "Available fields: %s. Checking filename for fallback.",
                service_output_path.name,
                list(extracted_data.keys())
            )
            
            # Try to find nf_e in filename (common patterns: _123456.pdf, 123456.pdf, etc.)
            import re
            numbers_in_filename = re.findall(r'\d+', filename_stem)
            if numbers_in_filename:
                # Use the longest number found as potential nf_e
                potential_nf_e = max(numbers_in_filename, key=len)
                if len(potential_nf_e) >= 5:  # NF-e numbers are typically 5+ digits
                    logger.info(
                        "Using potential nf_e from filename: %s (from %s)",
                        potential_nf_e,
                        filename_stem
                    )
                    nf_e_value = potential_nf_e
        
        if not nf_e_value:
            # Still no nf_e found, save to "Nao processados" folder
            nao_processados_dir = self.output_dir / "Nao processados"
            nao_processados_dir.mkdir(parents=True, exist_ok=True)
            final_path = nao_processados_dir / service_output_path.name
            logger.warning(
                "NF-e not identified for %s, saving to 'Nao processados': %s",
                service_output_path.name,
                final_path
            )
        else:
            nf_key = str(nf_e_value).strip()
            # CRITICAL: Only use doc_transportes from saga mapping (doc_transportes_list).
            # Never create folders from extracted values or filenames.
            doc_transportes = doc_transportes_map.get(nf_key)
            
            # If exact match not found, try partial matching (handle cases where extracted nf_e 
            # might be a substring of saga nf_e or vice versa, e.g., "491183" vs "4921183")
            if not doc_transportes and nf_key and len(nf_key) >= 5:
                logger.info(
                    "Exact match not found for nf_e '%s'. Available saga nf_e values: %s. Trying partial matching...",
                    nf_key,
                    list(doc_transportes_map.keys())[:10]  # Show first 10 for logging
                )
                best_match = None
                best_match_length = 0
                for saga_nf_e, saga_doc_transportes in doc_transportes_map.items():
                    # Check if nf_key is contained in saga_nf_e or saga_nf_e is contained in nf_key
                    if nf_key in saga_nf_e or saga_nf_e in nf_key:
                        # Use the longer matching substring for better accuracy
                        match_length = min(len(nf_key), len(saga_nf_e))
                        if match_length >= 5 and match_length > best_match_length:  # At least 5 digits
                            best_match = saga_doc_transportes
                            best_match_length = match_length
                            logger.info(
                                "Found partial match candidate: extracted nf_e '%s' matches saga nf_e '%s' (match length: %d) -> doc_transportes '%s'",
                                nf_key, saga_nf_e, match_length, saga_doc_transportes
                            )
                if best_match:
                    doc_transportes = best_match
                    logger.info("Using best partial match: doc_transportes '%s'", doc_transportes)
            
            # If still no doc_transportes from mapping, try using extracted doc_transportes from PDF
            if not doc_transportes:
                doc_transportes_from_extracted = extracted_data.get("doc_transportes")
                if doc_transportes_from_extracted:
                    doc_transportes_cleaned = str(doc_transportes_from_extracted).strip()
                    doc_transportes_cleaned = "".join(c for c in doc_transportes_cleaned if c.isalnum())
                    if doc_transportes_cleaned:
                        # Check if this doc_transportes folder exists (from saga data)
                        potential_folder = self.output_dir / doc_transportes_cleaned
                        if potential_folder.exists():
                            doc_transportes = doc_transportes_cleaned
                            logger.info(
                                "Using doc_transportes '%s' extracted from PDF (folder exists from saga data)",
                                doc_transportes
                            )
                        else:
                            logger.warning(
                                "Extracted doc_transportes '%s' from PDF, but folder does not exist in saga data. "
                                "Will save to 'Nao processados'.",
                                doc_transportes_cleaned
                            )
            
            if not doc_transportes:
                # Still no doc_transportes found - save to "Nao processados" but keep nf_e in name
                nao_processados_dir = self.output_dir / "Nao processados"
                nao_processados_dir.mkdir(parents=True, exist_ok=True)
                final_filename = f"nf_e_{nf_key}.pdf"
                final_path = nao_processados_dir / final_filename
                logger.warning(
                    "NF-e %s found but not found in saga doc_transportes_list mapping. "
                    "Saving to 'Nao processados' as: %s",
                    nf_key,
                    final_path
                )
            else:
                # Found doc_transportes from saga mapping, save to proper folder
                # CRITICAL: doc_folder must already exist from _setup_output_folders (saga doc_transportes_list)
                doc_folder = self.output_dir / str(doc_transportes)
                if not doc_folder.exists():
                    logger.error(
                        "CRITICAL: Folder %s does not exist in saga doc_transportes_list. "
                        "This should not happen - folder should be created from saga data only.",
                        doc_folder
                    )
                    # Fallback: save to "Nao processados" instead of creating wrong folder
                    nao_processados_dir = self.output_dir / "Nao processados"
                    nao_processados_dir.mkdir(parents=True, exist_ok=True)
                    final_filename = f"nf_e_{nf_key}.pdf"
                    final_path = nao_processados_dir / final_filename
                    logger.warning(
                        "NF-e %s mapped to doc_transportes %s, but folder not in saga list. "
                        "Saving to 'Nao processados' as: %s",
                        nf_key,
                        doc_transportes,
                        final_path
                    )
                else:
                    final_filename = f"{doc_transportes}_{nf_key}.pdf"
                    final_path = doc_folder / final_filename
                    logger.info(
                        "NF-e %s mapped to doc_transportes %s (from saga), saving as: %s",
                        nf_key,
                        doc_transportes,
                        final_path
                    )
        
        # Move/rename rotated file to final location
        # CRITICAL: Always use the rotated file from service (it's already rotated)
        if service_output_path.exists() and service_output_path != final_path:
            final_path.parent.mkdir(parents=True, exist_ok=True)
            if final_path.exists():
                logger.warning("Target file already exists, overwriting: %s", final_path)
                final_path.unlink()
            # Move the rotated PDF file to final location
            shutil.move(str(service_output_path), str(final_path))
            logger.info("Moved rotated PDF file from %s to %s", service_output_path, final_path)
            
            # Verify the rotated file exists at final location
            if not final_path.exists():
                raise RuntimeError(f"Failed to move rotated file to {final_path}")
            if final_path.stat().st_size == 0:
                raise RuntimeError(f"Rotated file is empty at {final_path}")
            logger.info("Rotated PDF file verified at final location: %s (%d bytes)", final_path, final_path.stat().st_size)
        elif service_output_path == final_path:
            logger.info("Rotated file already at final location: %s", final_path)
        else:
            logger.error("Service output file does not exist: %s", service_output_path)
            raise RuntimeError(f"Rotated PDF file not found at {service_output_path}. Rotation may have failed.")
        
        return final_path

