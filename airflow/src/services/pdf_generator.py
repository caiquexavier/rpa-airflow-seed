"""PDF generation service for protocolo de devolucao."""
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from fpdf import FPDF

logger = logging.getLogger(__name__)


class ProtocoloDeDevolucaoPDF(FPDF):
    """PDF generator for Protocolo de Devolução documents."""

    def __init__(self, doc_transportes: str, logo_path: str, *args, **kwargs):
        """
        Initialize PDF with doc_transportes value.
        
        Args:
            doc_transportes: Documento de Transporte value to display in header
            logo_path: Path to logo image file (PNG, JPG, etc.) - required
            *args, **kwargs: Arguments passed to FPDF.__init__ (orientation, unit, format, etc.)
        """
        super().__init__(*args, **kwargs)
        self.doc_transportes = doc_transportes
        self.logo_path = logo_path

    def header(self):
        """
        Draw PDF header with company logo and title bar.
        Called automatically by FPDF when add_page() is called.
        Must have no required arguments (only self) to be compatible with FPDF.
        """
        # Display logo image
        logo_x = 20
        logo_y = 15
        logo_width = 50  # Width in mm (height auto to maintain aspect ratio)
        
        logo_path_obj = Path(self.logo_path)
        if not logo_path_obj.exists():
            raise FileNotFoundError(f"Logo file not found: {self.logo_path}")
        
        absolute_logo_path = str(logo_path_obj.resolve())
        logger.info("Displaying logo from: %s (file size: %d bytes)", absolute_logo_path, logo_path_obj.stat().st_size)
        
        # Display logo image - FPDF requires absolute path
        # FPDF2 supports PNG, JPG, JPEG formats
        # Only specifying width (w) will auto-calculate height to maintain aspect ratio
        self.image(absolute_logo_path, x=logo_x, y=logo_y, w=logo_width)
        logger.info("Logo image displayed successfully")

        # Blue title bar
        self.set_fill_color(0, 51, 102)  # dark blue
        self.set_text_color(255, 255, 255)
        self.set_xy(20, 40)
        self.set_font("Helvetica", "B", 11)
        self.cell(180, 8, f"PROTOCOLO DE DEVOLUÇÃO {self.doc_transportes}", border=1, ln=1, align="C", fill=True)

        # Restore default text color for rest of document
        self.set_text_color(0, 0, 0)

    def draw_table(self, table_data: List[Tuple[str, str, str, str, str]]):
        """
        Draw table with protocol data.
        
        Args:
            table_data: List of tuples (quantidade, documento_transporte, entrega, nota_fiscal, regular_irregular)
        """
        # Table position and dimensions
        left_x = 20
        top_y = 48
        table_width = 180

        # Column widths (must sum to table_width)
        w_qtd = 15
        w_doc = 42
        w_entrega = 25
        w_nf = 28
        w_reg = 70  # Doubled from 35 to accommodate "Regular / Irregular" text
        row_height_header = 8
        row_height = 7

        # Header row
        self.set_xy(left_x, top_y)
        self.set_font("Helvetica", "B", 9)
        self.cell(w_qtd, row_height_header, "Quantidade", border=1, align="C")
        self.cell(w_doc, row_height_header, "Documento de\nTransporte", border=1, align="C")
        self.cell(w_entrega, row_height_header, "Entrega", border=1, align="C")
        self.cell(w_nf, row_height_header, "Nº Nota Fiscal", border=1, align="C")
        self.cell(w_reg, row_height_header, "Regular / Irregular", border=1, ln=1, align="C")

        # Data rows - only add rows that match NF-e quantity (no blank rows)
        self.set_font("Helvetica", "", 9)
        y = top_y + row_height_header
        
        for row in table_data:
            self.set_xy(left_x, y)
            self.cell(w_qtd, row_height, str(row[0]), border=1, align="C")
            self.cell(w_doc, row_height, str(row[1]), border=1, align="C")
            self.cell(w_entrega, row_height, str(row[2]), border=1, align="C")
            self.cell(w_nf, row_height, str(row[3]), border=1, align="C")
            self.cell(w_reg, row_height, str(row[4]), border=1, ln=1, align="C")
            y += row_height


