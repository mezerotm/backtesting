from fastapi import APIRouter

# This module is for central dashboard logic (e.g., health checks, app config, user info, etc).
# Do NOT put report or portfolio endpoints here. See api_report.py and portfolio_api.py for those.
# Intended for endpoints like: /api/dashboard/health, /api/dashboard/config, etc.

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

@router.get("/health")
def health_check():
    """Health check endpoint for the dashboard API."""
    return {"status": "ok"} 