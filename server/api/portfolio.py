"""
Portfolio API endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict, Any, List
from server.services.portfolio_service import PortfolioService
from server.api.auth import get_current_user_id
from server.database.models.portfolio import Position, PositionCreate, PositionUpdate
from config.backend.logger import get_api_logger

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])

# Initialize services and logger
portfolio_service = PortfolioService()
logger = get_api_logger("portfolio")


@router.get("/summary")
async def get_portfolio_summary(user_id: str = Depends(
        get_current_user_id)) -> Dict[str, Any]:
    """Get portfolio summary for the current user."""
    logger.info(f"GET /summary - User: {user_id}")

    try:
        result = await portfolio_service.get_portfolio_summary(user_id)

        if not result.get("success"):
            error_msg = result.get("error", "Failed to get portfolio summary")
            logger.error(
                f"GET /summary failed - User: {user_id}, Error: {error_msg}")
            raise HTTPException(status_code=400, detail=error_msg)

        logger.info(f"GET /summary successful - User: {user_id}, Positions: {
                    len(result.get('data', {}).get('positions', []))}")
        return result["data"]
    except Exception as e:
        logger.error(
            f"GET /summary exception - User: {user_id}, Error: {str(e)}")
        raise


@router.get("/settings")
async def get_portfolio_settings(user_id: str = Depends(
        get_current_user_id)) -> Dict[str, Any]:
    """Get portfolio settings for the current user."""
    logger.info(f"GET /settings - User: {user_id}")

    try:
        result = await portfolio_service.get_portfolio_settings(user_id)

        if not result.get("success"):
            error_msg = result.get("error", "Failed to get portfolio settings")
            logger.error(
                f"GET /settings failed - User: {user_id}, Error: {error_msg}")
            raise HTTPException(status_code=400, detail=error_msg)

        logger.info(f"GET /settings successful - User: {user_id}")
        return result["data"]
    except Exception as e:
        logger.error(
            f"GET /settings exception - User: {user_id}, Error: {str(e)}")
        raise


@router.put("/settings")
async def update_portfolio_settings(
    settings: Dict[str, Any],
    user_id: str = Depends(get_current_user_id)
) -> Dict[str, Any]:
    """Update portfolio settings for the current user."""
    try:
        # Log incoming request (excluding sensitive data)
        safe_settings = {
            k: '***' if k in ['robinhood_password', 'robinhood_mfa'] else v
            for k, v in settings.items()
        }
        logger.info(
            f"PUT /settings - User: {user_id}, Settings: {safe_settings}")

        # Validate numeric fields (use frontend keys)
        numeric_fields = [
            'total_portfolio_cash',
            'total_portfolio_btc',
            'btc_avg_buy_price']
        for field in numeric_fields:
            if field in settings:
                try:
                    value = float(settings[field])
                    if value < 0:
                        raise HTTPException(
                            status_code=400,
                            detail=f"{field} cannot be negative"
                        )
                    settings[field] = value
                except (TypeError, ValueError):
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid value for {field}. Must be a valid number."
                    )

        # Convert boolean fields
        if 'robinhood_enabled' in settings:
            settings['robinhood_enabled'] = bool(settings['robinhood_enabled'])

        # Clean up string fields
        string_fields = [
            'robinhood_username',
            'robinhood_password',
            'robinhood_mfa']
        for field in string_fields:
            if field in settings:
                value = settings[field]
                settings[field] = str(value).strip() if value else None

        # Remap frontend key to backend key expected by service
        if 'total_portfolio_cash' in settings and 'portfolio_cash' not in settings:
            settings['portfolio_cash'] = settings['total_portfolio_cash']

        result = await portfolio_service.update_portfolio_settings(user_id, settings)

        if not result.get("success"):
            error_msg = result.get(
                "error", "Failed to update portfolio settings")
            logger.error(
                f"PUT /settings failed - User: {user_id}, Error: {error_msg}")
            raise HTTPException(status_code=400, detail=error_msg)

        logger.info(f"PUT /settings successful - User: {user_id}")
        return result["data"]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"PUT /settings exception - User: {user_id}, Error: {str(e)}")
        logger.exception(e)  # Log full traceback
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.post("/settings")
async def set_portfolio_settings(
    settings: Dict[str, Any],
    user_id: str = Depends(get_current_user_id)
) -> Dict[str, Any]:
    """Set portfolio settings for the current user."""
    logger.info(
        f"POST /settings - User: {user_id}, Settings keys: {list(settings.keys())}")

    try:
        result = await portfolio_service.update_portfolio_settings(user_id, settings)

        if not result.get("success"):
            error_msg = result.get(
                "error", "Failed to update portfolio settings")
            logger.error(
                f"POST /settings failed - User: {user_id}, Error: {error_msg}")
            raise HTTPException(status_code=400, detail=error_msg)

        logger.info(f"POST /settings successful - User: {user_id}")
        return result["data"]
    except Exception as e:
        logger.error(
            f"POST /settings exception - User: {user_id}, Error: {str(e)}")
        raise


@router.get("/search-symbols")
async def search_symbols(
    query: str = Query(..., min_length=1),
    user_id: str = Depends(get_current_user_id)
) -> Dict[str, Any]:
    """Search for symbols."""
    logger.info(f"GET /search-symbols - User: {user_id}, Query: {query}")

    try:
        result = await portfolio_service.search_symbols(query)

        if not result.get("success"):
            error_msg = result.get("error", "Failed to search symbols")
            logger.error(
                f"GET /search-symbols failed - User: {user_id}, Query: {query}, Error: {error_msg}")
            raise HTTPException(status_code=400, detail=error_msg)

        symbols_count = len(result.get("data", []))
        logger.info(f"GET /search-symbols successful - User: {
                    user_id}, Query: {query}, Results: {symbols_count}")
        return result["data"]
    except Exception as e:
        logger.error(
            f"GET /search-symbols exception - User: {user_id}, Query: {query}, Error: {str(e)}")
        raise


@router.get("/latest-price/{symbol}")
async def get_latest_price(
    symbol: str,
    user_id: str = Depends(get_current_user_id)
) -> Dict[str, Any]:
    """Get latest price for a symbol."""
    logger.info(f"GET /latest-price/{symbol} - User: {user_id}")

    try:
        result = await portfolio_service.get_latest_price(symbol)

        if not result.get("success"):
            error_msg = result.get("error", "Failed to get latest price")
            logger.error(
                f"GET /latest-price/{symbol} failed - User: {user_id}, Error: {error_msg}")
            raise HTTPException(status_code=400, detail=error_msg)

        price = result.get("data", {}).get("price")
        logger.info(
            f"GET /latest-price/{symbol} successful - User: {user_id}, Price: {price}")
        return result["data"]
    except Exception as e:
        logger.error(
            f"GET /latest-price/{symbol} exception - User: {user_id}, Error: {str(e)}")
        raise


@router.get("/cash")
async def get_portfolio_cash(user_id: str = Depends(
        get_current_user_id)) -> Dict[str, Any]:
    """Get portfolio cash for the current user."""
    logger.info(f"GET /cash - User: {user_id}")

    try:
        result = await portfolio_service.get_portfolio_cash(user_id)

        if not result.get("success"):
            error_msg = result.get("error", "Failed to get portfolio cash")
            logger.error(
                f"GET /cash failed - User: {user_id}, Error: {error_msg}")
            raise HTTPException(status_code=400, detail=error_msg)

        cash = result.get("data", {}).get("cash")
        logger.info(f"GET /cash successful - User: {user_id}, Cash: {cash}")
        return result["data"]
    except Exception as e:
        logger.error(f"GET /cash exception - User: {user_id}, Error: {str(e)}")
        raise


@router.post("/cash")
async def set_portfolio_cash(
    data: Dict[str, Any],
    user_id: str = Depends(get_current_user_id)
) -> Dict[str, Any]:
    """Set portfolio cash for the current user."""
    cash = data.get("cash", 0)
    logger.info(f"POST /cash - User: {user_id}, Cash: {cash}")

    try:
        result = await portfolio_service.set_portfolio_cash(user_id, data)

        if not result.get("success"):
            error_msg = result.get("error", "Failed to set portfolio cash")
            logger.error(
                f"POST /cash failed - User: {user_id}, Cash: {cash}, Error: {error_msg}")
            raise HTTPException(status_code=400, detail=error_msg)

        logger.info(f"POST /cash successful - User: {user_id}, Cash: {cash}")
        return result["data"]
    except Exception as e:
        logger.error(
            f"POST /cash exception - User: {user_id}, Cash: {cash}, Error: {str(e)}")
        raise


@router.get("/btc")
async def get_portfolio_btc(user_id: str = Depends(
        get_current_user_id)) -> Dict[str, Any]:
    """Get portfolio BTC for the current user."""
    logger.info(f"GET /btc - User: {user_id}")

    try:
        result = await portfolio_service.get_portfolio_btc(user_id)

        if not result.get("success"):
            error_msg = result.get("error", "Failed to get portfolio BTC")
            logger.error(
                f"GET /btc failed - User: {user_id}, Error: {error_msg}")
            raise HTTPException(status_code=400, detail=error_msg)

        logger.info(f"GET /btc successful - User: {user_id}")
        return result["data"]
    except Exception as e:
        logger.error(f"GET /btc exception - User: {user_id}, Error: {str(e)}")
        raise


@router.post("/btc")
async def set_portfolio_btc(
    data: Dict[str, Any],
    user_id: str = Depends(get_current_user_id)
) -> Dict[str, Any]:
    """Set portfolio BTC for the current user."""
    logger.info(f"POST /btc - User: {user_id}, Data keys: {list(data.keys())}")

    try:
        result = await portfolio_service.set_portfolio_btc(user_id, data)

        if not result.get("success"):
            error_msg = result.get("error", "Failed to set portfolio BTC")
            logger.error(
                f"POST /btc failed - User: {user_id}, Error: {error_msg}")
            raise HTTPException(status_code=400, detail=error_msg)

        logger.info(f"POST /btc successful - User: {user_id}")
        return result["data"]
    except Exception as e:
        logger.error(f"POST /btc exception - User: {user_id}, Error: {str(e)}")
        raise


@router.post("/refresh-symbols")
async def refresh_symbol_data(user_id: str = Depends(
        get_current_user_id)) -> Dict[str, Any]:
    """Refresh symbol data for the current user's portfolio."""
    logger.info(f"POST /refresh-symbols - User: {user_id}")

    try:
        result = await portfolio_service.refresh_symbol_data(user_id)

        if not result.get("success"):
            error_msg = result.get("error", "Failed to refresh symbol data")
            logger.error(
                f"POST /refresh-symbols failed - User: {user_id}, Error: {error_msg}")
            raise HTTPException(status_code=400, detail=error_msg)

        symbols_count = len(result.get("data", {}).get("symbols", []))
        logger.info(
            f"POST /refresh-symbols successful - User: {user_id}, Symbols refreshed: {symbols_count}")
        return result["data"]
    except Exception as e:
        logger.error(
            f"POST /refresh-symbols exception - User: {user_id}, Error: {str(e)}")
        raise


