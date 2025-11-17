"""Unit tests for postgres adapter."""
import sys
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# Mock the config module before importing postgres
# The postgres module uses: from ...config.config import get_postgres_dsn
# We need to ensure the rpa-api config is used, not rpa-listener's
project_root = Path(__file__).parent.parent.parent.parent
config_path = project_root / "rpa-api" / "src" / "config" / "config.py"

# Create a mock config module
mock_config = MagicMock()
mock_config.get_postgres_dsn = Mock(return_value="postgresql://test:test@localhost:5432/testdb")
sys.modules['src.config.config'] = mock_config

# Now import postgres - it will use our mocked config
from src.infrastructure.adapters.postgres import (
    get_connection, execute_insert, execute_query, execute_update
)


@pytest.mark.unit
class TestGetConnection:
    """Tests for get_connection function."""

    @patch('src.infrastructure.adapters.postgres.psycopg2.connect')
    def test_get_connection_success(self, mock_connect):
        """Test successful connection creation."""
        mock_conn = Mock()
        mock_connect.return_value = mock_conn

        result = get_connection()

        assert result == mock_conn
        mock_connect.assert_called_once()

    def test_get_connection_calls_get_postgres_dsn(self):
        """Test that get_connection calls get_postgres_dsn."""
        with patch('src.infrastructure.adapters.postgres.psycopg2.connect') as mock_connect:
            get_connection()
            # Verify get_postgres_dsn was called (via the mock)
            mock_config.get_postgres_dsn.assert_called()


@pytest.mark.unit
class TestExecuteInsert:
    """Tests for execute_insert function."""

    @patch('src.infrastructure.adapters.postgres.get_connection')
    def test_execute_insert_success_with_dict_result(self, mock_get_conn):
        """Test successful insert with dict result."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {"exec_id": 1}
        mock_conn = MagicMock()
        mock_conn.__enter__ = Mock(return_value=mock_conn)
        mock_conn.__exit__ = Mock(return_value=None)
        mock_conn.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = Mock(return_value=None)
        mock_get_conn.return_value = mock_conn

        result = execute_insert("INSERT INTO test VALUES (%s) RETURNING exec_id", ("value",))

        assert result == 1
        mock_cursor.execute.assert_called_once()
        mock_conn.commit.assert_called_once()

    @patch('src.infrastructure.adapters.postgres.get_connection')
    def test_execute_insert_success_with_tuple_result(self, mock_get_conn):
        """Test successful insert with tuple result."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (1,)
        mock_conn = MagicMock()
        mock_conn.__enter__ = Mock(return_value=mock_conn)
        mock_conn.__exit__ = Mock(return_value=None)
        mock_conn.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = Mock(return_value=None)
        mock_get_conn.return_value = mock_conn

        result = execute_insert("INSERT INTO test VALUES (%s) RETURNING exec_id", ("value",))

        assert result == 1

    @patch('src.infrastructure.adapters.postgres.get_connection')
    def test_execute_insert_no_result(self, mock_get_conn):
        """Test insert with no result."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_conn = MagicMock()
        mock_conn.__enter__ = Mock(return_value=mock_conn)
        mock_conn.__exit__ = Mock(return_value=None)
        mock_conn.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = Mock(return_value=None)
        mock_get_conn.return_value = mock_conn

        result = execute_insert("INSERT INTO test VALUES (%s)", ("value",))

        assert result is None

    @patch('src.infrastructure.adapters.postgres.get_connection')
    def test_execute_insert_exception(self, mock_get_conn):
        """Test insert with exception."""
        mock_get_conn.side_effect = Exception("Connection failed")

        with pytest.raises(Exception, match="Database insert failed"):
            execute_insert("INSERT INTO test VALUES (%s)", ("value",))


@pytest.mark.unit
class TestExecuteQuery:
    """Tests for execute_query function."""

    @patch('src.infrastructure.adapters.postgres.get_connection')
    def test_execute_query_success(self, mock_get_conn):
        """Test successful query execution."""
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [{"id": 1, "name": "test"}]
        mock_conn = MagicMock()
        mock_conn.__enter__ = Mock(return_value=mock_conn)
        mock_conn.__exit__ = Mock(return_value=None)
        mock_conn.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = Mock(return_value=None)
        mock_get_conn.return_value = mock_conn

        result = execute_query("SELECT * FROM test WHERE id = %s", (1,))

        assert len(result) == 1
        assert result[0]["id"] == 1
        mock_cursor.execute.assert_called_once()

    @patch('src.infrastructure.adapters.postgres.get_connection')
    def test_execute_query_exception(self, mock_get_conn):
        """Test query with exception."""
        mock_get_conn.side_effect = Exception("Connection failed")

        with pytest.raises(Exception, match="Database query failed"):
            execute_query("SELECT * FROM test", ())


@pytest.mark.unit
class TestExecuteUpdate:
    """Tests for execute_update function."""

    @patch('src.infrastructure.adapters.postgres.get_connection')
    def test_execute_update_success(self, mock_get_conn):
        """Test successful update execution."""
        mock_cursor = MagicMock()
        mock_cursor.rowcount = 1
        mock_conn = MagicMock()
        mock_conn.__enter__ = Mock(return_value=mock_conn)
        mock_conn.__exit__ = Mock(return_value=None)
        mock_conn.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = Mock(return_value=None)
        mock_get_conn.return_value = mock_conn

        result = execute_update("UPDATE test SET name = %s WHERE id = %s", ("new_name", 1))

        assert result == 1
        mock_cursor.execute.assert_called_once()
        mock_conn.commit.assert_called_once()

    @patch('src.infrastructure.adapters.postgres.get_connection')
    def test_execute_update_exception(self, mock_get_conn):
        """Test update with exception."""
        mock_get_conn.side_effect = Exception("Connection failed")

        with pytest.raises(Exception, match="Database update failed"):
            execute_update("UPDATE test SET name = %s", ("value",))
