"""
Database connection and query utilities for the String Authority Database Search API.
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import SimpleConnectionPool
from contextlib import contextmanager
from typing import Dict, List, Optional, Any, Generator
import logging

from .config import get_database_config

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Manages database connections and provides query utilities."""
    
    def __init__(self):
        self._pool: Optional[SimpleConnectionPool] = None
        self._initialize_pool()
    
    def _initialize_pool(self):
        """Initialize the connection pool."""
        config = get_database_config()
        if not config:
            raise ValueError("Database configuration not found")
        
        try:
            self._pool = SimpleConnectionPool(
                minconn=1,
                maxconn=10,
                **config
            )
            logger.info("Database connection pool initialized")
        except Exception as e:
            logger.error(f"Failed to initialize database pool: {e}")
            raise
    
    @contextmanager
    def get_connection(self) -> Generator[psycopg2.extensions.connection, None, None]:
        """
        Context manager for getting a database connection from the pool.
        
        Yields:
            Database connection
        """
        if not self._pool:
            raise RuntimeError("Database pool not initialized")
        
        conn = None
        try:
            conn = self._pool.getconn()
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            if conn:
                self._pool.putconn(conn)
    
    def execute_query(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """
        Execute a SELECT query and return results as a list of dictionaries.
        
        Args:
            query: SQL query string
            params: Query parameters
            
        Returns:
            List of query results as dictionaries
        """
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, params)
                return [dict(row) for row in cursor.fetchall()]
    
    def execute_count_query(self, query: str, params: Optional[tuple] = None) -> int:
        """
        Execute a COUNT query and return the count as an integer.
        
        Args:
            query: SQL COUNT query string
            params: Query parameters
            
        Returns:
            Count result as integer
        """
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, params)
                result = cursor.fetchone()
                return result[0] if result else 0
    
    def close_pool(self):
        """Close the connection pool."""
        if self._pool:
            self._pool.closeall()
            self._pool = None
            logger.info("Database connection pool closed")

# Global database manager instance
db_manager = DatabaseManager()

def get_db_manager() -> DatabaseManager:
    """Get the global database manager instance."""
    return db_manager