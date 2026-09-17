from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any, List
from config.backend.logger import get_api_logger
from server.api.auth import get_current_user_id
import json
from datetime import datetime

router = APIRouter(prefix="/api/logs", tags=["logs"])

# Initialize logger
logger = get_api_logger("logs")


@router.post("/frontend")
async def receive_frontend_logs(
    logs_data: Dict[str, Any],
    user_id: str = Depends(get_current_user_id)
) -> Dict[str, Any]:
    """Receive and store frontend logs for debugging."""
    try:
        logger.info(
            f"POST /frontend - User: {user_id}, Session: {logs_data.get('sessionId')}")

        # Extract log data
        session_id = logs_data.get('sessionId', 'unknown')
        frontend_user_id = logs_data.get('userId', 'unknown')
        timestamp = logs_data.get('timestamp', datetime.now().isoformat())
        logs = logs_data.get('logs', [])

        # Log each frontend log entry
        for log_entry in logs:
            level = log_entry.get('level', 1)  # Default to INFO
            category = log_entry.get('category', 'unknown')
            message = log_entry.get('message', '')
            data = log_entry.get('data')

            # Map frontend log levels to backend levels
            if level == 0:  # DEBUG
                logger.debug(f"Frontend [{category}] {message}", data)
            elif level == 1:  # INFO
                logger.info(f"Frontend [{category}] {message}", data)
            elif level == 2:  # WARN
                logger.warning(f"Frontend [{category}] {message}", data)
            elif level == 3:  # ERROR
                logger.error(f"Frontend [{category}] {message}", data)
            else:
                logger.info(f"Frontend [{category}] {message}", data)

        logger.info(
            f"POST /frontend successful - User: {user_id}, Logs: {len(logs)}")
        return {
            "success": True,
            "message": f"Received {len(logs)} log entries",
            "session_id": session_id,
            "timestamp": timestamp
        }
    except Exception as e:
        logger.error(
            f"POST /frontend exception - User: {user_id}, Error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process logs:  str(e)")


@router.get("/stats")
async def get_log_stats(user_id: str = Depends(
        get_current_user_id)) -> Dict[str, Any]:
    """Get log statistics for the current user."""
    try:
        logger.info(f"GET /stats - User: {user_id}")

        # This would typically query the database for user-specific log stats
        # For now, return basic stats
        stats = {
            "user_id": user_id,
            "total_logs": 0,
            "error_count": 0,
            "warning_count": 0,
            "info_count": 0,
            "debug_count": 0,
            "last_log": None
        }

        logger.info(f"GET /stats successful - User: {user_id}")
        return stats
    except Exception as e:
        logger.error(
            f"GET /stats exception - User: {user_id}, Error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get log stats:  str(e)")


@router.get("/recent")
async def get_recent_logs(
    limit: int = 100,
    user_id: str = Depends(get_current_user_id)
) -> Dict[str, Any]:
    """Get recent logs for the current user."""
    try:
        logger.info(f"GET /recent - User: {user_id}, Limit: {limit}")

        # This would typically query the database for user-specific recent logs
        # For now, return empty list
        recent_logs = []

        logger.info(
            f"GET /recent successful - User: {user_id}, Logs: {len(recent_logs)}")
        return {
            "user_id": user_id,
            "logs": recent_logs,
            "total": len(recent_logs),
            "limit": limit
        }
    except Exception as e:
        logger.error(
            f"GET /recent exception - User: {user_id}, Error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get recent logs:  str(e)")
