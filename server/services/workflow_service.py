"""
Workflow service for orchestrating complex business processes.
"""

from typing import Dict, Any, List
from .base_service import BaseService
from .portfolio_service import PortfolioService
from .robinhood_service import RobinhoodService
from .market_data_service import MarketDataService


class WorkflowService(BaseService):
    """Service for orchestrating complex workflows."""

    def __init__(self):
        super().__init__()
        self.portfolio_service = PortfolioService()
        self.robinhood_service = RobinhoodService()
        self.market_data_service = MarketDataService()

    async def robinhood_sync_workflow(self, user_id: str) -> Dict[str, Any]:
        """Orchestrate Robinhood data sync workflow."""
        try:
            self.log_operation("robinhood_sync_workflow", {"user_id": user_id})

            # Step 1: Pull data from Robinhood
            robinhood_result = await self.robinhood_service.pull_robinhood_data(user_id)
            if not robinhood_result.get("success"):
                return robinhood_result

            # Step 2: Get updated positions
            positions_result = await self.portfolio_service.get_user_positions(user_id)
            if not positions_result.get("success"):
                return positions_result

            # Step 3: Extract symbols for market data refresh
            positions = positions_result.get("data", [])
            symbols = [pos['symbol']
                       for pos in positions if pos['symbol'] != 'CASH']

            # Step 4: Refresh market data
            if symbols:
                market_result = await self.market_data_service.refresh_symbols(symbols)
                if not market_result.get("success"):
                    return market_result

            return {
                "success": True,
                "data": {
                    "robinhood_sync": robinhood_result.get("data", {}),
                    "positions_count": len(positions),
                    "symbols_refreshed": len(symbols),
                    "message": "Robinhood sync workflow completed successfully"
                }
            }
        except Exception as e:
            return self.handle_error(e, "robinhood_sync_workflow")

    async def market_data_sync_workflow(self, user_id: str) -> Dict[str, Any]:
        """Orchestrate market data sync workflow."""
        try:
            self.log_operation(
                "market_data_sync_workflow", {
                    "user_id": user_id})

            # Step 1: Get current positions
            positions_result = await self.portfolio_service.get_user_positions(user_id)
            if not positions_result.get("success"):
                return positions_result

            # Step 2: Extract symbols
            positions = positions_result.get("data", [])
            symbols = [pos['symbol']
                       for pos in positions if pos['symbol'] != 'CASH']

            if not symbols:
                return {
                    "success": True,
                    "data": {
                        "message": "No symbols to refresh",
                        "symbols_refreshed": 0
                    }
                }

            # Step 3: Refresh market data
            market_result = await self.market_data_service.refresh_symbols(symbols)
            if not market_result.get("success"):
                return market_result

            return {
                "success": True,
                "data": {
                    "symbols_refreshed": len(symbols),
                    "market_data_result": market_result.get(
                        "data",
                        {}),
                    "message": "Market data sync workflow completed successfully"}}
        except Exception as e:
            return self.handle_error(e, "market_data_sync_workflow")

    async def full_sync_workflow(self, user_id: str) -> Dict[str, Any]:
        """Orchestrate full sync workflow (Robinhood + Market Data)."""
        try:
            self.log_operation("full_sync_workflow", {"user_id": user_id})

            # Step 1: Robinhood sync
            robinhood_result = await self.robinhood_sync_workflow(user_id)
            if not robinhood_result.get("success"):
                return robinhood_result

            # Step 2: Market data sync
            market_result = await self.market_data_sync_workflow(user_id)
            if not market_result.get("success"):
                return market_result

            # Step 3: Get final portfolio summary
            summary_result = await self.portfolio_service.get_portfolio_summary(user_id)
            if not summary_result.get("success"):
                return summary_result

            return {
                "success": True,
                "data": {
                    "robinhood_sync": robinhood_result.get("data", {}),
                    "market_data_sync": market_result.get("data", {}),
                    "portfolio_summary": summary_result.get("data", {}),
                    "message": "Full sync workflow completed successfully"
                }
            }
        except Exception as e:
            return self.handle_error(e, "full_sync_workflow")

    async def get_workflow_status(self, user_id: str) -> Dict[str, Any]:
        """Get status of all workflows for a user."""
        try:
            self.log_operation("get_workflow_status", {"user_id": user_id})

            # Get Robinhood status
            robinhood_status = await self.robinhood_service.get_robinhood_status(user_id)

            # Get market data status
            market_data_status = await self.market_data_service.get_rate_limit_stats()

            # Get portfolio summary
            portfolio_summary = await self.portfolio_service.get_portfolio_summary(user_id)

            return {
                "success": True,
                "data": {
                    "robinhood": robinhood_status.get("data", {}),
                    "market_data": market_data_status.get("data", {}),
                    "portfolio": portfolio_summary.get("data", {}),
                    "last_updated": "2024-01-01T00:00:00Z"  # Should be dynamic
                }
            }
        except Exception as e:
            return self.handle_error(e, "get_workflow_status")
