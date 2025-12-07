"""PDF generation service for protocolo de devolucao."""
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from fpdf import FPDF

logger = logging.getLogger(__name__)


class ProtocoloDeDevolucaoPDF(FPDF):
    """PDF generator for Protocolo de Devolução documents."""

    def header(self, doc_transportes: str):
        """
        Draw PDF header with company name and title bar.
        
        Args:
            doc_transportes: Documento de Transporte value to display in title
        """
        # Company name (simplified logo area)
        self.set_xy(20, 15)
        self.set_font("Helvetica", "B", 18)
        self.cell(0, 10, "MERCOSUL LINE")

        # Blue title bar
        self.set_fill_color(0, 51, 102)  # dark blue
        self.set_text_color(255, 255, 255)
        self.set_xy(20, 40)
        self.set_font("Helvetica", "B", 11)
        self.cell(180, 8, f"PROTOCOLO DE DEVOLUÇÃO {doc_transportes}", border=1, ln=1, align="C", fill=True)

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
        w_qtd = 20
        w_doc = 50
        w_entrega = 35
        w_nf = 40
        w_reg = 35
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

        # Data rows
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

        # Add empty rows to fill the page (up to 20 total rows)
        empty_rows_needed = max(0, 20 - len(table_data))
        for _ in range(empty_rows_needed):
            self.set_xy(left_x, y)
            self.cell(w_qtd, row_height, "", border=1)
            self.cell(w_doc, row_height, "", border=1)
            self.cell(w_entrega, row_height, "", border=1)
            self.cell(w_nf, row_height, "", border=1)
            self.cell(w_reg, row_height, "", border=1, ln=1)
            y += row_height


def build_table_data_from_saga(
    saga_data: Dict[str, Any], 
    doc_transportes_filter: Optional[str] = None
) -> List[Tuple[str, str, str, str, str]]:
    """
    Build table data from SAGA structure, optionally filtered by doc_transportes.
    
    Args:
        saga_data: SAGA data dictionary containing doc_transportes_list and extracted_data
        doc_transportes_filter: Optional doc_transportes value to filter by (if None, includes all)
        
    Returns:
        List of tuples (quantidade, documento_transporte, entrega, nota_fiscal, regular_irregular)
    """
    table_rows: List[Tuple[str, str, str, str, str]] = []
    
    doc_transportes_list = saga_data.get("doc_transportes_list", [])
    extracted_data = saga_data.get("extracted_data", {})
    
    row_number = 1
    
    for doc_entry in doc_transportes_list:
        doc_transportes = str(doc_entry.get("doc_transportes", ""))
        nf_e_list = doc_entry.get("nf_e", [])
        
        if not doc_transportes:
            continue
        
        # Filter by doc_transportes if specified
        if doc_transportes_filter and doc_transportes != doc_transportes_filter:
            continue
        
        # Use today's date for entrega (delivery date)
        today = datetime.now()
        entrega_date = today.strftime("%d/%m/%Y")
        regular_irregular = ""
        
        # Process each NF-e for this doc_transportes
        for nf_e in nf_e_list:
            nf_e_str = str(nf_e).strip()
            if not nf_e_str:
                continue
            
            # Add row for this NF-e with today's date as entrega
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
    doc_transportes: str
) -> None:
    """
    Generate PDF with protocolo de devolucao layout for a specific doc_transportes.
    
    Args:
        output_path: Path where PDF will be saved
        saga_data: SAGA data dictionary with doc_transportes_list and extracted_data
        doc_transportes: Documento de Transporte value to use in header and filter data
    """
    # Build table data from SAGA filtered by doc_transportes
    table_data = build_table_data_from_saga(saga_data, doc_transportes_filter=doc_transportes)
    
    if not table_data:
        logger.warning("No table data found for doc_transportes %s, generating empty PDF", doc_transportes)
    
    # Create PDF
    pdf = ProtocoloDeDevolucaoPDF(orientation="L", unit="mm", format="A4")
    pdf.add_page()
    pdf.header(doc_transportes=str(doc_transportes))
    pdf.draw_table(table_data)
    
    # Ensure output directory exists
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Save PDF
    pdf.output(str(output_file))
    logger.info("Generated PDF protocolo de devolucao for doc_transportes %s at: %s", doc_transportes, output_path)

