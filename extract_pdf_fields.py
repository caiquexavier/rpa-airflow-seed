"""
PDF Field Extraction Script - Pure functional approach.

Extracts structured fields from PDF documents using OCR.
Returns JSON with all extracted data.

Usage:
    python extract_pdf_fields.py <pdf_file_path>

Requirements:
    pip install pytesseract pillow pymupdf
    Also install Tesseract OCR: https://github.com/tesseract-ocr/tesseract
"""
import io
import json
import re
import sys
from functools import partial
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

try:
    import fitz  # PyMuPDF
    from PIL import Image, ImageFile
    Image.MAX_IMAGE_PIXELS = 500_000_000
    ImageFile.LOAD_TRUNCATED_IMAGES = True
except ImportError:
    print("Error: PyMuPDF (pymupdf) and Pillow are required.")
    print("Install with: pip install pymupdf pillow")
    sys.exit(1)

try:
    import pytesseract
    from pytesseract import TesseractNotFoundError
    # Try to find Tesseract in common installation paths
    import os
    tesseract_paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    ]
    tesseract_cmd = None
    for path in tesseract_paths:
        if os.path.exists(path):
            tesseract_cmd = path
            pytesseract.pytesseract.tesseract_cmd = path
            break
    
    TESSERACT_AVAILABLE = bool(pytesseract.get_tesseract_version())
    if TESSERACT_AVAILABLE:
        print("Tesseract OCR available")
except (ImportError, TesseractNotFoundError, Exception) as e:
    TESSERACT_AVAILABLE = False
    print(f"Warning: Tesseract OCR not available: {e}")
    print("OCR will be skipped.")


# ============================================================================
# Pure Functions - Text Processing
# ============================================================================

def normalize_text(text: str) -> str:
    """Normalize text: single spaces, trim."""
    return re.sub(r'\s+', ' ', text).strip()


def normalize_ocr_text(text: str) -> str:
    """Normalize OCR text by correcting common character confusions."""
    text = re.sub(r'(\d)[lI](\d)', r'\g<1>1\g<2>', text)  # l/I -> 1
    text = re.sub(r'(\d)O(\d)', r'\g<1>0\g<2>', text)   # O -> 0
    text = re.sub(r'(\d)\s+(\d)', r'\g<1>\g<2>', text)  # Remove spaces between digits
    return text


# ============================================================================
# Pure Functions - OCR
# ============================================================================

def calculate_dpi(page_rect) -> int:
    """Calculate adaptive DPI based on page size."""
    area = page_rect.width * page_rect.height
    return 200 if area > 1000000 else (250 if area > 500000 else 300)


def extract_text_with_ocr(image: Image.Image) -> str:
    """Extract text from image using OCR - pure function."""
    if not TESSERACT_AVAILABLE:
        return ""
    
    try:
        # Try with Portuguese first, fallback to English if not available
        try:
            ocr_text = pytesseract.image_to_string(
                image, lang='por', config='--oem 3 --psm 6'
            )
        except Exception:
            # Fallback to English if Portuguese not available
            ocr_text = pytesseract.image_to_string(
                image, lang='eng', config='--oem 3 --psm 6'
            )
        
        # Try digits-focused OCR if no numbers found
        if not re.search(r'\d{6,}', ocr_text):
            try:
                ocr_digits = pytesseract.image_to_string(
                    image, lang='por',
                    config='--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyzÁÉÍÓÚáéíóúÂÊÔâêôÃÕãõÇçÀà,.-/ '
                )
            except Exception:
                ocr_digits = pytesseract.image_to_string(
                    image, lang='eng',
                    config='--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz,.-/ '
                )
            if len(ocr_digits.strip()) > len(ocr_text.strip()):
                ocr_text = ocr_digits
        
        return normalize_ocr_text(ocr_text.strip()) if ocr_text.strip() else ""
    except Exception as e:
        print(f"  OCR error: {e}")
        return ""