# Now the parameterized routes (must come after specific routes)
@router.get("/")
async def get_user_positions(user_id: str = Depends(
        get_current_user_id)) -> Dict[str, Any]:
    """Get all positions for the current user."""
    logger.info(f"GET / - User: {user_id}")

    try:
        result = await portfolio_service.get_user_positions(user_id)

        if not result.get("success"):
            error_msg = result.get("error", "Failed to get user positions")
            logger.error(
                f"GET / failed - User: {user_id}, Error: {error_msg}")
            raise HTTPException(status_code=400, detail=error_msg)

        positions_count = len(result.get("data", []))
        logger.info(
            f"GET / successful - User: {user_id}, Positions: {positions_count}")
        return {"positions": result["data"]}  # Wrap in dictionary
    except Exception as e:
        logger.error(
            f"GET / exception - User: {user_id}, Error: {str(e)}")
        raise


@router.post("/")
async def add_position(
    position: PositionCreate,
    user_id: str = Depends(get_current_user_id)
) -> Dict[str, Any]:
    """Add a new position for the current user."""
    logger.info(
        f"POST / - User: {user_id}, Symbol: {
            position.symbol}, Quantity: {
            position.quantity}")

    try:
        result = await portfolio_service.create_position(user_id, position)

        if not result.get("success"):
            error_msg = result.get("error", "Failed to create position")
            logger.error(
                f"POST / failed - User: {user_id}, Symbol: {position.symbol}, Error: {error_msg}")
            raise HTTPException(status_code=400, detail=error_msg)

        logger.info(
            f"POST / successful - User: {user_id}, Symbol: {
                position.symbol}, Position ID: {
                result.get(
                    'data',
                    {}).get('id')}")
        return result["data"]
    except Exception as e:
        logger.error(
            f"POST / exception - User: {user_id}, Symbol: {position.symbol}, Error: {str(e)}")
        raise


