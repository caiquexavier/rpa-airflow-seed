"""Unit tests for PDF reader."""
import pytest
from pathlib import Path

from src.infrastructure.pdf.pdf_reader import extract_text_from_pdf


def test_extract_text_from_pdf_file_not_found():
    """Test that FileNotFoundError is raised for non-existent file."""
    with pytest.raises(FileNotFoundError):
        extract_text_from_pdf("/nonexistent/file.pdf")


def test_extract_text_from_pdf_invalid_path(tmp_path):
    """Test that ValueError is raised for invalid path."""
    invalid_path = tmp_path / "not_a_file"
    invalid_path.mkdir()
    
    with pytest.raises(ValueError, match="Path is not a file"):
        extract_text_from_pdf(str(invalid_path))


def test_extract_text_from_pdf_empty_pdf(tmp_path):
    """Test extraction from an empty PDF (if we can create one)."""
    # This test would require a sample PDF file
    # For now, we'll skip it or create a minimal test PDF
    # In a real scenario, you'd have a test PDF in tests/resources/
    pass