def build_table_data_from_saga(
    saga_data: Dict[str, Any], 
    doc_transportes_filter: Optional[str] = None
) -> List[Tuple[str, str, str, str, str]]:
    """
    Build table data from SAGA structure, optionally filtered by doc_transportes.
    
    Row numbers start at 1 and increment sequentially for each NF-e, matching the quantity.
    When filtering by doc_transportes, row numbers start at 1 for that specific doc_transportes.
    
    Args:
        saga_data: SAGA data dictionary containing doc_transportes_list and extracted_data
        doc_transportes_filter: Optional doc_transportes value to filter by (if None, includes all)
        
    Returns:
        List of tuples (quantidade, documento_transporte, entrega, nota_fiscal, regular_irregular)
    """
    table_rows: List[Tuple[str, str, str, str, str]] = []
    
    doc_transportes_list = saga_data.get("doc_transportes_list", [])
    extracted_data = saga_data.get("extracted_data", {})
    
    # Row number starts at 1 and increments sequentially for each NF-e
    # When filtering by doc_transportes, row_number starts at 1 for that specific doc_transportes
    # Otherwise, row_number continues sequentially across all doc_transportes entries
    row_number = 1
    
    for doc_entry in doc_transportes_list:
        doc_transportes = str(doc_entry.get("doc_transportes", ""))
        nf_e_list = doc_entry.get("nf_e", [])
        
        if not doc_transportes:
            continue
        
        # Filter by doc_transportes if specified
        if doc_transportes_filter and doc_transportes != doc_transportes_filter:
            continue
        
        # Reset row_number to 1 when filtering by specific doc_transportes
        # This ensures row numbers match the NF-e quantity for that doc_transportes (1, 2, 3, ...)
        # When filtering, we only process one doc_transportes, so numbering should start at 1
        if doc_transportes_filter:
            row_number = 1
        
        # Use today's date for entrega (delivery date)
        today = datetime.now()
        entrega_date = today.strftime("%d/%m/%Y")
        regular_irregular = ""
        
        # Process each NF-e for this doc_transportes
        # Row number increments sequentially: 1, 2, 3, ... matching NF-e quantity
        for nf_e in nf_e_list:
            nf_e_str = str(nf_e).strip()
            if not nf_e_str:
                continue
            
            # Add row for this NF-e with sequential row number matching NF-e quantity
            table_rows.append((
                str(row_number),
                doc_transportes,
                entrega_date,
                nf_e_str,
                regular_irregular
            ))
            row_number += 1
    
    return table_rows


def create_protocolo_de_devolucao_pdf(
    output_path: str,
    saga_data: Dict[str, Any],
    doc_transportes: str,
    logo_path: Optional[str] = None
) -> None:
    """
    Generate PDF with protocolo de devolucao layout for a specific doc_transportes.
    
    Args:
        output_path: Path where PDF will be saved
        saga_data: SAGA data dictionary with doc_transportes_list and extracted_data
        doc_transportes: Documento de Transporte value to use in header and filter data
        logo_path: Path to logo image file. Default: /opt/airflow/assets/logos/mercosul_line_logo.jpg
    """
    # Build table data from SAGA filtered by doc_transportes
    table_data = build_table_data_from_saga(saga_data, doc_transportes_filter=doc_transportes)
    
    if not table_data:
        logger.warning("No table data found for doc_transportes %s, generating empty PDF", doc_transportes)
    
    # Use default logo path if not provided
    if not logo_path:
        logo_path = "/opt/airflow/assets/logos/mercosul_line_logo.jpg"
    
    # Verify logo file exists
    logo_path_obj = Path(logo_path)
    if not logo_path_obj.exists():
        raise FileNotFoundError(f"Logo file not found: {logo_path}. Please ensure the logo is at /opt/airflow/assets/logos/mercosul_line_logo.jpg")
    
    logger.info("Using logo: %s", str(logo_path_obj.resolve()))
    
    # Create PDF with doc_transportes value and logo path
    # doc_transportes is passed to __init__ and stored as instance variable
    # header() will be called automatically by add_page() and uses self.doc_transportes and self.logo_path
    pdf = ProtocoloDeDevolucaoPDF(
        doc_transportes=str(doc_transportes),
        logo_path=logo_path,
        orientation="L",
        unit="mm",
        format="A4"
    )
    try:
        pdf.add_page()  # This automatically calls header() which uses self.doc_transportes and self.logo_path
        pdf.draw_table(table_data)
        
        # Ensure output directory exists
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Save PDF
        pdf.output(str(output_file))
        
        # Verify PDF was created
        if not output_file.exists():
            raise RuntimeError(f"PDF file was not created at {output_path}")
        if output_file.stat().st_size == 0:
            raise RuntimeError(f"PDF file is empty at {output_path}")
        
        logger.info("Generated PDF protocolo de devolucao for doc_transportes %s at: %s (%d bytes)", 
                   doc_transportes, output_path, output_file.stat().st_size)
    except Exception as e:
        logger.error("Failed to generate PDF for doc_transportes %s: %s", doc_transportes, e, exc_info=True)
        raise