def render_page_to_image(page, dpi: int) -> Optional[Image.Image]:
    """Render PDF page to PIL Image - pure function."""
    try:
        zoom = dpi / 72.0
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img_data = pix.tobytes("png")
        image = Image.open(io.BytesIO(img_data))
        return image.convert('RGB') if image.mode != 'RGB' else image
    except Exception:
        return None


# ============================================================================
# Pure Functions - PDF Text Extraction
# ============================================================================

def extract_page_text(page, force_ocr: bool = False, page_num: int = 0) -> str:
    """Extract text from a single PDF page - pure function."""
    page_text = page.get_text()
    text_length = len(page_text.strip())
    
    # Use OCR if needed
    if (force_ocr or text_length < 100) and TESSERACT_AVAILABLE:
        print(f"  Using OCR on page {page_num + 1} (direct text: {text_length} chars)")
        dpi = calculate_dpi(page.rect)
        image = render_page_to_image(page, dpi)
        if image:
            print(f"  Rendered image: {image.size[0]}x{image.size[1]} pixels at {dpi} DPI")
            ocr_text = extract_text_with_ocr(image)
            print(f"  OCR extracted: {len(ocr_text)} characters")
            return ocr_text if ocr_text else page_text
        else:
            print(f"  Failed to render page {page_num + 1} to image")
    
    return page_text


def extract_pdf_text(pdf_path: str, force_ocr: bool = False) -> str:
    """Extract all text from PDF - pure function."""
    doc = fitz.open(pdf_path)
    try:
        total_pages = len(doc)
        print(f"PDF contains {total_pages} page(s)")
        pages_text = [extract_page_text(doc[i], force_ocr, i) for i in range(total_pages)]
        full_text = "\n".join(pages_text)
        print(f"Total text extracted: {len(full_text)} characters")
        return full_text
    finally:
        doc.close()


# ============================================================================
# Pure Functions - Field Extraction
# ============================================================================

def find_pattern(text: str, pattern: str, flags: int = 0) -> Optional[str]:
    """Find first match of pattern in text - pure function."""
    match = re.search(pattern, text, flags)
    return match.group(1).strip() if match else None


def find_all_patterns(text: str, pattern: str, flags: int = 0) -> List[str]:
    """Find all matches of pattern in text - pure function."""
    return [m.strip() for m in re.findall(pattern, text, flags) if m.strip()]


def extract_nfe_number(text: str) -> Optional[str]:
    """Extract NF-E number from text - pure function."""
    nfe_mentions = list(re.finditer(r'NF[- ]?E|DADOS\s+DA\s+NF[- ]?E', text, re.IGNORECASE))
    
    for mention in nfe_mentions:
        start = max(0, mention.start() - 200)
        end = min(len(text), mention.end() + 400)
        search_text = text[start:end]
        
        # Try complete 9-digit number
        match = re.search(r'\b(00\d{7})\b', search_text)
        if match:
            return match.group(1)
        
        # Try split patterns
        patterns = [
            (r'(00\d{4})\s+(\d{1})\s+(\d{2})\b', lambda m: m.group(1) + m.group(2) + m.group(3)),
            (r'(00\d{4})\s+(\d{3})\b', lambda m: m.group(1) + m.group(2)),
            (r'(00\d{5})\s+(\d{2})\b', lambda m: m.group(1) + m.group(2)),
        ]
        
        for pattern, combiner in patterns:
            match = re.search(pattern, search_text)
            if match:
                nfe = combiner(match)
                if len(nfe) == 9 and nfe.startswith('00'):
                    return nfe
    
    return None


def extract_cnpj(text: str) -> List[str]:
    """Extract CNPJ numbers from text - pure function."""
    matches = re.findall(r'([O0-9]{14})', text)
    cnpjs = []
    seen = set()
    
    for match in matches:
        cleaned = match.replace('O', '0').replace('I', '1').replace('l', '1')
        digits = re.sub(r'[^\d]', '', cleaned)
        if len(digits) == 14 and digits not in seen:
            if not digits.startswith('00') and len(set(digits)) > 1:
                seen.add(digits)
                cnpjs.append(digits)
                if len(cnpjs) >= 2:
                    break
    
    return cnpjs


