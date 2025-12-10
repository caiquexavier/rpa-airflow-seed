"""Protocolo PDF Generator operator - Generates protocolo de devolução PDFs from SAGA data."""
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from airflow.exceptions import AirflowException
from airflow.models import BaseOperator
from airflow.models import Variable
from airflow.utils.context import Context

try:
    import fitz  # PyMuPDF
    FITZ_AVAILABLE = True
except ImportError:
    FITZ_AVAILABLE = False

from services.saga import get_saga_from_context, build_saga_event, send_saga_event_to_api, log_saga
from services.pdf_generator import create_protocolo_de_devolucao_pdf

logger = logging.getLogger(__name__)

# Default fallback saga data when saga is not available
# Structured as complete saga data object with doc_transportes_list
DEFAULT_SAGA_DATA = {
    "doc_transportes_list": [
        {
            "doc_transportes": "96722724",
            "nf_e": [
                "4921184",
                "4921183",
                "4921190",
                "4921192",
                "4920188",
                "4941272",
                "4941187",
                "4941186",
                "4941177"
            ]
        },
        {
            "doc_transportes": "96802793",
            "nf_e": [
                "1301229",
                "1301232",
                "1301236",
                "1303468",
                "1301233",
                "1301231",
                "1301230",
                "1301234",
                "1301235",
                "1301228"
            ]
        },
        {
            "doc_transportes": "97542262",
            "nf_e": [
                "1319786",
                "1320038",
                "1329928",
                "1328276",
                "1328274",
                "1328260"
            ]
        }
    ],
    "extracted_data": {},
    "saga_id": None
}


