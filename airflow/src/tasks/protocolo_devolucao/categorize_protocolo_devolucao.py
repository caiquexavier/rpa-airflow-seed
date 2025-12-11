"""Categorize Protocolo Devolução results by validating POD files."""
import logging
import re
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

from airflow.exceptions import AirflowException
from services.saga import (
    get_saga_from_context,
    log_saga,
    build_saga_event,
    send_saga_event_to_api,
)

logger = logging.getLogger(__name__)


def count_pdf_pages(pdf_path: Path) -> int:
    """Count number of pages in a PDF file."""
    if pdfplumber is None:
        raise RuntimeError("pdfplumber is required. Install it with: pip install pdfplumber")
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            return len(pdf.pages)
    except Exception as e:
        logger.error(f"Error counting pages in {pdf_path}: {e}")
        raise


def extract_nota_fiscal_count_from_pod(pod_path: Path) -> int:
    """
    Extract the number of Nota Fiscal entries from POD PDF table.
    
    Looks for the PROTOCOLO DE DEVOLUÇÃO table and counts rows with Nota Fiscal numbers.
    The table structure is:
    - Header row: Quantidade | Documento de Transporte | Entrega | Nº Nota Fiscal | Regular / Irregular
    - Data rows: Each row contains one Nota Fiscal number
    """
    if pdfplumber is None:
        raise RuntimeError("pdfplumber is required. Install it with: pip install pdfplumber")
    
    try:
        with pdfplumber.open(pod_path) as pdf:
            # Extract text from all pages
            full_text = ""
            for page in pdf.pages:
                page_text = page.extract_text() or ""
                full_text += page_text + "\n"
            
            logger.debug(f"Extracted {len(full_text)} characters from POD PDF")
            
            nota_fiscal_numbers = set()
            
            # Strategy 1: Extract from tables (most reliable)
            for page_num, page in enumerate(pdf.pages, 1):
                tables = page.extract_tables()
                logger.debug(f"Page {page_num}: Found {len(tables)} table(s)")
                
                for table_idx, table in enumerate(tables):
                    if not table or len(table) < 2:  # Need at least header + 1 data row
                        continue
                    
                    # Check if this table contains PROTOCOLO DE DEVOLUÇÃO header
                    header_found = False
                    header_row_idx = None
                    nf_column_idx = None
                    
                    for row_idx, row in enumerate(table[:10]):  # Check first 10 rows for header
                        if not row:
                            continue
                        # Look for header row containing "PROTOCOLO" and "DEVOLU"
                        row_text = " ".join(str(cell or "").upper() for cell in row if cell)
                        if "PROTOCOLO" in row_text and "DEVOLU" in row_text:
                            header_found = True
                            header_row_idx = row_idx
                            logger.debug(f"Found header at row {row_idx}: {row_text[:100]}")
                            
                            # Find the "Nota Fiscal" column index - try multiple patterns
                            for col_idx, cell in enumerate(row):
                                if cell:
                                    cell_upper = str(cell).upper()
                                    if any(keyword in cell_upper for keyword in ["NOTA FISCAL", "Nº NOTA", "NF", "NF-E"]):
                                        nf_column_idx = col_idx
                                        logger.debug(f"Found Nota Fiscal column at index {col_idx}")
                                        break
                            
                            # If not found by keyword, assume it's the 4th column (0-indexed: 3)
                            if nf_column_idx is None and len(row) >= 4:
                                nf_column_idx = 3
                                logger.debug(f"Using default Nota Fiscal column index 3")
                            break
                    
                    if header_found and nf_column_idx is not None:
                        # Extract Nota Fiscal numbers from data rows (skip header row)
                        # ONLY from the identified "Nº Nota Fiscal" column
                        rows_extracted = 0
                        for row_idx in range(header_row_idx + 1, len(table)):
                            row = table[row_idx]
                            if not row:
                                continue
                            
                            # ONLY get NF from the identified column (Nº Nota Fiscal)
                            if len(row) > nf_column_idx:
                                nf_cell = row[nf_column_idx]
                                if nf_cell:
                                    nf_str = str(nf_cell).strip()
                                    # Extract numbers (5-15 digits) - this is the Nota Fiscal number
                                    matches = re.findall(r'\b\d{5,15}\b', nf_str)
                                    for match in matches:
                                        if len(match) >= 5:
                                            nota_fiscal_numbers.add(match)
                                            rows_extracted += 1
                        
                        logger.debug(f"Extracted {rows_extracted} NF numbers from table {table_idx} on page {page_num} (column {nf_column_idx})")
            
            # Strategy 2: Extract from text patterns if table extraction found nothing or found few
            # This is a fallback that tries to identify the NF column position from text
            if len(nota_fiscal_numbers) < 3:  # If we found less than 3, try text extraction
                logger.debug("Trying text-based extraction as fallback")
                lines = full_text.split('\n')
                in_table = False
                table_start_line = None
                nf_column_position = None
                
                for line_idx, line in enumerate(lines):
                    line_upper = line.upper()
                    # Detect table start and find NF column position
                    if "PROTOCOLO" in line_upper and "DEVOLU" in line_upper:
                        in_table = True
                        table_start_line = line_idx
                        logger.debug(f"Table starts at line {line_idx}")
                        
                        # Try to identify NF column position from header line
                        # Look for patterns like "Nº NOTA FISCAL" or "NOTA FISCAL"
                        header_parts = line.split()
                        for i, part in enumerate(header_parts):
                            if any(keyword in part.upper() for keyword in ["NOTA", "NF", "FISCAL"]):
                                nf_column_position = i
                                logger.debug(f"Identified NF column position: {nf_column_position} from header")
                                break
                        continue
                    
                    if in_table and nf_column_position is not None:
                        # Only extract from the identified column position
                        line_parts = line.split()
                        if len(line_parts) > nf_column_position:
                            nf_part = line_parts[nf_column_position]
                            # Extract numbers (5-15 digits) from this specific column
                            matches = re.findall(r'\b\d{5,15}\b', nf_part)
                            for match in matches:
                                if len(match) >= 5:
                                    # Additional validation: exclude dates and common patterns
                                    if '/' not in nf_part and '-' not in nf_part:
                                        if not any(x in nf_part.lower() for x in ['cnpj', 'cpf', 'cep']):
                                            nota_fiscal_numbers.add(match)
                        
                        # Stop after reasonable number of lines (table shouldn't be too long)
                        if line_idx - table_start_line > 50:
                            break
            
            # Strategy 3: Look for patterns like "4921184", "4921183" in the entire text
            # These are typically 7-digit numbers that appear multiple times
            if len(nota_fiscal_numbers) == 0:
                logger.debug("Trying pattern-based extraction from full text")
                # Look for sequences of 7-8 digit numbers that appear multiple times
                all_numbers = re.findall(r'\b\d{7,8}\b', full_text)
                number_counts = Counter(all_numbers)
                # Get numbers that appear at least twice (likely NF numbers)
                for num, count in number_counts.most_common(20):
                    if count >= 2 and len(num) >= 7:
                        # Additional validation: should not be a date component
                        if not re.search(rf'\b{num}\b.*[/-]', full_text):
                            nota_fiscal_numbers.add(num)
            
            count = len(nota_fiscal_numbers)
            if count > 0:
                logger.info(f"Found {count} unique Nota Fiscal numbers in POD: {sorted(nota_fiscal_numbers)}")
            else:
                logger.warning(f"No Nota Fiscal numbers found in POD: {pod_path}")
                logger.debug(f"First 500 chars of extracted text: {full_text[:500]}")
            return count
            
    except Exception as e:
        logger.error(f"Error extracting Nota Fiscal count from {pod_path}: {e}")
        raise


