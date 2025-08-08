from fastapi import APIRouter, Request, HTTPException, Body
from server.models import get_model_manager, Dividend, validate_dividend_data, transform_pocketbase_record, transform_to_pocketbase_data
from server.api.auth import get_current_user_id
from config.backend.logger import get_server_logger
from typing import List, Dict
from datetime import datetime

logger = get_server_logger("dividends")

router = APIRouter(prefix="/api/dividends", tags=["dividends"])


@router.get("/")
async def get_all_dividends(request: Request) -> List[Dict]:
    """Get all dividends from PocketBase."""
    try:
        logger.info("Getting all dividends from PocketBase...")
        model_manager = get_model_manager()

        # Get user ID from authenticated session
        user_id = await get_current_user_id(request)
        if not user_id:
            logger.warning(
                "No authenticated user found, returning empty dividends")
            return []

        # Get raw dividends from PocketBase
        raw_dividends = model_manager.get_dividends(user_id)

        # Transform to Pydantic models for validation
        dividends = []
        for raw_dividend in raw_dividends:
            try:
                dividend = transform_pocketbase_record(raw_dividend, Dividend)
                dividends.append(dividend)
            except Exception as e:
                logger.warning(
                    f"Invalid dividend data: {e}, skipping dividend {
                        raw_dividend.get(
                            'id', 'unknown')}")
                continue

        # Convert back to dictionaries for API response
        dividend_dicts = [transform_to_pocketbase_data(
            dividend) for dividend in dividends]

        logger.info(
            f"Retrieved {
                len(dividend_dicts)} dividends from PocketBase for user {user_id}")
        return dividend_dicts
    except Exception as e:
        logger.error(f"Error getting dividends: {e}")
        raise HTTPException(status_code=500,
                            detail=f"Error loading dividends: {e}")


@router.get("/received")
async def get_received_dividends(request: Request) -> List[Dict]:
    """Get received dividends only from PocketBase."""
    try:
        logger.info("Getting received dividends from PocketBase...")
        model_manager = get_model_manager()

        # Get user ID from authenticated session
        user_id = await get_current_user_id(request)
        if not user_id:
            logger.warning(
                "No authenticated user found, returning empty dividends")
            return []

        # Get raw dividends from PocketBase
        raw_dividends = model_manager.get_dividends(user_id)

        # Transform to Pydantic models and filter for received dividends
        received = []
        for raw_dividend in raw_dividends:
            try:
                dividend = transform_pocketbase_record(raw_dividend, Dividend)
                # Filter for received dividends (state = 'paid' or null for
                # Robinhood dividends)
                if dividend.state == 'paid' or dividend.state is None:
                    received.append(dividend)
            except Exception as e:
                logger.warning(
                    f"Invalid dividend data: {e}, skipping dividend {
                        raw_dividend.get(
                            'id', 'unknown')}")
                continue

        # Convert back to dictionaries for API response
        received_dicts = [transform_to_pocketbase_data(
            dividend) for dividend in received]

        logger.info(
            f"Retrieved {
                len(received_dicts)} received dividends from PocketBase for user {user_id}")
        return received_dicts
    except Exception as e:
        logger.error(f"Error filtering dividends: {e}")
        raise HTTPException(status_code=500,
                            detail=f"Error filtering dividends: {e}")


@router.get("/past")
async def get_past_dividends(request: Request) -> List[Dict]:
    """Get past dividends only from PocketBase."""
    try:
        logger.info("Getting past dividends from PocketBase...")
        model_manager = get_model_manager()

        # Get user ID from authenticated session
        user_id = await get_current_user_id(request)
        if not user_id:
            logger.warning(
                "No authenticated user found, returning empty dividends")
            return []

        dividends = model_manager.get_dividends(user_id)
        today = datetime.now().strftime("%Y-%m-%d")

        past = []
        for d in dividends:
            payable_date = d.get('payable_date', '')
            if payable_date and payable_date < today:
                past.append(d)

        logger.info(
            f"Retrieved {
                len(past)} past dividends from PocketBase for user {user_id}")
        return past
    except Exception as e:
        logger.error(f"Error filtering past dividends: {e}")
        raise HTTPException(status_code=500,
                            detail=f"Error filtering past dividends: {e}")


@router.get("/summary")
async def get_dividends_summary(request: Request) -> Dict:
    """Get dividends summary from PocketBase."""
    try:
        logger.info("Getting dividends summary from PocketBase...")
        model_manager = get_model_manager()

        # Get user ID from authenticated session
        user_id = await get_current_user_id(request)
        if not user_id:
            logger.warning(
                "No authenticated user found, returning empty summary")
            return {
                "total_this_year": 0.0,
                "total_dividends": 0,
                "received_dividends": 0
            }

        dividends = model_manager.get_dividends(user_id)
        current_year = datetime.now().year

        total_this_year = 0.0
        for d in dividends:
            if d.get('state') == 'paid':
                payable_date = d.get('payable_date', '')
                if payable_date and payable_date.startswith(str(current_year)):
                    total_this_year += float(d.get('amount', 0))

        summary = {
            "total_this_year": total_this_year,
            "total_dividends": len(dividends),
            "received_dividends": len([d for d in dividends if d.get('state') == 'paid'])
        }

        logger.info(f"Retrieved dividends summary from PocketBase for user {
                    user_id}: {summary}")
        return summary
    except Exception as e:
        logger.error(f"Error calculating summary: {e}")
        raise HTTPException(status_code=500,
                            detail=f"Error calculating summary: {e}")


@router.post("/record")
async def record_dividend(data: dict = Body(...), request: Request = None):
    """Record a new dividend in PocketBase."""
    try:
        logger.info(f"Recording dividend for {data.get('symbol')}...")
        model_manager = get_model_manager()

        # Get user ID from authenticated session
        user_id = await get_current_user_id(request)
        if not user_id:
            logger.warning(
                "Dividends API called without authentication - expected for fresh starts")
            raise HTTPException(
                status_code=401,
                detail="User not authenticated")

        # Add user ID to dividend data
        data["user"] = user_id

        if model_manager.add_dividends([data]):
            logger.info(
                f"Successfully recorded dividend for {
                    data.get('symbol')}")
            return {"status": "ok"}
        else:
            raise HTTPException(
                status_code=400,
                detail="Failed to record dividend")
    except Exception as e:
        logger.error(f"Error recording dividend: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to record dividend")
