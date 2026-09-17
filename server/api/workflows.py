"""
Workflow Orchestrator - Handles complex workflows that combine multiple services
"""
import asyncio
import random
import time
from typing import Dict, List, Any, Optional
from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from config.backend.logger import get_api_logger
from server.models.model_manager import get_model_manager
from server.api.market_data import market_data_service
from server.api.robinhood import pull_robinhood_data_internal
from server.api.auth import get_current_user_id, security

logger = get_api_logger("workflows")
router = APIRouter(prefix="/api/workflows", tags=["workflows"])

# ── Background sync task tracking ──
_sync_tasks: dict[str, dict] = {}


async def _cleanup_stale_syncs():
    """Remove sync tasks older than 10 minutes to prevent memory leaks."""
    now = time.time()
    stale = [sid for sid, t in _sync_tasks.items()
             if t.get('_started_at', 0) < now - 600]
    for sid in stale:
        _sync_tasks.pop(sid, None)


async def _run_background_sync(sync_id: str, user_id: str, token: str):
    """Run the Robinhood sync in a background asyncio task, updating progress."""
    try:
        _sync_tasks[sync_id] = {
            "status": "running",
            "progress": "Pulling Robinhood positions...",
            "_started_at": time.time()
        }

        # Recreate credentials object for the internal function
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        # Step 1: Pull Robinhood data
        _sync_tasks[sync_id]["progress"] = "Pulling stock positions..."
        try:
            robinhood_result = await asyncio.wait_for(
                pull_robinhood_data_internal(creds),
                timeout=240
            )
        except asyncio.TimeoutError:
            logger.error(f"Background sync {sync_id}: Robinhood pull timed out after 240s")
            _sync_tasks[sync_id] = {
                "status": "error",
                "progress": "Robinhood pull timed out — try again for full sync",
                "error": "Sync timed out after 240s — data may be incomplete. Try again for full sync.",
                "_started_at": _sync_tasks[sync_id].get('_started_at', time.time())
            }
            return

        if not robinhood_result.get('success'):
            _sync_tasks[sync_id] = {
                "status": "error",
                "progress": robinhood_result.get('error', 'Robinhood pull failed'),
                "error": robinhood_result.get('error', 'Unknown error'),
                "_started_at": _sync_tasks[sync_id].get('_started_at', time.time())
            }
            return

        _sync_tasks[sync_id]["progress"] = "Extracting portfolio symbols..."

        # Step 2: Extract symbols from Robinhood data + existing positions
        model_manager = get_model_manager()
        symbols = set()

        # pull_robinhood_data_internal returns positions/orders as top-level keys
        for position in robinhood_result.get('positions', {}).get('mapped', []):
            if position.get('symbol'):
                symbols.add(position['symbol'])
        for order in robinhood_result.get('orders', {}).get('mapped', []):
            if order.get('symbol'):
                symbols.add(order['symbol'])

        positions = model_manager.get_positions(user_id)
        for position in positions:
            if position.get('symbol'):
                symbols.add(position['symbol'])

        if not symbols:
            _sync_tasks[sync_id] = {
                "status": "done",
                "progress": "No symbols found",
                "result": robinhood_result,
                "symbols_processed": 0,
                "_started_at": _sync_tasks[sync_id].get('_started_at', time.time())
            }
            return

        # Step 3: Refresh market data
        _sync_tasks[sync_id]["progress"] = f"Refreshing market data for {len(symbols)} symbols..."
        try:
            from server.api.market_data import market_data_service
            symbol_data = market_data_service.fetch_symbol_data(list(symbols))
            if symbol_data:
                symbol_records = []
                for sym, data in symbol_data.items():
                    symbol_records.append({
                        "symbol": sym,
                        "price": data.get("last_price"),
                        "date": time.strftime('%Y-%m-%d'),
                        "beta": data.get("beta"),
                        "delta": None
                    })
                model_manager.upsert_symbol_cache_records(symbol_records)
        except Exception as md_error:
            logger.error(f"Market data refresh failed: {md_error}")

        # Done
        _sync_tasks[sync_id] = {
            "status": "done",
            "progress": "Sync complete",
            "result": robinhood_result,
            "symbols_processed": len(symbols),
            "_started_at": _sync_tasks[sync_id].get('_started_at', time.time())
        }
        logger.info(f"Background sync {sync_id} completed for user {user_id}")

    except Exception as e:
        logger.error(f"Background sync {sync_id} failed: {e}")
        _sync_tasks[sync_id] = {
            "status": "error",
            "progress": f"Sync error: {e}",
            "error": str(e),
            "_started_at": _sync_tasks[sync_id].get('_started_at', time.time()) if sync_id in _sync_tasks else time.time()
        }