@router.delete("/{position_id}")
async def delete_position(
    position_id: str,
    user_id: str = Depends(get_current_user_id)
) -> Dict[str, Any]:
    """Delete a position for the current user."""
    logger.info(f"DELETE /{position_id} - User: {user_id}")

    try:
        result = await portfolio_service.delete_position(position_id)

        if not result.get("success"):
            error_msg = result.get("error", "Failed to delete position")
            logger.error(
                f"DELETE /{position_id} failed - User: {user_id}, Error: {error_msg}")
            raise HTTPException(status_code=400, detail=error_msg)

        logger.info(f"DELETE /{position_id} successful - User: {user_id}")
        return result["data"]
    except Exception as e:
        logger.error(
            f"DELETE /{position_id} exception - User: {user_id}, Error: {str(e)}")
        raise


@router.put("/{position_id}")
async def update_position(
    position_id: str,
    position: PositionUpdate,
    user_id: str = Depends(get_current_user_id)
) -> Dict[str, Any]:
    """Update an existing position for the current user."""
    logger.info(f"PUT /{position_id} - User: {user_id}")

    try:
        result = await portfolio_service.update_position(position_id, position)

        if not result.get("success"):
            error_msg = result.get("error", "Failed to update position")
            logger.error(
                f"PUT /{position_id} failed - User: {user_id}, Error: {error_msg}")
            raise HTTPException(status_code=400, detail=error_msg)

        logger.info(f"PUT /{position_id} successful - User: {user_id}")
        return result["data"]
    except Exception as e:
        logger.error(
            f"PUT /{position_id} exception - User: {user_id}, Error: {str(e)}")
        raise