def extract_monetary_value(text: str) -> Optional[str]:
    """Extract monetary value from text - pure function."""
    # Try with "VALOR TOTAL" context
    match = find_pattern(text, r'VALOR\s+TOTAL[:\s|]*(\d{1,3}(?:[\.\s]\d{3})*(?:[,\s]\d{2})?)', re.IGNORECASE)
    if match:
        return match.replace(' ', '')
    
    # Try general monetary pattern
    matches = find_all_patterns(text, r'(\d{1,3}[\.\s]\d{3}[,\s]\d{2})')
    for match in matches:
        cleaned = match.replace(' ', '')
        if '.' in cleaned and ',' in cleaned and len(cleaned) > 6:
            return cleaned
    
    return None


def extract_date(text: str) -> Optional[str]:
    """Extract date from text - pure function."""
    # Try 8-digit format
    match = find_pattern(text, r'\b(\d{8})\b')
    if match and len(match) == 8:
        return f"{match[:2]}/{match[2:4]}/{match[4:]}"
    
    # Try standard date formats
    patterns = [
        r'(\d{1,2}/\d{1,2}/\d{4})',
        r'(\d{1,2}/\d{1,2}/\d{2})',
        r'(\d{1,2}[\/\s]\d{1,2}[\/\s]\d{2,4})',
    ]
    
    for pattern in patterns:
        match = find_pattern(text, pattern)
        if match:
            date_str = match.replace(' ', '/')
            # Fix OCR errors like "11/062025" -> "11/06/2025"
            if re.match(r'\d{1,2}/\d{4,6}', date_str):
                parts = date_str.split('/')
                if len(parts) == 2 and len(parts[1]) >= 4:
                    date_str = f"{parts[0]}/{parts[1][:2]}/{parts[1][2:]}"
            return date_str
    
    return None


def extract_company_name(text: str, section_pattern: str, stop_pattern: str) -> Optional[str]:
    """Extract company name from a section - pure function."""
    match = re.search(section_pattern, text, re.IGNORECASE | re.DOTALL)
    if not match:
        return None
    
    section = match.group(1)
    company_match = re.search(
        r'([A-Z][A-Z\s&]{5,60}?)(?:\s+[O0-9]{13,14}|\s+CNPJ|\s+' + stop_pattern + r'|\n)',
        section
    )
    
    if company_match:
        company = company_match.group(1).strip()
        company = re.sub(r'\s+', ' ', company)
        company = re.sub(r'[^\w\s&\-]', '', company)
        if 5 < len(company) < 80:
            return company
    
    return None


def extract_field(text: str, extractor: Callable[[str], Optional[str]]) -> Optional[str]:
    """Generic field extractor - pure function."""
    return extractor(text) if text else None