@router.post("/sync-start")
async def sync_start(
    credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Start a background sync. Returns immediately with a sync_id for polling."""
    # Clean up stale tasks periodically
    await _cleanup_stale_syncs()

    user_id = await get_current_user_id(credentials)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    sync_id = f"sync_{int(time.time())}_{random.randint(1000, 9999)}"
    token = credentials.credentials  # Extract raw token for background use

    _sync_tasks[sync_id] = {
        "status": "starting",
        "progress": "Starting sync...",
        "_started_at": time.time()
    }

    asyncio.create_task(_run_background_sync(sync_id, user_id, token))

    return {"status": "started", "sync_id": sync_id}


@router.get("/sync-status/{sync_id}")
async def get_sync_status(sync_id: str):
    """Get the current status of a background sync task."""
    task = _sync_tasks.get(sync_id)
    if not task:
        raise HTTPException(status_code=404, detail="Sync task not found or expired")

    # Return a clean response without internal fields
    return {
        "sync_id": sync_id,
        "status": task["status"],
        "progress": task.get("progress", ""),
        "error": task.get("error"),
        "symbols_processed": task.get("symbols_processed", 0)
    }


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
async def market_sync_workflow(
        timeout: int = 300,
        credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Primary market sync workflow that:
    1. Pulls Robinhood data (if enabled)
    2. Updates portfolio positions
    3. Refreshes market data for all portfolio symbols
    4. Updates symbol cache

    Args:
        timeout: Maximum seconds to wait for the sync to complete (default 300, 0 = no timeout)
    """
    logger.info(f"=== Starting Market Sync Workflow (timeout={timeout}s) ===")

    try:
        # Apply timeout if specified
        if timeout > 0:
            return await asyncio.wait_for(
                _do_market_sync(credentials, timeout),
                timeout=timeout)
        else:
            return await _do_market_sync(credentials, timeout)

    except asyncio.TimeoutError:
        logger.error(
            f"Market sync workflow timed out after {timeout}s, returning partial results")
        return {
            "success": False,
            "message": f"Market sync timed out after {timeout}s, partial data may have been saved",
            "partial": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Market sync workflow failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Workflow failed: {str(e)}")


async def _do_market_sync(
        credentials: HTTPAuthorizationCredentials, timeout: int) -> Dict[str, Any]:
    """Internal market sync logic with timeout support."""
    try:
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
                robinhood_result = await asyncio.wait_for(
                    pull_robinhood_data_internal(credentials),
                    timeout=120
                )

                if not robinhood_result.get('success'):
                    logger.error(
                        f"Robinhood data pull failed: {robinhood_result.get('error')}")

                    # Continue with market data sync even if Robinhood fails
            except asyncio.TimeoutError:
                logger.error("Robinhood data pull timed out after 120s total")
                robinhood_result = {
                    "success": True,
                    "partial": True,
                    "error": "Sync timed out after 120s — data may be incomplete. Try again for full sync."
                }
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
            f"Step 3: Refreshing market data for  len(symbols) symbols...")

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
async def symbol_sync_workflow(
        symbols: List[str],
        credentials: HTTPAuthorizationCredentials = Depends(security)):
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

        logger.info(
            f"Symbol sync workflow for user: {user_id}, symbols: {symbols}")

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
async def get_workflow_status(
        credentials: HTTPAuthorizationCredentials = Depends(security)):
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
            f"Market data sync completed:  len(symbol_data) symbols processed")

        return {
            "success": True,
            "symbols_processed": len(symbol_data),
            "upsert_results": upsert_results
        }

    except Exception as e:
        logger.error(f"Market data sync failed: {e}")
        return {"success": False, "error": str(e)}
