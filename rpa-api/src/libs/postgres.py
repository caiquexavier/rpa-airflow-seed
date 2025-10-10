"""Postgres client library for rpa-api."""
import json
import logging
from typing import Any, Dict, Optional

import psycopg2
from psycopg2.extras import RealDictCursor

from ..config.config import get_postgres_dsn

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
                return result[0] if result else None
    except Exception as e:
        logger.error(f"Failed to execute insert: {e}")
        raise Exception(f"Database insert failed: {str(e)}")
