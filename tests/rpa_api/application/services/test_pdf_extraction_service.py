"""Unit tests for PDF extraction service."""
import pytest
from unittest.mock import patch, MagicMock

from src.application.services.pdf_extraction_service import extract_pdf_fields_with_gpt
from src.domain.models.pdf_extraction_request import PdfExtractionRequest
from src.domain.models.pdf_extraction_result import PdfExtractionResult


@patch('src.application.services.pdf_extraction_service.extract_fields_with_gpt')
@patch('src.application.services.pdf_extraction_service.extract_text_from_pdf')
def test_extract_pdf_fields_with_gpt_success(mock_extract_text, mock_extract_fields):
    """Test successful PDF field extraction."""
    # Arrange
    mock_extract_text.return_value = "Sample PDF text with CNPJ: 12.345.678/0001-90"
    mock_extract_fields.return_value = {
        "cnpj": "12.345.678/0001-90",
        "valor_total": "R$ 1.234,56"
    }
    
    request = PdfExtractionRequest(
        file_path="/path/to/file.pdf",
        fields=["cnpj", "valor_total"]
    )
    
    # Act
    result = extract_pdf_fields_with_gpt(request)
    
    # Assert
    assert isinstance(result, PdfExtractionResult)
    assert result.extracted["cnpj"] == "12.345.678/0001-90"
    assert result.extracted["valor_total"] == "R$ 1.234,56"
    assert result.raw_text == "Sample PDF text with CNPJ: 12.345.678/0001-90"
    mock_extract_text.assert_called_once_with("/path/to/file.pdf")
    mock_extract_fields.assert_called_once()


@patch('src.application.services.pdf_extraction_service.extract_fields_with_gpt')
@patch('src.application.services.pdf_extraction_service.extract_text_from_pdf')
def test_extract_pdf_fields_with_gpt_missing_field(mock_extract_text, mock_extract_fields):
    """Test extraction when GPT doesn't return all requested fields."""
    # Arrange
    mock_extract_text.return_value = "Sample PDF text"
    mock_extract_fields.return_value = {
        "cnpj": "12.345.678/0001-90"
        # Missing "valor_total"
    }
    
    request = PdfExtractionRequest(
        file_path="/path/to/file.pdf",
        fields=["cnpj", "valor_total"]
    )
    
    # Act
    result = extract_pdf_fields_with_gpt(request)
    
    # Assert
    assert result.extracted["cnpj"] == "12.345.678/0001-90"
    assert result.extracted["valor_total"] is None


@patch('src.application.services.pdf_extraction_service.extract_text_from_pdf')
def test_extract_pdf_fields_with_gpt_file_not_found(mock_extract_text):
    """Test that FileNotFoundError is propagated."""
    # Arrange
    mock_extract_text.side_effect = FileNotFoundError("File not found")
    
    request = PdfExtractionRequest(
        file_path="/nonexistent/file.pdf",
        fields=["cnpj"]
    )
    
    # Act & Assert
    with pytest.raises(FileNotFoundError):
        extract_pdf_fields_with_gpt(request)

