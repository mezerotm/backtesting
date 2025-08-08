"""
Authentication service for managing user authentication and authorization.
"""

from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import jwt
from .base_service import BaseService


class AuthService(BaseService):
    """Service for authentication operations."""

    def __init__(self):
        super().__init__()
        self.secret_key = "your-secret-key"  # Should come from config
        self.algorithm = "HS256"
        self.access_token_expire_minutes = 1440  # 24 hours instead of 30 minutes

    async def authenticate_user(
            self, email: str, password: str) -> Dict[str, Any]:
        """Authenticate a user with email and password."""
        try:
            self.log_operation("authenticate_user", {"email": email})

            # Validate required fields
            if not self.validate_required_fields(
                    {"email": email, "password": password}, ["email", "password"]):
                return self.handle_error(
                    Exception("Email and password are required"),
                    "authenticate_user")

            # Use PocketBase's built-in user authentication
            auth_result = self.pb_client.authenticate_user(email, password)
            if not auth_result:
                return self.handle_error(
                    Exception("Invalid credentials"),
                    "authenticate_user")

            # Generate access token
            access_token = self._create_access_token(
                data={"sub": auth_result["user_id"]})

            return {
                "success": True,
                "data": {
                    "access_token": access_token,
                    "token_type": "bearer",
                    "user": {
                        "id": auth_result["user_id"],
                        "email": email,
                        "name": auth_result.get("name", "")
                    }
                }
            }
        except Exception as e:
            return self.handle_error(e, "authenticate_user")

    async def register_user(
            self, email: str, password: str, name: str) -> Dict[str, Any]:
        """Register a new user."""
        try:
            self.log_operation("register_user", {"email": email, "name": name})

            # Validate required fields
            if not self.validate_required_fields(
                    {"email": email, "password": password, "name": name}, ["email", "password", "name"]):
                return self.handle_error(
                    Exception("Email, password, and name are required"),
                    "register_user")

            # Check if user already exists
            existing_user = await self._get_user_by_email(email)
            if existing_user:
                return self.handle_error(
                    Exception("User already exists"), "register_user")

            # Use the existing PocketBaseClient register_user method
            user = self.pb_client.register_user(email, password, name)
            if not user:
                return self.handle_error(
                    Exception("Failed to create user"), "register_user")

            return {
                "success": True,
                "data": {
                    "user": {
                        "id": user["id"],
                        "email": user["email"],
                        "name": user["name"]
                    },
                    "message": "User registered successfully"
                }
            }
        except Exception as e:
            return self.handle_error(e, "register_user")

    async def get_current_user(self, token: str) -> Dict[str, Any]:
        """Get current user from token."""
        try:
            self.log_operation("get_current_user")

            if not token:
                return self.handle_error(
                    Exception("Token is required"), "get_current_user")

            # Decode token
            payload = jwt.decode(
                token, self.secret_key, algorithms=[
                    self.algorithm])
            user_id = payload.get("sub")

            if not user_id:
                return self.handle_error(
                    Exception("Invalid token"), "get_current_user")

            # Get user from database
            user = await self._get_user_by_id(user_id)
            if not user:
                return self.handle_error(
                    Exception("User not found"), "get_current_user")

            return {
                "success": True,
                "data": {
                    "user": {
                        "id": user["id"],
                        "email": user["email"],
                        "name": user.get("name", "")
                    }
                }
            }
        except jwt.ExpiredSignatureError:
            return self.handle_error(
                Exception("Token has expired"),
                "get_current_user")
        except jwt.JWTError:
            return self.handle_error(
                Exception("Invalid token"),
                "get_current_user")
        except Exception as e:
            return self.handle_error(e, "get_current_user")

    async def logout_user(self, token: str) -> Dict[str, Any]:
        """Log out a user by invalidating their token."""
        try:
            self.log_operation("logout_user")

            # In a real implementation, you might want to:
            # 1. Add the token to a blacklist
            # 2. Clear any server-side sessions
            # 3. Revoke refresh tokens

            # For now, we'll just return success since token invalidation
            # will be handled on the client side
            return {
                "success": True,
                "data": {
                    "message": "Successfully logged out"
                }
            }
        except Exception as e:
            return self.handle_error(e, "logout_user")

    def _create_access_token(self, data: Dict[str, Any]) -> str:
        """Create a JWT access token."""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(
            to_encode,
            self.secret_key,
            algorithm=self.algorithm)
        return encoded_jwt

    async def _get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email."""
        try:
            # Ensure we're authenticated as admin
            if not self.pb_client.authenticate():
                self.logger.error("Failed to authenticate as admin")
                return None

            # Get user directly from the users collection
            users = self.pb_client.get_records("users", f"email='{email}'")
            if users:
                user = users[0]
                return {
                    "id": user.get("id"),
                    "email": user.get("email"),
                    "name": user.get("name", ""),
                    "password": user.get("password", "")
                }
            return None
        except Exception as e:
            self.logger.error(f"Error getting user by email: {e}")
            return None

    async def _get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID."""
        try:
            # Ensure we're authenticated as admin
            if not self.pb_client.authenticate():
                self.logger.error("Failed to authenticate as admin")
                return None

            # Get user directly from the users collection
            users = self.pb_client.get_records("users", f"id='{user_id}'")
            if users:
                user = users[0]
                return {
                    "id": user.get("id"),
                    "email": user.get("email"),
                    "name": user.get("name", ""),
                    "password": user.get("password", "")
                }
            return None
        except Exception as e:
            self.logger.error(f"Error getting user by ID: {e}")
            return None

    async def _hash_password(self, password: str) -> str:
        """Hash a password."""
        # Implement password hashing (e.g., with bcrypt)
        # For now, return as-is (NOT for production)
        return password

    async def _verify_password(
            self,
            password: str,
            hashed_password: str) -> bool:
        """Verify a password against its hash."""
        # Implement password verification (e.g., with bcrypt)
        # For now, simple comparison (NOT for production)
        return password == hashed_password
