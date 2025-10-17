"""Unit tests for postgres module."""
import pytest
from unittest.mock import patch, MagicMock, call

from src.libs.postgres import get_connection, execute_insert


class TestGetConnection:
    """Test get_connection function."""
    
    @patch('src.libs.postgres.psycopg2.connect')
    @patch('src.libs.postgres.get_postgres_dsn')
    def test_get_connection_success(self, mock_get_dsn, mock_connect):
        """Test successful connection."""
        # Setup
        mock_dsn = "postgresql://user:pass@host:5432/db"
        mock_get_dsn.return_value = mock_dsn
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        
        # Execute
        result = get_connection()
        
        # Verify
        assert result == mock_conn
        mock_get_dsn.assert_called_once()
        mock_connect.assert_called_once_with(mock_dsn)
    
    @patch('src.libs.postgres.psycopg2.connect')
    @patch('src.libs.postgres.get_postgres_dsn')
    def test_get_connection_failure(self, mock_get_dsn, mock_connect):
        """Test connection failure."""
        # Setup
        mock_get_dsn.return_value = "postgresql://user:pass@host:5432/db"
        mock_connect.side_effect = Exception("Connection failed")
        
        # Execute & Verify
        with pytest.raises(Exception) as exc_info:
            get_connection()
        
        assert "Connection failed" in str(exc_info.value)


class TestExecuteInsert:
    """Test execute_insert function."""
    
    @patch('src.libs.postgres.get_connection')
    def test_execute_insert_success(self, mock_get_connection):
        """Test successful insert with RETURNING clause."""
        # Setup
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_conn.__enter__.return_value = mock_conn
        mock_get_connection.return_value = mock_conn
        
        mock_cursor.fetchone.return_value = [123]
        
        sql = "INSERT INTO test (name) VALUES (%s) RETURNING id"
        params = ("test_name",)
        
        # Execute
        result = execute_insert(sql, params)
        
        # Verify
        assert result == 123
        mock_cursor.execute.assert_called_once_with(sql, params)
        mock_cursor.fetchone.assert_called_once()
        mock_conn.commit.assert_called_once()
    
    @patch('src.libs.postgres.get_connection')
    def test_execute_insert_no_returning(self, mock_get_connection):
        """Test insert without RETURNING clause."""
        # Setup
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_conn.__enter__.return_value = mock_conn
        mock_get_connection.return_value = mock_conn
        
        mock_cursor.fetchone.return_value = None
        
        sql = "INSERT INTO test (name) VALUES (%s)"
        params = ("test_name",)
        
        # Execute
        result = execute_insert(sql, params)
        
        # Verify
        assert result is None
        mock_cursor.execute.assert_called_once_with(sql, params)
        mock_cursor.fetchone.assert_called_once()
        mock_conn.commit.assert_called_once()
    
    @patch('src.libs.postgres.get_connection')
    def test_execute_insert_database_error(self, mock_get_connection):
        """Test insert with database error."""
        # Setup
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_conn.__enter__.return_value = mock_conn
        mock_get_connection.return_value = mock_conn
        
        mock_cursor.execute.side_effect = Exception("Database error")
        
        sql = "INSERT INTO test (name) VALUES (%s)"
        params = ("test_name",)
        
        # Execute & Verify
        with pytest.raises(Exception) as exc_info:
            execute_insert(sql, params)
        
        assert "Database insert failed" in str(exc_info.value)
        assert "Database error" in str(exc_info.value)
    
    @patch('src.libs.postgres.get_connection')
    def test_execute_insert_connection_error(self, mock_get_connection):
        """Test insert with connection error."""
        # Setup
        mock_get_connection.side_effect = Exception("Connection failed")
        
        sql = "INSERT INTO test (name) VALUES (%s)"
        params = ("test_name",)
        
        # Execute & Verify
        with pytest.raises(Exception) as exc_info:
            execute_insert(sql, params)
        
        assert "Database insert failed" in str(exc_info.value)
        assert "Connection failed" in str(exc_info.value)
