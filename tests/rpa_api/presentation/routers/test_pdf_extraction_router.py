"""API integration tests for PDF extraction router."""
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from src.main import app
from src.domain.models.pdf_extraction_result import PdfExtractionResult

client = TestClient(app)


def test_extract_pdf_fields_endpoint_success():
    """Test successful PDF extraction endpoint."""
    with patch('src.presentation.controllers.pdf_extraction_controller.extract_pdf_fields_with_gpt') as mock_extract:
        # Arrange
        mock_result = PdfExtractionResult(
            extracted={"cnpj": "12.345.678/0001-90", "valor_total": "R$ 1.234,56"},
            raw_text="Sample PDF text"
        )
        mock_extract.return_value = mock_result
        
        payload = {
            "file_path": "/path/to/file.pdf",
            "fields": ["cnpj", "valor_total"]
        }
        
        # Act
        response = client.post("/rpa/pdf/extract-gpt", json=payload)
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "SUCCESS"
        assert data["extracted"]["cnpj"] == "12.345.678/0001-90"
        assert data["extracted"]["valor_total"] == "R$ 1.234,56"
        assert data["raw_text"] == "Sample PDF text"


def test_extract_pdf_fields_endpoint_file_not_found():
    """Test endpoint when file is not found."""
    with patch('src.presentation.controllers.pdf_extraction_controller.extract_pdf_fields_with_gpt') as mock_extract:
        # Arrange
        mock_extract.side_effect = FileNotFoundError("File not found")
        
        payload = {
            "file_path": "/nonexistent/file.pdf",
            "fields": ["cnpj"]
        }
        
        # Act
        response = client.post("/rpa/pdf/extract-gpt", json=payload)
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "FAIL"
        assert data["extracted"] == {}
        assert data["raw_text"] is None


def test_extract_pdf_fields_endpoint_validation_error():
    """Test endpoint with validation error."""
    with patch('src.presentation.controllers.pdf_extraction_controller.extract_pdf_fields_with_gpt') as mock_extract:
        # Arrange
        mock_extract.side_effect = ValueError("Invalid PDF file")
        
        payload = {
            "file_path": "/path/to/file.pdf",
            "fields": ["cnpj"]
        }
        
        # Act
        response = client.post("/rpa/pdf/extract-gpt", json=payload)
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "FAIL"
        assert data["extracted"] == {}
        assert data["raw_text"] is None


def test_extract_pdf_fields_endpoint_openai_error():
    """Test endpoint when OpenAI API fails."""
    with patch('src.presentation.controllers.pdf_extraction_controller.extract_pdf_fields_with_gpt') as mock_extract:
        # Arrange
        mock_extract.side_effect = RuntimeError("OpenAI API error")
        
        payload = {
            "file_path": "/path/to/file.pdf",
            "fields": ["cnpj"]
        }
        
        # Act
        response = client.post("/rpa/pdf/extract-gpt", json=payload)
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "FAIL"
        assert data["extracted"] == {}
        assert data["raw_text"] is None


def test_extract_pdf_fields_endpoint_invalid_payload():
    """Test endpoint with invalid payload."""
    # Missing required fields
    payload = {
        "file_path": "/path/to/file.pdf"
        # Missing "fields"
    }
    
    response = client.post("/rpa/pdf/extract-gpt", json=payload)
    assert response.status_code == 422  # Validation error

