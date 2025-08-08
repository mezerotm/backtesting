"""
Workflow Orchestrator - Handles complex workflows that combine multiple services
"""
import time
from typing import Dict, List, Any
from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from config.backend.logger import get_api_logger
from server.models.model_manager import get_model_manager
from server.api.market_data import market_data_service
from server.api.robinhood import pull_robinhood_data_internal
from server.api.auth import get_current_user_id, security

logger = get_api_logger("workflows")
router = APIRouter(prefix="/api/workflows", tags=["workflows"])


def extract_symbols_from_robinhood_data(
        robinhood_result: Dict[str, Any]) -> List[str]:
    """Extract unique symbols from Robinhood data response."""
    symbols = set()

    try:
        # Extract from positions
        positions = robinhood_result.get('data', {}).get('positions', [])
        for position in positions:
            if position.get('symbol'):
                symbols.add(position['symbol'])

        # Extract from orders
        orders = robinhood_result.get('data', {}).get('orders', [])
        for order in orders:
            if order.get('symbol'):
                symbols.add(order['symbol'])

        return list(symbols)
    except Exception as e:
        logger.error(f"Error extracting symbols from Robinhood data: {e}")
        return []


@router.post("/market-sync")
async def market_sync_workflow(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Primary market sync workflow that:
    1. Pulls Robinhood data (if enabled)
    2. Updates portfolio positions
    3. Refreshes market data for all portfolio symbols
    4. Updates symbol cache

    This is the main workflow that should be used for regular portfolio updates.
    """
    logger.info("=== Starting Market Sync Workflow ===")

    try:
        # Get user ID from authenticated session
        user_id = await get_current_user_id(credentials)
        if not user_id:
            raise HTTPException(
                status_code=401,
                detail="User not authenticated.")

        logger.info(f"Market sync workflow for user: {user_id}")

        # Step 1: Pull Robinhood data if enabled
        logger.info("Step 1: Checking Robinhood integration...")
        model_manager = get_model_manager()
        portfolio_data = model_manager.get_portfolio_data(user_id)

        robinhood_result = None
        if portfolio_data.get('robinhood_enabled'):
            logger.info("Robinhood enabled, attempting to pull data...")
            try:
                robinhood_result = await pull_robinhood_data_internal(credentials)

                if not robinhood_result.get('success'):
                    logger.error(
                        f"Robinhood data pull failed: {
                            robinhood_result.get('error')}")
                    # Continue with market data sync even if Robinhood fails
            except Exception as e:
                logger.error(f"Robinhood integration error: {e}")
                robinhood_result = {"success": False, "error": str(e)}
                # Continue with market data sync even if Robinhood fails

        # Step 2: Extract symbols from portfolio data
        logger.info("Step 2: Extracting symbols from portfolio data...")
        symbols = set()

        # Add symbols from Robinhood data if available
        if robinhood_result and robinhood_result.get('success'):
            symbols.update(
                extract_symbols_from_robinhood_data(robinhood_result))

        # Add symbols from existing portfolio positions
        positions = model_manager.get_positions(user_id)
        for position in positions:
            if position.get('symbol'):
                symbols.add(position['symbol'])

        if not symbols:
            logger.warning("No symbols found in portfolio")
            return {
                "success": True,
                "message": "Market sync completed but no symbols found",
                "robinhood_result": robinhood_result,
                "symbols_processed": 0
            }

        # Step 3: Refresh market data for all symbols
        logger.info(
            f"Step 3: Refreshing market data for {
                len(symbols)} symbols...")
        market_data_result = await market_data_sync_workflow_internal(list(symbols), user_id)

        # Step 4: Return combined results
        logger.info("=== Market Sync Workflow Complete ===")
        return {
            "success": True,
            "message": "Market sync workflow completed successfully",
            "robinhood_result": robinhood_result,
            "market_data_result": market_data_result,
            "symbols_processed": len(symbols)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Market sync workflow failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Workflow failed: {str(e)}")


@router.post("/symbol-sync")
async def symbol_sync_workflow(symbols: List[str], credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Targeted symbol sync workflow that refreshes market data for specific symbols.
    Use this when you need to update prices for specific symbols without pulling new portfolio data.

    Args:
        symbols: List of symbols to refresh market data for
    """
    logger.info("=== Starting Symbol Sync Workflow ===")

    try:
        # Get user ID from authenticated session
        user_id = await get_current_user_id(credentials)
        if not user_id:
            raise HTTPException(
                status_code=401,
                detail="User not authenticated.")

        logger.info(f"Symbol sync workflow for user: {
                    user_id}, symbols: {symbols}")

        if not symbols:
            return {
                "success": True,
                "message": "Symbol sync completed but no symbols provided",
                "symbols_processed": 0
            }

        # Refresh market data for provided symbols
        result = await market_data_sync_workflow_internal(symbols, user_id)

        logger.info("=== Symbol Sync Workflow Complete ===")
        return {
            "success": True,
            "message": "Symbol sync workflow completed successfully",
            "symbols_processed": len(symbols),
            "details": result
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Symbol sync workflow failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Workflow failed: {str(e)}")


@router.get("/status")
async def get_workflow_status(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get the current status of workflow components (Robinhood, market data, etc.)"""
    try:
        # Get user ID from authenticated session
        user_id = await get_current_user_id(credentials)
        if not user_id:
            raise HTTPException(
                status_code=401,
                detail="User not authenticated.")

        model_manager = get_model_manager()

        # Get portfolio settings
        portfolio_data = model_manager.get_portfolio_data(user_id)

        # Get latest sync timestamps
        latest_market_sync = model_manager.get_latest_market_sync(user_id)
        latest_robinhood_sync = model_manager.get_latest_robinhood_sync(
            user_id) if portfolio_data.get('robinhood_enabled') else None

        return {
            "success": True,
            "robinhood": {
                "enabled": portfolio_data.get(
                    'robinhood_enabled',
                    False),
                "last_sync": latest_robinhood_sync,
                "has_credentials": bool(
                    portfolio_data.get('robinhood_username'))},
            "market_data": {
                "last_sync": latest_market_sync,
                "symbols_cached": len(
                    model_manager.get_cached_symbols(user_id))}}
    except Exception as e:
        logger.error(f"Error getting workflow status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get workflow status: {str(e)}")


async def market_data_sync_workflow_internal(
        symbols: List[str], user_id: str) -> Dict[str, Any]:
    """
    Internal market data sync workflow - used by other workflows
    """
    logger.info(f"Refreshing market data for {len(symbols)} symbols...")

    try:
        # Fetch market data using the market data service
        symbol_data = market_data_service.fetch_symbol_data(symbols)

        if not symbol_data:
            logger.warning("No market data fetched")
            return {"success": False, "error": "No market data fetched"}

        # Save to database
        model_manager = get_model_manager()

        # Convert to database format
        symbol_data_list = []
        for symbol, data in symbol_data.items():
            symbol_record = {
                "symbol": symbol,
                "price": data.get("last_price"),
                "date": time.strftime('%Y-%m-%d'),
                "beta": data.get("beta"),
                "delta": None  # Delta not calculated yet
            }
            symbol_data_list.append(symbol_record)

        # Upsert to database
        upsert_results = model_manager.upsert_symbol_cache_records(
            symbol_data_list)

        logger.info(
            f"Market data sync completed: {
                len(symbol_data)} symbols processed")

        return {
            "success": True,
            "symbols_processed": len(symbol_data),
            "upsert_results": upsert_results
        }

    except Exception as e:
        logger.error(f"Market data sync failed: {e}")
        return {"success": False, "error": str(e)}