class ProtocoloPdfGeneratorOperator(BaseOperator):
    """
    Operator for generating protocolo de devolução PDFs from SAGA data.
    
    This operator:
    1. Reads doc_transportes_list from saga.data (or uses default fallback)
    2. Generates one PDF per doc_transportes with format: {doc_transportes}_POD.pdf
    3. Saves PDFs to processado/{doc_transportes}/ folder
    4. Concatenates protocolo PDF with all associated PDFs ({doc_transportes}_*.pdf) into final PDF
    5. Updates SAGA with generation event
    
    The operator can run with or without saga data. If saga is not available, it uses a default
    fallback doc_transportes_list for PDF generation.
    
    Args:
        processado_dir: Path to processado directory where doc_transportes folders are located
                       (default: "/opt/airflow/data/processado")
        rpa_api_conn_id: Connection ID for RPA API (default: "rpa_api")
    """

    def __init__(
        self,
        processado_dir: Optional[str] = None,
        rpa_api_conn_id: str = "rpa_api",
        task_id: Optional[str] = None,
        **kwargs
    ):
        super().__init__(task_id=task_id, **kwargs)
        # Use processado_dir parameter or default
        if processado_dir:
            self.processado_dir = Path(processado_dir).resolve()
        else:
            self.processado_dir = Path("/opt/airflow/data/processado").resolve()
        self.rpa_api_conn_id = rpa_api_conn_id
        
        if not FITZ_AVAILABLE:
            logger.warning("PyMuPDF (fitz) not available. PDF concatenation will fail.")

    def execute(self, context: Context) -> Dict[str, Any]:
        """Generate protocolo de devolução PDFs from SAGA data and concatenate with associated PDFs."""
        logger.info("Starting ProtocoloPdfGeneratorOperator for processado directory: %s", self.processado_dir)
        
        if not FITZ_AVAILABLE:
            raise AirflowException("PyMuPDF (fitz) is required for PDF concatenation. Please install PyMuPDF.")
        
        # Get SAGA from context
        saga = get_saga_from_context(context)
        
        # Ensure processado directory exists
        self.processado_dir.mkdir(parents=True, exist_ok=True)
        
        # Get saga data for PDF generation (from saga or use default fallback)
        saga_data = self._get_saga_data(saga)
        
        doc_transportes_list = saga_data.get("doc_transportes_list", [])
        if not doc_transportes_list:
            logger.warning("No doc_transportes_list found, cannot generate PDFs")
            if saga:
                self._update_saga_with_event(saga, context, success=False, files_generated=0)
            return {
                "status": "success",
                "files_generated": 0,
                "output_paths": [],
                "saga_id": saga.get("saga_id") if saga else None
            }
        
        # Generate one PDF for each doc_transportes
        generated_files = []
        failed_count = 0
        
        for doc_entry in doc_transportes_list:
            doc_transportes = doc_entry.get("doc_transportes")
            if not doc_transportes:
                logger.warning("Found doc_transportes entry without value, skipping")
                continue
            
            doc_transportes_str = str(doc_transportes).strip()
            if not doc_transportes_str:
                continue
            
            # Create doc_transportes folder in processado directory
            doc_folder = self.processado_dir / doc_transportes_str
            doc_folder.mkdir(parents=True, exist_ok=True)
            
            # Generate protocolo PDF filename: doc_transportes_protocolo_temp.pdf (intermediate file)
            protocolo_filename = f"{doc_transportes_str}_protocolo_temp.pdf"
            protocolo_path = doc_folder / protocolo_filename
            
            logger.info("Generating protocolo PDF for doc_transportes=%s, output: %s", doc_transportes_str, protocolo_path)
            
            try:
                # Generate protocolo PDF
                create_protocolo_de_devolucao_pdf(
                    output_path=str(protocolo_path),
                    saga_data=saga_data,
                    doc_transportes=doc_transportes_str
                )
                logger.info("Successfully generated protocolo PDF at: %s", protocolo_path)
                
                # Verify protocolo PDF was created
                if not protocolo_path.exists():
                    raise AirflowException(f"Protocolo PDF was not created at {protocolo_path}")
                if protocolo_path.stat().st_size == 0:
                    raise AirflowException(f"Protocolo PDF is empty at {protocolo_path}")
                
                # Find all associated PDFs for this doc_transportes
                associated_pdfs = self._find_associated_pdfs(doc_folder, doc_transportes_str)
                logger.info("Found %d associated PDF(s) for doc_transportes %s", len(associated_pdfs), doc_transportes_str)
                
                # Generate final concatenated PDF filename: doc_transportes_POD.pdf
                final_filename = f"{doc_transportes_str}_POD.pdf"
                final_path = doc_folder / final_filename
                
                # If there are associated PDFs, concatenate them with protocolo PDF
                # Otherwise, just rename protocolo PDF to final name
                if associated_pdfs:
                    # Concatenate protocolo PDF with all associated PDFs into final PDF
                    self._concatenate_pdfs([protocolo_path] + associated_pdfs, final_path)
                    logger.info("Successfully created final concatenated PDF at: %s", final_path)
                    
                    # Remove intermediate protocolo PDF (keep only the final concatenated one)
                    if protocolo_path.exists():
                        protocolo_path.unlink()
                        logger.debug("Removed intermediate protocolo PDF: %s", protocolo_path)
                else:
                    # No associated PDFs - just rename protocolo PDF to final name
                    import shutil
                    shutil.move(str(protocolo_path), str(final_path))
                    logger.info("No associated PDFs found, renamed protocolo PDF to: %s", final_path)
                
                # Verify final PDF exists
                if not final_path.exists():
                    raise AirflowException(f"Final PDF was not created at {final_path}")
                if final_path.stat().st_size == 0:
                    raise AirflowException(f"Final PDF is empty at {final_path}")
                
                logger.info("Final PDF verified: %s (%d bytes)", final_path, final_path.stat().st_size)
                generated_files.append(str(final_path))
            except Exception as e:
                failed_count += 1
                logger.error("Failed to generate PDF for doc_transportes %s: %s", doc_transportes_str, e, exc_info=True)
                # Continue with other files even if one fails
                continue
        
        if not generated_files and failed_count > 0:
            logger.error("No PDFs were generated successfully, %d failed", failed_count)
            if saga:
                self._update_saga_with_event(saga, context, success=False, files_generated=0, files_failed=failed_count)
            raise AirflowException(f"PDF generation failed: no files were generated, {failed_count} failed")
        
        logger.info("ProtocoloPdfGeneratorOperator generated %d PDFs successfully, %d failed", len(generated_files), failed_count)
        
        # Update SAGA with PDF generation event
        if saga:
            self._update_saga_with_event(
                saga, 
                context, 
                success=(failed_count == 0), 
                files_generated=len(generated_files),
                files_failed=failed_count,
                output_paths=generated_files
            )
        
        return {
            "status": "success",
            "files_generated": len(generated_files),
            "files_failed": failed_count,
            "output_paths": generated_files,
            "saga_id": saga.get("saga_id") if saga else None
        }
    
    def _get_saga_data(self, saga: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Get saga data for PDF generation from saga or use default fallback.
        
        Returns complete saga data structure with doc_transportes_list, extracted_data, and saga_id.
        
        Args:
            saga: Saga dictionary with data.doc_transportes_list (optional)
            
        Returns:
            Dictionary with saga data structure:
            {
                "doc_transportes_list": [...],
                "extracted_data": {...},
                "saga_id": ... or None
            }
        """
        # If saga is available, extract data from it
        if saga and saga.get("data"):
            saga_data = {
                "doc_transportes_list": saga["data"].get("doc_transportes_list", []),
                "extracted_data": saga["data"].get("extracted_data", {}),
                "saga_id": saga.get("saga_id"),
            }
            
            # If doc_transportes_list is empty, use default fallback
            if not saga_data["doc_transportes_list"]:
                logger.info("doc_transportes_list not found in saga data, using default fallback")
                saga_data = DEFAULT_SAGA_DATA.copy()
                # Preserve saga_id from actual saga if available
                saga_data["saga_id"] = saga.get("saga_id")
            else:
                logger.info("Using doc_transportes_list from saga data")
        else:
            logger.info("Saga data not available, using default fallback saga data")
            saga_data = DEFAULT_SAGA_DATA.copy()
        
        logger.info(
            "Using saga data with %d doc_transportes entries and %d extracted_data entries",
            len(saga_data.get("doc_transportes_list", [])),
            len(saga_data.get("extracted_data", {}))
        )
        return saga_data
    
    def _update_saga_with_event(
        self, 
        saga: dict, 
        context: Context, 
        success: bool, 
        files_generated: int,
        files_failed: int = 0,
        output_paths: Optional[list] = None
    ) -> None:
        """Update SAGA with protocolo PDF generation event and push to XCom."""
        if not saga or not saga.get("saga_id"):
            logger.warning("SAGA missing saga_id, skipping event update")
            return
        
        # Ensure events list exists
        if "events" not in saga:
            saga["events"] = []
        
        # Build event for protocolo PDF generation operation
        event = build_saga_event(
            event_type="TaskCompleted" if success else "TaskFailed",
            event_data={
                "step": "generate_protocolo_pdf",
                "status": "SUCCESS" if success else "FAILED",
                "files_generated": files_generated,
                "files_failed": files_failed,
                "processado_dir": str(self.processado_dir),
                "output_paths": output_paths or []
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
    
    def _find_associated_pdfs(self, doc_folder: Path, doc_transportes: str) -> list[Path]:
        """
        Find all PDF files associated with a doc_transportes.
        
        Looks for files matching pattern: {doc_transportes}_*.pdf
        Excludes the protocolo PDF itself.
        
        Args:
            doc_folder: Folder containing the PDFs
            doc_transportes: Documento de Transporte value
            
        Returns:
            List of Path objects for associated PDFs, sorted by filename
        """
        associated_pdfs = []
        pattern = f"{doc_transportes}_*.pdf"
        
        for pdf_file in sorted(doc_folder.glob(pattern)):
            # Exclude protocolo PDF (both temp and final), and final concatenated PDF
            if "_POD" not in pdf_file.name and "_protocolo_temp" not in pdf_file.name:
                associated_pdfs.append(pdf_file)
                logger.debug("Found associated PDF: %s", pdf_file.name)
        
        return associated_pdfs
    
    def _concatenate_pdfs(self, pdf_paths: list[Path], output_path: Path) -> None:
        """
        Concatenate multiple PDF files into a single PDF.
        
        - First PDF (protocolo) is added as-is
        - Subsequent PDFs have protocolo pages removed and are resized to fit A4 landscape
        
        Args:
            pdf_paths: List of Path objects for PDF files to concatenate (first should be protocolo PDF)
            output_path: Path where the concatenated PDF will be saved
            
        Raises:
            AirflowException: If concatenation fails
        """
        if not pdf_paths:
            raise AirflowException("No PDF files provided for concatenation")
        
        logger.info("Concatenating %d PDF file(s) into: %s", len(pdf_paths), output_path)
        
        try:
            # Create a new PDF document with A4 landscape format
            merged_pdf = fitz.open()
            # Set to A4 landscape (297mm x 210mm)
            a4_landscape_rect = fitz.Rect(0, 0, 842, 595)  # A4 landscape in points (297mm x 210mm)
            
            protocolo_added = False
            
            for idx, pdf_path in enumerate(pdf_paths):
                if not pdf_path.exists():
                    logger.warning("PDF file does not exist, skipping: %s", pdf_path)
                    continue
                
                logger.debug("Processing PDF: %s", pdf_path.name)
                source_pdf = None
                try:
                    # Open the PDF
                    source_pdf = fitz.open(str(pdf_path))
                    
                    if idx == 0:
                        # First PDF is the protocolo - add all pages as-is
                        merged_pdf.insert_pdf(source_pdf)
                        protocolo_added = True
                        logger.debug("Added protocolo PDF with %d page(s)", len(source_pdf))
                    else:
                        # For associated PDFs, filter out protocolo pages and resize
                        pages_added = 0
                        pages_to_add = []
                        
                        # First pass: identify which pages to add (skip protocolo pages)
                        for page_num in range(len(source_pdf)):
                            page = source_pdf[page_num]
                            
                            # Check if page contains protocolo text (case-insensitive, handle variations)
                            text = page.get_text().upper()
                            # Check for protocolo de devolução (with or without accents)
                            is_protocolo_page = (
                                "PROTOCOLO DE DEVOLUÇÃO" in text or 
                                "PROTOCOLO DE DEVOLUCAO" in text or
                                ("PROTOCOLO" in text and "DEVOLU" in text)
                            )
                            
                            if is_protocolo_page:
                                logger.debug("Skipping protocolo page %d from %s (already included)", page_num + 1, pdf_path.name)
                                continue
                            
                            pages_to_add.append(page_num)
                        
                        # Second pass: add pages with proper sizing
                        for page_num in pages_to_add:
                            page = source_pdf[page_num]
                            
                            # Get the source page's mediabox (actual page size)
                            source_rect = page.rect
                            
                            # Target size: A4 landscape (842 x 595 points = 297mm x 210mm)
                            target_width = 842
                            target_height = 595
                            
                            # Calculate scaling to fit the page while maintaining aspect ratio
                            scale_x = target_width / source_rect.width
                            scale_y = target_height / source_rect.height
                            scale = min(scale_x, scale_y)  # Use smaller scale to fit within bounds
                            
                            # Calculate centered position
                            scaled_width = source_rect.width * scale
                            scaled_height = source_rect.height * scale
                            x_offset = (target_width - scaled_width) / 2
                            y_offset = (target_height - scaled_height) / 2
                            
                            # Create a new page in merged PDF with A4 landscape size
                            new_page = merged_pdf.new_page(width=target_width, height=target_height)
                            
                            # Calculate the target rectangle for the scaled page (centered)
                            target_rect = fitz.Rect(
                                x_offset,
                                y_offset,
                                x_offset + scaled_width,
                                y_offset + scaled_height
                            )
                            
                            # Insert the page content into the new page with scaling and centering
                            # Use show_pdf_page with the scaled rect - it will fit the source page to the rect
                            new_page.show_pdf_page(
                                target_rect,  # Target rect (scaled and centered)
                                source_pdf,  # Source document
                                page_num,  # Page number
                                keep_proportion=True  # Maintain aspect ratio
                            )
                            
                            pages_added += 1
                        
                        logger.debug("Added %d page(s) from %s (protocolo pages filtered, resized to A4 landscape)", pages_added, pdf_path.name)
                    
                except Exception as e:
                    logger.error("Failed to process PDF %s: %s", pdf_path, e)
                    raise AirflowException(f"Failed to process PDF {pdf_path}: {e}") from e
                finally:
                    # Close source PDF
                    if source_pdf:
                        source_pdf.close()
            
            total_pages = len(merged_pdf)
            if total_pages == 0:
                merged_pdf.close()
                raise AirflowException("No pages were added to the merged PDF")
            
            if not protocolo_added:
                merged_pdf.close()
                raise AirflowException("Protocolo PDF was not added to merged PDF")
            
            # Save the merged PDF
            merged_pdf.save(str(output_path))
            merged_pdf.close()
            
            logger.info(
                "Successfully concatenated %d PDF file(s) into %s (%d total pages)",
                len(pdf_paths),
                output_path.name,
                total_pages
            )
        except Exception as e:
            logger.error("Failed to concatenate PDFs: %s", e, exc_info=True)
            raise AirflowException(f"PDF concatenation failed: {e}") from e

