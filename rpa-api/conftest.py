"""Pytest configuration and fixtures."""
import pytest
import asyncio
from unittest.mock import MagicMock


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_db_connection():
    """Mock database connection for tests."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_conn.__enter__.return_value = mock_conn
    return mock_conn, mock_cursor


@pytest.fixture
def mock_rabbitmq_connection():
    """Mock RabbitMQ connection for tests."""
    mock_conn = MagicMock()
    mock_channel = MagicMock()
    mock_conn.channel.return_value = mock_channel
    return mock_conn, mock_channel


@pytest.fixture
def sample_execution_payload():
    """Sample execution payload for tests."""
    return {
        "rpa_key_id": "job-001",
        "callback_url": "http://localhost:3000/callback",
        "rpa_request": {"nota_fiscal": "12345"}
    }


@pytest.fixture
def sample_execution_record():
    """Sample execution record for tests."""
    return {
        "exec_id": 123,
        "rpa_key_id": "job-001",
        "exec_status": "PENDING",
        "rpa_request": {"nota_fiscal": "12345"},
        "rpa_response": None,
        "callback_url": "http://localhost:3000/callback",
        "created_at": "2023-01-01T00:00:00Z",
        "updated_at": "2023-01-01T00:00:00Z",
        "finished_at": None,
        "error_message": None
    }
