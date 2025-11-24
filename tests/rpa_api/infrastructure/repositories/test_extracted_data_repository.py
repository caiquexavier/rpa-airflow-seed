"""Unit tests for extracted data repository."""
import sys
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Mock the config module before importing repository
mock_config = MagicMock()
mock_config.get_postgres_dsn = Mock(return_value="postgresql://test:test@localhost:5432/testdb")
sys.modules['src.config.config'] = mock_config

from src.domain.entities.extracted_data import ExtractedData
from src.infrastructure.repositories.extracted_data_repository import (
    create_extracted_data,
    get_extracted_data,
    get_all_extracted_data_for_saga,
    update_extracted_data
)


@pytest.mark.unit
class TestCreateExtractedData:
    """Tests for create_extracted_data function."""

    @patch('src.infrastructure.repositories.extracted_data_repository.execute_insert')
    def test_create_extracted_data_success(self, mock_insert):
        """Test creating extracted data record."""
        mock_insert.return_value = 1
        
        result = create_extracted_data(saga_id=123, metadata={"nf_e": "12345", "cnpj": "12.345.678/0001-90"})
        
        assert result == 1
        mock_insert.assert_called_once()
        call_args = mock_insert.call_args
        assert call_args[0][1][0] == 123  # saga_id
        assert "nf_e" in call_args[0][1][1]  # metadata JSON

    @patch('src.infrastructure.repositories.extracted_data_repository.execute_insert')
    def test_create_extracted_data_returns_dict(self, mock_insert):
        """Test create when execute_insert returns dict."""
        mock_insert.return_value = {"id": 42}
        
        result = create_extracted_data(saga_id=123, metadata={"test": "data"})
        
        assert result == 42

    @patch('src.infrastructure.repositories.extracted_data_repository.execute_insert')
    def test_create_extracted_data_returns_none(self, mock_insert):
        """Test create when execute_insert returns None."""
        mock_insert.return_value = None
        
        result = create_extracted_data(saga_id=123, metadata={"test": "data"})
        
        assert result == 0


@pytest.mark.unit
class TestGetExtractedData:
    """Tests for get_extracted_data function."""

    @patch('src.infrastructure.repositories.extracted_data_repository.execute_query')
    def test_get_extracted_data_success(self, mock_query):
        """Test getting extracted data by ID."""
        mock_query.return_value = [{
            "id": 1,
            "saga_id": 123,
            "metadata": '{"nf_e": "12345", "cnpj": "12.345.678/0001-90"}',
            "created_at": datetime(2024, 1, 1, 12, 0, 0)
        }]
        
        result = get_extracted_data(1)
        
        assert result is not None
        assert result.id == 1
        assert result.saga_id == 123
        assert result.metadata["nf_e"] == "12345"

    @patch('src.infrastructure.repositories.extracted_data_repository.execute_query')
    def test_get_extracted_data_not_found(self, mock_query):
        """Test getting non-existent extracted data."""
        mock_query.return_value = []
        
        result = get_extracted_data(999)
        
        assert result is None


@pytest.mark.unit
class TestGetAllExtractedDataForSaga:
    """Tests for get_all_extracted_data_for_saga function."""

    @patch('src.infrastructure.repositories.extracted_data_repository.execute_query')
    def test_get_all_extracted_data_for_saga_success(self, mock_query):
        """Test getting all extracted data for a saga."""
        mock_query.return_value = [
            {
                "id": 1,
                "saga_id": 123,
                "metadata": '{"nf_e": "12345"}',
                "created_at": datetime(2024, 1, 1, 12, 0, 0)
            },
            {
                "id": 2,
                "saga_id": 123,
                "metadata": '{"nf_e": "67890"}',
                "created_at": datetime(2024, 1, 1, 13, 0, 0)
            }
        ]
        
        result = get_all_extracted_data_for_saga(123)
        
        assert len(result) == 2
        assert result[0].id == 1
        assert result[1].id == 2

    @patch('src.infrastructure.repositories.extracted_data_repository.execute_query')
    def test_get_all_extracted_data_for_saga_empty(self, mock_query):
        """Test getting extracted data when none exists."""
        mock_query.return_value = []
        
        result = get_all_extracted_data_for_saga(123)
        
        assert len(result) == 0


@pytest.mark.unit
class TestUpdateExtractedData:
    """Tests for update_extracted_data function."""

    @patch('src.infrastructure.repositories.extracted_data_repository.execute_update')
    def test_update_extracted_data_success(self, mock_update):
        """Test updating extracted data."""
        mock_update.return_value = 1
        
        result = update_extracted_data(id=1, metadata={"nf_e": "99999"})
        
        assert result is True
        mock_update.assert_called_once()

    @patch('src.infrastructure.repositories.extracted_data_repository.execute_update')
    def test_update_extracted_data_not_found(self, mock_update):
        """Test updating non-existent extracted data."""
        mock_update.return_value = 0
        
        result = update_extracted_data(id=999, metadata={"test": "data"})
        
        assert result is False

