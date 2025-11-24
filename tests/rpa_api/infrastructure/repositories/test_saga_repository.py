"""Unit tests for saga repository."""
import sys
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Mock the config module before importing repository
mock_config = MagicMock()
mock_config.get_postgres_dsn = Mock(return_value="postgresql://test:test@localhost:5432/testdb")
sys.modules['src.config.config'] = mock_config

from src.domain.entities.saga import Saga, SagaState, SagaEvent
from src.infrastructure.repositories.saga_repository import (
    save_saga, get_saga, get_saga_by_exec_id
)


@pytest.mark.unit
class TestSaveSaga:
    """Tests for save_saga function."""

    @patch('src.infrastructure.repositories.saga_repository.execute_insert')
    def test_save_new_saga(self, mock_insert, sample_saga: Saga):
        """Test saving a new saga (insert)."""
        new_saga = Saga(
            saga_id=0,
            exec_id=sample_saga.exec_id,
            rpa_key_id=sample_saga.rpa_key_id,
            rpa_request_object=sample_saga.rpa_request_object,
            current_state=sample_saga.current_state,
            events=[],
            created_at=sample_saga.created_at,
            updated_at=sample_saga.updated_at
        )
        mock_insert.return_value = 1

        saga_id = save_saga(new_saga)

        assert saga_id == 1
        mock_insert.assert_called_once()

    @patch('src.infrastructure.repositories.saga_repository.execute_update')
    def test_save_existing_saga(self, mock_update, sample_saga: Saga):
        """Test saving an existing saga (update)."""
        saga_id = save_saga(sample_saga)

        assert saga_id == sample_saga.saga_id
        mock_update.assert_called_once()

    @patch('src.infrastructure.repositories.saga_repository.execute_insert')
    def test_save_saga_with_none_id(self, mock_insert, sample_saga: Saga):
        """Test saving saga when insert returns None."""
        new_saga = Saga(
            saga_id=0,
            exec_id=sample_saga.exec_id,
            rpa_key_id=sample_saga.rpa_key_id,
            rpa_request_object=sample_saga.rpa_request_object,
            current_state=sample_saga.current_state,
            events=[],
            created_at=sample_saga.created_at,
            updated_at=sample_saga.updated_at
        )
        mock_insert.return_value = None

        saga_id = save_saga(new_saga)

        assert saga_id == 0


@pytest.mark.unit
class TestGetSaga:
    """Tests for get_saga function."""

    @patch('src.infrastructure.repositories.saga_repository.execute_query')
    def test_get_saga_success(self, mock_query, sample_saga: Saga):
        """Test getting an existing saga."""
        mock_query.return_value = [{
            "saga_id": sample_saga.saga_id,
            "exec_id": sample_saga.exec_id,
            "rpa_key_id": sample_saga.rpa_key_id,
            "rpa_request_object": '{"doc_transportes_list": []}',
            "current_state": sample_saga.current_state.value,
            "events": "[]",
            "created_at": sample_saga.created_at,
            "updated_at": sample_saga.updated_at
        }]

        result = get_saga(sample_saga.saga_id)

        assert result is not None
        assert result.saga_id == sample_saga.saga_id

    @patch('src.infrastructure.repositories.saga_repository.execute_query')
    def test_get_saga_not_found(self, mock_query):
        """Test getting non-existent saga."""
        mock_query.return_value = []

        result = get_saga(999)

        assert result is None


@pytest.mark.unit
class TestGetSagaByExecId:
    """Tests for get_saga_by_exec_id function."""

    @patch('src.infrastructure.repositories.saga_repository.execute_query')
    def test_get_saga_by_exec_id_success(self, mock_query, sample_saga: Saga):
        """Test getting saga by execution ID."""
        mock_query.return_value = [{
            "saga_id": sample_saga.saga_id,
            "exec_id": sample_saga.exec_id,
            "rpa_key_id": sample_saga.rpa_key_id,
            "rpa_request_object": '{"doc_transportes_list": []}',
            "current_state": sample_saga.current_state.value,
            "events": "[]",
            "created_at": sample_saga.created_at,
            "updated_at": sample_saga.updated_at
        }]

        result = get_saga_by_exec_id(sample_saga.exec_id)

        assert result is not None
        assert result.exec_id == sample_saga.exec_id

    @patch('src.infrastructure.repositories.saga_repository.execute_query')
    def test_get_saga_by_exec_id_not_found(self, mock_query):
        """Test getting saga when execution ID doesn't exist."""
        mock_query.return_value = []

        result = get_saga_by_exec_id(999)

        assert result is None
