"""
User repository for database operations.
"""

from typing import Optional, List
from datetime import datetime
from server.database.models.user import User, UserCreate, UserUpdate
from server.database.connection import db_connection
from config.backend.logger import get_api_logger


class UserRepository:
    """Repository for user-related database operations."""

    def __init__(self):
        self.logger = get_api_logger(__name__)
        self.pb_client = db_connection.get_pocketbase_client()

    async def create_user(self, user_data: UserCreate) -> Optional[User]:
        """Create a new user."""
        try:
            # Hash password before storing
            hashed_password = await self._hash_password(user_data.password)

            data = {
                "email": user_data.email,
                "name": user_data.name,
                "password": hashed_password,
                "created_at": datetime.now().isoformat()
            }

            result = await self.pb_client.create_user(data)
            return User(**result) if result else None
        except Exception as e:
            self.logger.error(f"Error creating user: {e}")
            return None

    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        try:
            result = await self.pb_client.get_user_by_id(user_id)
            return User(**result) if result else None
        except Exception as e:
            self.logger.error(f"Error getting user by ID: {e}")
            return None

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        try:
            result = await self.pb_client.get_user_by_email(email)
            return User(**result) if result else None
        except Exception as e:
            self.logger.error(f"Error getting user by email: {e}")
            return None

    async def update_user(
            self,
            user_id: str,
            user_data: UserUpdate) -> Optional[User]:
        """Update user data."""
        try:
            update_data = user_data.dict(exclude_unset=True)
            if update_data:
                update_data["updated_at"] = datetime.now().isoformat()
                result = await self.pb_client.update_user(user_id, update_data)
                return User(**result) if result else None
            return None
        except Exception as e:
            self.logger.error(f"Error updating user: {e}")
            return None

    async def delete_user(self, user_id: str) -> bool:
        """Delete a user."""
        try:
            await self.pb_client.delete_user(user_id)
            return True
        except Exception as e:
            self.logger.error(f"Error deleting user: {e}")
            return False

    async def list_users(
            self,
            limit: int = 100,
            offset: int = 0) -> List[User]:
        """List all users with pagination."""
        try:
            results = await self.pb_client.list_users(limit=limit, offset=offset)
            return [User(**user) for user in results] if results else []
        except Exception as e:
            self.logger.error(f"Error listing users: {e}")
            return []

    async def _hash_password(self, password: str) -> str:
        """Hash a password."""
        # TODO: Implement proper password hashing with bcrypt
        # For now, return as-is (NOT for production)
        return password

    async def _verify_password(
            self,
            password: str,
            hashed_password: str) -> bool:
        """Verify a password against its hash."""
        # TODO: Implement proper password verification with bcrypt
        # For now, simple comparison (NOT for production)
        return password == hashed_password
