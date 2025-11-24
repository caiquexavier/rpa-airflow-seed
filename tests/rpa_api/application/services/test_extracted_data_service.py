"""Unit tests for extracted data service."""
import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from src.domain.entities.extracted_data import ExtractedData
from src.application.services.extracted_data_service import (
    create_extracted_metadata,
    read_extracted_metadata,
    read_extracted_metadata_by_saga,
    update_extracted_metadata
)


@pytest.mark.unit
class TestCreateExtractedMetadata:
    """Tests for create_extracted_metadata function."""

    @patch('src.application.services.extracted_data_service.create_extracted_data')
    def test_create_extracted_metadata_success(self, mock_create):
        """Test creating extracted metadata."""
        mock_create.return_value = 1
        
        result = create_extracted_metadata(saga_id=123, metadata={"nf_e": "12345"})
        
        assert result == 1
        mock_create.assert_called_once_with(123, {"nf_e": "12345"})

    @patch('src.application.services.extracted_data_service.create_extracted_data')
    def test_create_extracted_metadata_invalid_saga_id(self, mock_create):
        """Test creating with invalid saga_id."""
        with pytest.raises(ValueError, match="saga_id must be a positive integer"):
            create_extracted_metadata(saga_id=0, metadata={"test": "data"})
        
        mock_create.assert_not_called()

    @patch('src.application.services.extracted_data_service.create_extracted_data')
    def test_create_extracted_metadata_empty_metadata(self, mock_create):
        """Test creating with empty metadata."""
        with pytest.raises(ValueError, match="metadata cannot be empty"):
            create_extracted_metadata(saga_id=123, metadata={})
        
        mock_create.assert_not_called()


@pytest.mark.unit
class TestReadExtractedMetadata:
    """Tests for read_extracted_metadata function."""

    @patch('src.application.services.extracted_data_service.get_extracted_data')
    def test_read_extracted_metadata_success(self, mock_get):
        """Test reading extracted metadata."""
        entity = ExtractedData(
            id=1,
            saga_id=123,
            metadata={"nf_e": "12345"},
            created_at=datetime(2024, 1, 1, 12, 0, 0)
        )
        mock_get.return_value = entity
        
        result = read_extracted_metadata(1)
        
        assert result is not None
        assert result.id == 1
        assert result.saga_id == 123

    @patch('src.application.services.extracted_data_service.get_extracted_data')
    def test_read_extracted_metadata_invalid_id(self, mock_get):
        """Test reading with invalid ID."""
        result = read_extracted_metadata(0)
        
        assert result is None
        mock_get.assert_not_called()


@pytest.mark.unit
class TestReadExtractedMetadataBySaga:
    """Tests for read_extracted_metadata_by_saga function."""

    @patch('src.application.services.extracted_data_service.get_all_extracted_data_for_saga')
    def test_read_extracted_metadata_by_saga_success(self, mock_get_all):
        """Test reading all extracted metadata for a saga."""
        entities = [
            ExtractedData(
                id=1,
                saga_id=123,
                metadata={"nf_e": "12345"},
                created_at=datetime(2024, 1, 1, 12, 0, 0)
            )
        ]
        mock_get_all.return_value = entities
        
        result = read_extracted_metadata_by_saga(123)
        
        assert len(result) == 1
        assert result[0].id == 1

    @patch('src.application.services.extracted_data_service.get_all_extracted_data_for_saga')
    def test_read_extracted_metadata_by_saga_invalid_id(self, mock_get_all):
        """Test reading with invalid saga_id."""
        result = read_extracted_metadata_by_saga(0)
        
        assert result == []
        mock_get_all.assert_not_called()


@pytest.mark.unit
class TestUpdateExtractedMetadata:
    """Tests for update_extracted_metadata function."""

    @patch('src.application.services.extracted_data_service.update_extracted_data')
    def test_update_extracted_metadata_success(self, mock_update):
        """Test updating extracted metadata."""
        mock_update.return_value = True
        
        result = update_extracted_metadata(id=1, metadata={"nf_e": "99999"})
        
        assert result is True
        mock_update.assert_called_once_with(1, {"nf_e": "99999"})

    @patch('src.application.services.extracted_data_service.update_extracted_data')
    def test_update_extracted_metadata_invalid_id(self, mock_update):
        """Test updating with invalid ID."""
        result = update_extracted_metadata(id=0, metadata={"test": "data"})
        
        assert result is False
        mock_update.assert_not_called()

    @patch('src.application.services.extracted_data_service.update_extracted_data')
    def test_update_extracted_metadata_empty_metadata(self, mock_update):
        """Test updating with empty metadata."""
        with pytest.raises(ValueError, match="metadata cannot be empty"):
            update_extracted_metadata(id=1, metadata={})
        
        mock_update.assert_not_called()

