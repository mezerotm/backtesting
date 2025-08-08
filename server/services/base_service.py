"""
Base service class providing common functionality for all services.
"""

from typing import Optional, Dict, Any
from config.backend.logger import get_api_logger
from server.database.connection import db_connection


class BaseService:
    """Base service class with common functionality."""

    def __init__(self):
        self.logger = get_api_logger(__name__)
        self.pb_client = db_connection.get_pocketbase_client()

    def handle_error(self, error: Exception,
                     context: str = "") -> Dict[str, Any]:
        """Standard error handling for services."""
        self.logger.error(f"Service error in {context}: {str(error)}")
        return {
            "success": False,
            "error": str(error),
            "context": context
        }

    def log_operation(self, operation: str,
                      details: Optional[Dict[str, Any]] = None):
        """Standard logging for service operations."""
        if details:
            self.logger.info(f"Service operation: {operation} - {details}")
        else:
            self.logger.info(f"Service operation: {operation}")

    def validate_required_fields(
            self, data: Dict[str, Any], required_fields: list) -> bool:
        """Validate that required fields are present in data."""
        missing_fields = [
            field for field in required_fields if field not in data or data[field] is None]
        if missing_fields:
            self.logger.warning(f"Missing required fields: {missing_fields}")
            return False
        return True
