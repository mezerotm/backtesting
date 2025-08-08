"""
Authentication API endpoints.
"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Dict, Any
from server.services.auth_service import AuthService
from config.backend.logger import get_api_logger

router = APIRouter(prefix="/api/auth", tags=["auth"])
security = HTTPBearer()

# Initialize services and logger
auth_service = AuthService()
logger = get_api_logger("auth")


@router.post("/login")
async def login(credentials: Dict[str, str]) -> Dict[str, Any]:
    """Login with email and password."""
    email = credentials.get("email", "")
    logger.info(f"POST /login - Email: {email}")

    try:
        result = await auth_service.authenticate_user(email, credentials.get("password", ""))

        if not result.get("success"):
            error_msg = result.get("error", "Authentication failed")
            logger.error(
                f"POST /login failed - Email: {email}, Error: {error_msg}")
            raise HTTPException(status_code=401, detail=error_msg)

        logger.info(
            f"POST /login successful - Email: {email}, User ID: {
                result.get(
                    'data',
                    {}).get(
                    'user',
                    {}).get('id')}")
        return result["data"]
    except Exception as e:
        logger.error(
            f"POST /login exception - Email: {email}, Error: {str(e)}")
        raise


@router.post("/logout")
async def logout(credentials: HTTPAuthorizationCredentials = Depends(
        security)) -> Dict[str, Any]:
    """Logout the current user."""
    logger.info("POST /logout")

    try:
        result = await auth_service.logout_user(credentials.credentials)

        if not result.get("success"):
            error_msg = result.get("error", "Logout failed")
            logger.error(f"POST /logout failed - Error: {error_msg}")
            raise HTTPException(status_code=400, detail=error_msg)

        logger.info("POST /logout successful")
        return result["data"]
    except Exception as e:
        logger.error(f"POST /logout exception - Error: {str(e)}")
        raise


@router.get("/me")
async def get_current_user(
        credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """Get current user information."""
    logger.info("GET /me")

    try:
        result = await auth_service.get_current_user(credentials.credentials)

        if not result.get("success"):
            error_msg = result.get("error", "Failed to get current user")
            logger.error(f"GET /me failed - Error: {error_msg}")
            raise HTTPException(status_code=401, detail=error_msg)

        user_data = result.get("data", {}).get("user", {})
        if not user_data.get("id"):
            logger.error("GET /me failed - No user ID in response")
            raise HTTPException(status_code=401, detail="Invalid user data")

        logger.info(f"GET /me successful - User ID: {user_data.get('id')}")
        return user_data
    except Exception as e:
        logger.error(f"GET /me exception - Error: {str(e)}")
        raise


@router.post("/register")
async def register(user_data: Dict[str, str]) -> Dict[str, Any]:
    """Register a new user."""
    email = user_data.get("email", "")
    logger.info(f"POST /register - Email: {email}")

    try:
        result = await auth_service.register_user(
            email,
            user_data.get("password", ""),
            user_data.get("name", "")
        )

        if not result.get("success"):
            error_msg = result.get("error", "Registration failed")
            logger.error(
                f"POST /register failed - Email: {email}, Error: {error_msg}")
            raise HTTPException(status_code=400, detail=error_msg)

        user_id = result.get("data", {}).get("id")
        logger.info(
            f"POST /register successful - Email: {email}, User ID: {user_id}")
        return result["data"]
    except Exception as e:
        logger.error(
            f"POST /register exception - Email: {email}, Error: {str(e)}")
        raise


async def get_current_user_id(
        credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Get current user ID from token."""
    token = credentials.credentials
    result = await auth_service.get_current_user(token)

    if not result.get("success"):
        raise HTTPException(
            status_code=401, detail=result.get(
                "error", "Invalid token"))

    return result["data"]["user"]["id"]
