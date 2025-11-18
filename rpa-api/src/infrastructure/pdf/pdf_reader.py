"""PDF reader infrastructure - extracts text from PDF files."""
import logging
from pathlib import Path

import pdfplumber

logger = logging.getLogger(__name__)


def extract_text_from_pdf(file_path: str) -> str:
    """
    Open the given PDF file path and return extracted text as a single string.

    Raise a clear exception if the file does not exist or cannot be read.

    Args:
        file_path: Path to the PDF file

    Returns:
        Extracted text as a single string

    Raises:
        FileNotFoundError: If the file does not exist
        ValueError: If the file cannot be read or processed
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"PDF file not found: {file_path}")

    if not path.is_file():
        raise ValueError(f"Path is not a file: {file_path}")

    try:
        text_parts = []
        with pdfplumber.open(file_path) as pdf:
            logger.info(f"Processing PDF with {len(pdf.pages)} pages")
            for page_num, page in enumerate(pdf.pages, start=1):
                try:
                    page_text = page.extract_text()
                    if page_text is None:
                        page_text = ""
                    text_parts.append(page_text)
                except Exception as e:
                    logger.warning(f"Error extracting text from page {page_num}: {e}")
                    text_parts.append("")

        full_text = "\n".join(text_parts)
        logger.info(f"Extracted {len(full_text)} characters from PDF")
        return full_text

    except Exception as e:
        logger.error(f"Error reading PDF file {file_path}: {e}")
        raise ValueError(f"Failed to read PDF file: {e}") from e

