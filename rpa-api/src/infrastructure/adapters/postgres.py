"""Postgres client library for rpa-api."""
import json
import logging
from typing import Any, Dict, Optional

import psycopg2
from psycopg2.extras import RealDictCursor

from ...config.config import get_postgres_dsn

logger = logging.getLogger(__name__)


def get_connection():
    """Get a Postgres connection."""
    dsn = get_postgres_dsn()
    return psycopg2.connect(dsn)


def execute_insert(sql: str, params: tuple) -> Optional[int]:
    """
    Execute an INSERT statement and return the generated ID.
    
    Args:
        sql: SQL INSERT statement
        params: Parameters for the SQL statement
        
    Returns:
        Generated ID if RETURNING clause is used, None otherwise
    """
    try:
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(sql, params)
                result = cursor.fetchone()
                conn.commit()
                if not result:
                    return None
                # RealDictCursor returns a mapping; prefer explicit key then fallback to first value
                if isinstance(result, dict):
                    return result.get("exec_id") or next(iter(result.values()))
                # Fallback for non-dict row types (tuple-like)
                try:
                    return result[0]
                except Exception:
                    return None
    except Exception as e:
        logger.error(f"Failed to execute insert: {e}")
        raise Exception(f"Database insert failed: {str(e)}")


def execute_query(sql: str, params: tuple) -> list:
    """
    Execute a SELECT statement and return results.
    
    Args:
        sql: SQL SELECT statement
        params: Parameters for the SQL statement
        
    Returns:
        List of query results
    """
    try:
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(sql, params)
                return cursor.fetchall()
    except Exception as e:
        logger.error(f"Failed to execute query: {e}")
        raise Exception(f"Database query failed: {str(e)}")


def execute_update(sql: str, params: tuple) -> int:
    """
    Execute an UPDATE/DELETE statement and return affected rows.
    
    Args:
        sql: SQL UPDATE/DELETE statement
        params: Parameters for the SQL statement
        
    Returns:
        Number of affected rows
    """
    try:
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(sql, params)
                conn.commit()
                return cursor.rowcount
    except Exception as e:
        logger.error(f"Failed to execute update: {e}")
        raise Exception(f"Database update failed: {str(e)}")

