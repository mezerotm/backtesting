"""
Authentication API endpoints for user login, registration, and session management.
"""

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, EmailStr
from typing import Dict, Any, Optional
import requests

from utils.pocketbase_client import PocketBaseClient
from utils.logger import get_api_logger

logger = get_api_logger("auth")

router = APIRouter(prefix="/api/auth", tags=["auth"])

# PocketBase client instance
pb_client = PocketBaseClient()

# In-memory session storage (for development)
_sessions = {}

# Pydantic models for request/response


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    passwordConfirm: str
    name: str


class LogoutRequest(BaseModel):
    token: str


class AuthResponse(BaseModel):
    success: bool
    message: str
    user: Optional[Dict[str, Any]] = None


# Session storage (in production, use Redis or database)
_sessions = {}
_session_counter = 0


def get_pocketbase_client() -> PocketBaseClient:
    """Get a new PocketBase client instance for each request."""
    return PocketBaseClient()


def get_shared_pocketbase_client() -> PocketBaseClient:
    """Get the shared PocketBase client from ModelManager."""
    from server.models.model_manager import get_model_manager
    model_manager = get_model_manager()
    return model_manager.pb_client

# =============================================================================
# INTERNAL AI DEBUGGING SECTION
# =============================================================================
# This section contains authentication dependencies and debugging utilities
# for internal AI use. These functions help diagnose authentication issues
# and provide detailed logging for troubleshooting.


async def get_current_user(request: Request) -> Optional[Dict[str, Any]]:
    """Get current user from session or token."""
    auth_token = request.cookies.get("pb_auth_token")
    if not auth_token:
        logger.debug("=== AI DEBUG: No auth token found ===")
        return None

    # Check if we have a cached session
    if auth_token in _sessions:
        logger.debug("=== AI DEBUG: Found cached session ===")
        return _sessions[auth_token]

    # Try to validate the token using direct REST API call
    try:
        logger.debug("=== AI DEBUG: Attempting to validate token ===")
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(
            f"{pb_client.base_url}/api/users/auth-refresh", headers=headers, timeout=5)
        if response.status_code == 200:
            user_record = response.json().get("record", {})
            logger.debug("=== AI DEBUG: Token validation successful ===")
            user_info = {
                "user_id": user_record.get("id"),
                "email": user_record.get("email"),
                "name": user_record.get("name", user_record.get("email"))
            }
            _sessions[auth_token] = user_info
            logger.debug("=== AI DEBUG: Stored session in memory ===")
            return user_info
        else:
            logger.debug(
                f"=== AI DEBUG: Token validation failed: {
                    response.status_code} ===")
            return None
    except Exception as e:
        logger.warning(f"=== AI DEBUG: Error validating token: {e} ===")
        return None


async def require_auth(request: Request) -> Dict[str, Any]:
    """Require authentication - raises HTTPException if not authenticated."""
    logger.debug("=== AI DEBUG: require_auth called ===")
    user = await get_current_user(request)
    if not user:
        logger.debug(
            "=== AI DEBUG: Authentication required but not provided ===")
        raise HTTPException(status_code=401, detail="Authentication required")
    logger.debug(
        f"=== AI DEBUG: Authentication successful for user: {user} ===")
    return user


async def get_current_user_id(request: Request) -> Optional[str]:
    """Get the current authenticated user ID from request context with AI debugging."""
    try:
        logger.debug("=== AI DEBUG: get_current_user_id called ===")
        user = await get_current_user(request)
        user_id = user["user_id"] if user else None
        logger.debug(f"=== AI DEBUG: Extracted user ID: {user_id} ===")
        return user_id
    except Exception as e:
        logger.error(f"=== AI DEBUG: Error getting current user ID: {e} ===")
        return None

# =============================================================================
# END INTERNAL AI DEBUGGING SECTION
# =============================================================================


@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest, response: Response):
    """Authenticate user with email and password."""
    try:
        logger.info(f"Login attempt for email: {request.email}")

        # Get shared PocketBase client
        pb_client = get_shared_pocketbase_client()

        # Check if PocketBase server is running
        if not pb_client.is_server_running():
            raise HTTPException(
                status_code=503,
                detail="Database server is not running. Please run 'make db-start' to start the database.")

        try:
            # Try to authenticate with PocketBase
            auth_result = pb_client.authenticate_user(
                request.email, request.password)

            if auth_result and auth_result.get('token'):
                # Store session in memory
                token = auth_result['token']
                user_info = {
                    "user_id": auth_result.get('user_id'),
                    "email": request.email,
                    "name": auth_result.get(
                        'name',
                        auth_result.get(
                            'username',
                            request.email))}
                _sessions[token] = user_info

                # Set the auth cookie
                response.set_cookie(
                    key="pb_auth_token",
                    value=token,
                    httponly=True,
                    secure=False,  # Set to True in production with HTTPS
                    samesite="lax",
                    max_age=3600 * 24 * 7  # 7 days
                )

                logger.info(f"User {request.email} logged in successfully")

                return AuthResponse(
                    success=True,
                    message="Login successful",
                    user=user_info
                )
            else:
                logger.warning(f"Login failed for {request.email}")
                raise HTTPException(
                    status_code=401, detail="Invalid credentials")

        except Exception as e:
            logger.error(f"Login error for {request.email}: {e}")
            raise HTTPException(status_code=500, detail="Login failed")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during login: {e}")
        raise HTTPException(status_code=500,
                            detail="Internal server error during login")