def count_nf_pdf_files(folder_path: Path) -> int:
    """Count PDF files in folder excluding POD files."""
    pdf_files = [f for f in folder_path.glob("*.pdf") 
                 if f.is_file() and "POD" not in f.name.upper()]
    return len(pdf_files)


def validate_pod_folder(folder_path: Path) -> Tuple[bool, Dict[str, any]]:
    """
    Validate POD folder structure and content.
    
    Returns:
        Tuple of (is_valid, validation_details)
    """
    pod_file = folder_path / f"{folder_path.name}_POD.pdf"
    
    if not pod_file.exists():
        return False, {
            "error": f"POD file not found: {pod_file.name}",
            "pod_file": str(pod_file),
            "folder": str(folder_path)
        }
    
    try:
        # Count Nota Fiscal entries in POD
        nota_fiscal_count = extract_nota_fiscal_count_from_pod(pod_file)
        
        # Count PDF pages in POD
        pod_pages = count_pdf_pages(pod_file)
        
        # Count NF PDF files (excluding POD)
        nf_pdf_count = count_nf_pdf_files(folder_path)
        
        # Validation rules:
        # 1. POD should have X + 1 pages (X = number of Nota Fiscal entries)
        # 2. Number of NF PDF files should match X
        expected_pages = nota_fiscal_count + 1
        is_valid = (
            pod_pages == expected_pages and
            nf_pdf_count == nota_fiscal_count
        )
        
        validation_details = {
            "is_valid": is_valid,
            "nota_fiscal_count": nota_fiscal_count,
            "pod_pages": pod_pages,
            "expected_pod_pages": expected_pages,
            "nf_pdf_count": nf_pdf_count,
            "pod_file": str(pod_file),
            "folder": str(folder_path),
            "errors": []
        }
        
        if pod_pages != expected_pages:
            validation_details["errors"].append(
                f"POD has {pod_pages} pages, expected {expected_pages} (Nota Fiscal count + 1)"
            )
        
        if nf_pdf_count != nota_fiscal_count:
            validation_details["errors"].append(
                f"Found {nf_pdf_count} NF PDF files, expected {nota_fiscal_count} (matching Nota Fiscal count)"
            )
        
        return is_valid, validation_details
        
    except Exception as e:
        logger.error(f"Error validating folder {folder_path}: {e}")
        return False, {
            "error": str(e),
            "pod_file": str(pod_file),
            "folder": str(folder_path)
        }


