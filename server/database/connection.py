"""
Database connection management for PocketBase.
"""

import os
from typing import Optional
from server.database.pocketbase_client import PocketBaseClient
from config.backend.logger import get_api_logger


class DatabaseConnection:
    """Manages database connections and provides access to data sources."""

    def __init__(self):
        self.logger = get_api_logger(__name__)
        self.pocketbase_client: Optional[PocketBaseClient] = None
        self._initialize_connections()

    def _initialize_connections(self):
        """Initialize database connections."""
        try:
            # Initialize PocketBase client
            self.pocketbase_client = PocketBaseClient()
            self.logger.info("Database connections initialized successfully")
        except Exception as e:
            self.logger.error(
                f"Failed to initialize database connections: {e}")
            raise

    def get_pocketbase_client(self) -> PocketBaseClient:
        """Get PocketBase client instance."""
        if not self.pocketbase_client:
            raise Exception("PocketBase client not initialized")
        return self.pocketbase_client

    def close_connections(self):
        """Close all database connections."""
        try:
            if self.pocketbase_client:
                # PocketBase client doesn't need explicit closing
                self.pocketbase_client = None
            self.logger.info("Database connections closed successfully")
        except Exception as e:
            self.logger.error(f"Error closing database connections: {e}")


# Global database connection instance
db_connection = DatabaseConnection()