@router.post("/register", response_model=AuthResponse)
async def register(request: RegisterRequest, response: Response):
    """Register a new user account."""
    try:
        logger.info(f"Registration attempt for email: {request.email}")

        # Validate password confirmation
        if request.password != request.passwordConfirm:
            raise HTTPException(
                status_code=400,
                detail="Passwords do not match")

        # Get shared PocketBase client
        pb_client = get_shared_pocketbase_client()

        # Check if PocketBase server is running
        if not pb_client.is_server_running():
            raise HTTPException(
                status_code=503,
                detail="Database server is not running. Please run 'make db-start' to start the database.")

        try:
            # Try to register with PocketBase
            register_result = pb_client.register_user(
                request.email, request.password, request.name)

            if register_result and register_result.get('user_id'):
                logger.info(f"User {request.email} registered successfully")

                # Auto-login after registration
                auth_result = pb_client.authenticate_user(
                    request.email, request.password)
                if auth_result and auth_result.get('token'):
                    token = auth_result['token']
                    user_info = {
                        "user_id": register_result['user_id'],
                        "email": request.email,
                        "name": register_result.get('name', request.name)
                    }
                    _sessions[token] = user_info

                    # Set the auth cookie
                    response.set_cookie(
                        key="pb_auth_token",
                        value=token,
                        httponly=True,
                        secure=False,  # Set to True in production with HTTPS
                        samesite="lax",
                        max_age=3600 * 24 * 7  # 7 days
                    )

                return AuthResponse(
                    success=True,
                    message="Registration successful",
                    user={
                        "user_id": register_result['user_id'],
                        "email": request.email,
                        "name": register_result.get('name', request.name)})
            else:
                logger.warning(f"Registration failed for {request.email}")
                raise HTTPException(
                    status_code=400, detail="Registration failed")

        except Exception as e:
            logger.error(f"Registration error for {request.email}: {e}")
            raise HTTPException(status_code=500, detail="Registration failed")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during registration: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error during registration")


@router.post("/logout", response_model=AuthResponse)
async def logout(response: Response):
    """Logout the current user."""
    try:
        logger.info("User logout request")

        # Clear the auth cookie
        response.delete_cookie(key="pb_auth_token")

        # Clear session storage
        _sessions.clear()

        logger.info("User logged out successfully")

        return AuthResponse(
            success=True,
            message="Logout successful",
            user=None
        )

    except Exception as e:
        logger.error(f"Error during logout: {e}")
        raise HTTPException(status_code=500,
                            detail="Internal server error during logout")


@router.get("/me")
async def get_current_user_endpoint(request: Request):
    """Get current user information."""
    try:
        # Get auth token from cookie
        auth_token = request.cookies.get("pb_auth_token")

        if not auth_token:
            raise HTTPException(status_code=401, detail="Not authenticated")

        # First check if we have this session in memory
        if auth_token in _sessions:
            user_data = _sessions[auth_token]
            logger.info(f"Found user session in memory: {user_data['email']}")
            return {
                "success": True,
                "message": "User authenticated",
                "user": user_data
            }

        # If not in memory, try to validate with PocketBase using REST API
        try:
            # Get shared PocketBase client
            pb_client = get_shared_pocketbase_client()

            # Check if PocketBase server is running
            if not pb_client.is_server_running():
                raise HTTPException(
                    status_code=503,
                    detail="Database server is not running. Please run 'make db-start' to start the database.")

            # Validate token using REST API
            headers = {"Authorization": f"Bearer {auth_token}"}
            response = requests.get(
                f"{pb_client.base_url}/api/users/auth-refresh",
                headers=headers,
                timeout=5
            )

            if response.status_code == 200:
                user_record = response.json().get("record", {})
                user_info = {
                    "user_id": user_record.get("id"),
                    "email": user_record.get("email"),
                    "name": user_record.get(
                        "name",
                        user_record.get(
                            "username",
                            user_record.get("email")))}

                # Store in memory for future requests
                _sessions[auth_token] = user_info

                return {
                    "success": True,
                    "message": "User authenticated",
                    "user": user_info
                }
            else:
                logger.warning(
                    f"Token validation failed: {
                        response.status_code}")
                raise HTTPException(
                    status_code=401,
                    detail="Invalid or expired session")

        except Exception as e:
            logger.warning(f"Error validating token: {e}")
            raise HTTPException(
                status_code=401,
                detail="Invalid or expired session")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting current user: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