def move_folder(source: Path, destination: Path) -> None:
    """Move folder from source to destination."""
    if destination.exists():
        logger.warning(f"Destination already exists: {destination}, removing it first")
        import shutil
        shutil.rmtree(destination)
    
    import shutil
    shutil.move(str(source), str(destination))
    logger.info(f"Moved folder from {source} to {destination}")


def categorize_protocolo_devolucao_task(**context) -> Dict[str, any]:
    """
    Categorize Protocolo Devolução results by validating POD files.
    
    Reads all POD files from subfolders in processado directory and validates:
    - Number of Nota Fiscal entries matches number of PDF files
    - POD PDF has correct number of pages (Nota Fiscal count + 1)
    
    Moves folders to 'aprovados' if valid, 'rejeitados' if invalid.
    """
    from airflow.models import Variable
    
    ti = context.get("task_instance")
    saga = get_saga_from_context(context)
    
    if not saga or not saga.get("saga_id"):
        raise AirflowException("SAGA not found in context, cannot categorize protocolo")
    
    log_saga(saga, task_id="categorize_protocolo_devolucao")
    
    # Get processado directory from Variable or use default
    processado_dir = Variable.get(
        "PROTOCOLO_PROCESSADO_DIR", 
        default_var="/opt/airflow/data/processado"
    )
    processado_path = Path(processado_dir)
    
    if not processado_path.exists():
        raise FileNotFoundError(f"Processado directory not found: {processado_path}")
    
    # Create aprovados and rejeitados folders
    aprovados_path = processado_path / "aprovados"
    rejeitados_path = processado_path / "rejeitados"
    aprovados_path.mkdir(exist_ok=True)
    rejeitados_path.mkdir(exist_ok=True)
    
    logger.info(f"Processing folders in: {processado_path}")
    logger.info(f"Aprovados folder: {aprovados_path}")
    logger.info(f"Rejeitados folder: {rejeitados_path}")
    
    # Find all subfolders (excluding aprovados, rejeitados, and "Nao processados")
    excluded_folders = {"aprovados", "rejeitados", "nao processados"}
    folders_to_process = [
        f for f in processado_path.iterdir()
        if f.is_dir() and f.name.lower() not in excluded_folders
    ]
    
    if not folders_to_process:
        logger.warning(f"No folders found to process in {processado_path}")
        return {
            "status": "success",
            "processed": 0,
            "aprovados": 0,
            "rejeitados": 0,
            "details": []
        }
    
    results = {
        "status": "success",
        "processed": 0,
        "aprovados": 0,
        "rejeitados": 0,
        "details": []
    }
    
    for folder_path in folders_to_process:
        logger.info(f"Processing folder: {folder_path.name}")
        
        try:
            is_valid, validation_details = validate_pod_folder(folder_path)
            
            if is_valid:
                # Move to aprovados
                destination = aprovados_path / folder_path.name
                move_folder(folder_path, destination)
                results["aprovados"] += 1
                logger.info(f"✓ Folder {folder_path.name} moved to aprovados")
            else:
                # Move to rejeitados
                destination = rejeitados_path / folder_path.name
                move_folder(folder_path, destination)
                results["rejeitados"] += 1
                logger.warning(f"✗ Folder {folder_path.name} moved to rejeitados: {validation_details.get('errors', [])}")
            
            results["processed"] += 1
            results["details"].append({
                "folder": folder_path.name,
                "is_valid": is_valid,
                **validation_details
            })
            
        except Exception as e:
            logger.error(f"Error processing folder {folder_path.name}: {e}")
            # Move to rejeitados on error
            try:
                destination = rejeitados_path / folder_path.name
                move_folder(folder_path, destination)
                results["rejeitados"] += 1
                results["details"].append({
                    "folder": folder_path.name,
                    "is_valid": False,
                    "error": str(e)
                })
            except Exception as move_error:
                logger.error(f"Failed to move folder {folder_path.name} to rejeitados: {move_error}")
    
    logger.info(
        f"Categorization complete: {results['processed']} processed, "
        f"{results['aprovados']} aprovados, {results['rejeitados']} rejeitados"
    )
    
    # Update SAGA with event
    if "events" not in saga:
        saga["events"] = []
    
    event = build_saga_event(
        event_type="TaskCompleted",
        event_data={
            "step": "categorize_protocolo_devolucao",
            "status": "SUCCESS",
            "processed": results["processed"],
            "aprovados": results["aprovados"],
            "rejeitados": results["rejeitados"],
            "details": results["details"],
        },
        context=context,
        task_id="categorize_protocolo_devolucao"
    )
    saga["events"].append(event)
    
    # Send event to rpa-api for persistence
    send_saga_event_to_api(saga, event, rpa_api_conn_id="rpa_api")
    
    # Update events_count
    saga["events_count"] = len(saga["events"])
    
    # Push updated SAGA back to XCom
    if ti:
        ti.xcom_push(key="saga", value=saga)
        ti.xcom_push(key="rpa_payload", value=saga)  # Backward compatibility
    
    # Log SAGA
    log_saga(saga, task_id="categorize_protocolo_devolucao")
    
    return results

