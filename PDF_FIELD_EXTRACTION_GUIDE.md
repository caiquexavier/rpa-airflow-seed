# PDF Field Extraction Guide

## Overview

This guide explains how to extract all fields and values from PDF files using Python OCR. The script `extract_pdf_fields.py` provides a complete solution that:

1. **Tries text extraction first** (using `pdfplumber`) - Fast and accurate if PDF has a text layer
2. **Falls back to OCR** (using `pytesseract`) - For scanned PDFs or images
3. **Extracts structured fields** - Uses pattern matching to identify common document fields
4. **Returns JSON** - Structured output with all extracted data

## Installation

```bash
# Install Python libraries
pip install pytesseract pillow pdf2image pdfplumber

# Install Tesseract OCR (required for OCR functionality)
# Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki
# macOS: brew install tesseract
# Linux: sudo apt-get install tesseract-ocr
```

## Usage

```bash
python extract_pdf_fields.py <path_to_pdf_file>
```

Example:
```bash
python extract_pdf_fields.py shared/data/processar/537834_page_1.pdf
```

## Output Format

The script returns a JSON object with:

```json
{
  "file_path": "path/to/file.pdf",
  "extraction_method": "pdfplumber" or "ocr",
  "fields": {
    "nfe_number": "005043156",
    "cnpj_transportadora": "12345678000190",
    "cnpj_destinatario": "98765432000111",
    "valor_total": "2.948,00",
    "data_emissao": "11/06/2025",
    "razao_social_transportadora": "COMPANY NAME",
    "razao_social_destinatario": "DESTINATION COMPANY",
    "placa": "ABC1234",
    "quantidade": "308",
    "endereco_destinatario": "ROD AL HO 123 CITY",
    "uf": "SP",
    "municipio": "SANTOS",
    "serie": "1",
    "especie": "NF-E"
  },
  "raw_text": "Full extracted text...",
  "pages_processed": 1,
  "fields_count": 13
}
```

## Extracted Fields

The script automatically identifies and extracts:

- **NF-E Number** - 9-digit invoice number
- **CNPJ** - Company registration numbers (transportadora and destinatario)
- **Monetary Values** - Total values in Brazilian format (e.g., 2.948,00)
- **Dates** - Emission dates in DD/MM/YYYY format
- **Company Names** - Razão social (legal company names)
- **License Plates** - Vehicle license plates (PLACA)
- **Quantities** - Product quantities
- **Addresses** - Destination addresses
- **Location Data** - UF (state) and municipality
- **Document Details** - Series, species/type

## How It Works

### 1. Text Extraction (pdfplumber)
- Fast method for PDFs with text layers
- Directly extracts text from PDF structure
- No image processing required

### 2. OCR Extraction (pytesseract)
- For scanned PDFs or image-based documents
- Converts PDF pages to images (300 DPI)
- Detects and corrects page orientation
- Extracts text using Tesseract OCR with Portuguese language support

### 3. Field Extraction
- Uses regex pattern matching to identify structured data
- Handles common OCR errors (O→0, I→1)
- Normalizes text and extracts values based on context
- Removes empty/null values from results

## Pattern Matching Examples

The script uses intelligent pattern matching:

- **NF-E Numbers**: Handles split numbers like "005043 1 56" → "005043156"
- **CNPJ**: Extracts 14-digit sequences, filters out dates/phone numbers
- **Monetary Values**: Recognizes Brazilian format (1.234,56)
- **Dates**: Handles various formats including OCR errors
- **Company Names**: Extracts uppercase text from specific document sections

## Error Handling

- Automatically falls back from text extraction to OCR
- Handles missing libraries gracefully
- Provides clear error messages
- Saves results to JSON file for inspection

## Customization

To extract additional fields, modify the `extract_all_fields()` function in `extract_pdf_fields.py`:

```python
# Add new field extraction pattern
new_field_match = re.search(r'YOUR_PATTERN', normalized_text, re.IGNORECASE)
if new_field_match:
    result["your_field_name"] = new_field_match.group(1).strip()
```

## Notes

- The script is standalone and doesn't modify the project
- Results are saved to `<pdf_filename>_extracted.json`
- OCR processing can be slow for large PDFs (use text extraction when possible)
- Portuguese language support improves accuracy for Brazilian documents