def extract_all_fields(text: str) -> Dict[str, str]:
    """Extract all identifiable fields from text - pure function."""
    if not text or not text.strip():
        return {}
    
    normalized = normalize_text(text)
    
    # Define field extractors
    extractors = {
        'nfe_number': extract_nfe_number,
        'valor_total': extract_monetary_value,
        'data_emissao': extract_date,
        'placa': partial(find_pattern, pattern=r'(?:PLACA|ANTT)[:\s]+([A-Z]{3}[\dA-Z]{4})', flags=re.IGNORECASE),
        'quantidade': partial(find_pattern, pattern=r'QUANTIDADE[:\s|]*(\d{1,3}(?:[\.\s]\d{3})*(?:[,\s]\d{3})?)', flags=re.IGNORECASE),
        'endereco_destinatario': partial(find_pattern, pattern=r'ENDERE[ÃÇ]O[:\s]+([A-Z][A-Z\s\d,.-]+?)(?:\s+UF|\n)', flags=re.IGNORECASE | re.DOTALL),
        'uf': partial(find_pattern, pattern=r'UF[:\s]+([A-Z]{2})\b', flags=re.IGNORECASE),
        'municipio': partial(find_pattern, pattern=r'MUNIC[ÃI]PIO[:\s]+([A-Z][A-Z\s]+?)(?:\s+PLACA|\s+ANTT|\n)', flags=re.IGNORECASE),
        'serie': partial(find_pattern, pattern=r'SERIE[:\s]+(\d+)', flags=re.IGNORECASE),
        'especie': partial(find_pattern, pattern=r'ESPECIE[:\s|]+([A-Z]{2,})', flags=re.IGNORECASE),
    }
    
    # Extract fields
    fields = {}
    for field_name, extractor in extractors.items():
        value = extract_field(normalized, extractor)
        if value:
            fields[field_name] = value
    
    # Extract CNPJs
    cnpjs = extract_cnpj(normalized)
    if cnpjs:
        fields['cnpj_transportadora'] = cnpjs[0]
        if len(cnpjs) > 1:
            fields['cnpj_destinatario'] = cnpjs[1]
    
    # Extract company names
    transportadora = extract_company_name(
        normalized,
        r'DADOS\s+TRANSPORTADORA(.*?)(?:DADOS\s+DA\s+NF|$)',
        'Frete|AV'
    )
    if transportadora:
        fields['razao_social_transportadora'] = transportadora
    
    destinatario = extract_company_name(
        normalized,
        r'DADOS\s+DA\s+NF[- ]?E(.*?)(?:VALOR\s+TOTAL|NF-E\s+DECLARA|308|$)',
        'ENDERE|ROD'
    )
    if destinatario:
        fields['razao_social_destinatario'] = destinatario
    
    # Clean up monetary and quantity values
    if 'valor_total' in fields:
        fields['valor_total'] = fields['valor_total'].replace(' ', '')
    if 'quantidade' in fields:
        fields['quantidade'] = fields['quantidade'].replace(' ', '')
    if 'placa' in fields:
        fields['placa'] = fields['placa'].upper()
    
    return fields


# ============================================================================
# Main Pipeline - Pure Functions
# ============================================================================

def process_pdf(pdf_path: str, force_ocr: bool = False) -> Dict[str, any]:
    """Process PDF and extract all fields - pure function."""
    if not Path(pdf_path).exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    
    # Extract text
    text = extract_pdf_text(pdf_path, force_ocr)
    
    # Count pages
    doc = fitz.open(pdf_path)
    page_count = len(doc)
    doc.close()
    
    # Extract fields
    fields = extract_all_fields(text)
    
    # Determine method
    method = "ocr" if (TESSERACT_AVAILABLE and len(text.strip()) < 100) else "direct"
    
    return {
        "file_path": pdf_path,
        "extraction_method": method,
        "fields": fields,
        "raw_text": text,
        "pages_processed": page_count,
        "fields_count": len(fields)
    }


# ============================================================================
# I/O Functions
# ============================================================================

def save_results(result: Dict, output_path: str) -> None:
    """Save results to JSON file."""
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)


def print_results(result: Dict) -> None:
    """Print results to console."""
    print("\n" + "="*60)
    print("EXTRACTION RESULTS (JSON):")
    print("="*60)
    print(json.dumps(result, indent=2, ensure_ascii=False))


# ============================================================================
# Main Entry Point
# ============================================================================

def main() -> None:
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python extract_pdf_fields.py <pdf_file_path>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    try:
        print(f"Processing PDF: {pdf_path}")
        result = process_pdf(pdf_path, force_ocr=False)
        
        print_results(result)
        
        output_file = Path(pdf_path).stem + "_extracted.json"
        save_results(result, output_file)
        print(f"\nResults saved to: {output_file}")
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
