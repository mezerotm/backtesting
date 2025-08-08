"""
Portfolio service for managing portfolio data and operations.
"""

from typing import Dict, Any, Optional
from decimal import Decimal
from datetime import datetime
from server.services.base_service import BaseService
from .market_data_service import MarketDataService
from server.database.repositories.portfolio_repository import PortfolioRepository
from server.database.models.portfolio import PositionCreate, PositionUpdate
from server.database.models.portfolio import Position
from server.database.models.portfolio import PortfolioSettings


class PortfolioService(BaseService):
    """Service for portfolio-related business logic."""

    def __init__(self):
        super().__init__()
        self.market_data_service = MarketDataService()
        self.portfolio_repository = PortfolioRepository()

    async def get_portfolio_summary(self, user_id: str) -> Dict[str, Any]:
        """Get portfolio summary including positions."""
        try:
            # Get positions
            positions_result = await self.get_user_positions(user_id)
            if not positions_result["success"]:
                return positions_result

            # Get portfolio settings
            settings = await self.get_portfolio_settings(user_id)
            if not settings["success"]:
                return settings

            # Convert positions to frontend format
            frontend_positions = []
            for pos in positions_result["data"]:
                # Create a Position object with the correct field mapping
                position_obj = Position(
                    id=pos["id"],
                    user=user_id,
                    symbol=pos["symbol"],
                    quantity=Decimal(str(pos["quantity"])),
                    buy_price=Decimal(str(pos["buy_price"])),
                    market_value=Decimal(str(pos["market_value"])) if pos["market_value"] else None,
                    current_price=Decimal(str(pos["current_price"])) if pos["current_price"] else None,
                    total_return=Decimal(str(pos["total_return"])) if pos["total_return"] else None,
                    total_return_percent=Decimal(str(pos["total_return_percent"])) if pos["total_return_percent"] else None,
                    is_crypto=pos["is_crypto"],
                    source=pos["source"],
                    notes=pos["notes"],
                    pulled_at=pos["pulled_at"],
                    updated_at=datetime.fromisoformat(pos["updated_at"]) if pos["updated_at"] else None
                )
                frontend_positions.append(position_obj.to_frontend_dict())

            return {
                "success": True,
                "data": {
                    "positions": frontend_positions,
                    "total_value": settings["data"]["total_portfolio_cash"],
                    "total_cash": settings["data"]["total_portfolio_cash"],
                    "total_btc": settings["data"].get(
                        "total_portfolio_btc",
                        0),
                    "btc_avg_price": settings["data"].get(
                        "btc_avg_buy_price",
                        0)}}
        except Exception as e:
            return self.handle_error(e, "get_portfolio_summary")

    async def get_user_positions(self, user_id: str) -> Dict[str, Any]:
        """Get all positions for a user."""
        try:
            self.log_operation("get_user_positions", {"user_id": user_id})

            positions = await self.portfolio_repository.get_user_positions(user_id)

            # Refresh market data for positions
            symbols = [pos.symbol for pos in positions if pos.symbol != 'CASH']
            if symbols:
                await self.market_data_service.refresh_symbols(symbols)

            # Convert to dict for API response
            positions_data = []
            for pos in positions:
                positions_data.append({
                    "id": pos.id,
                    "symbol": pos.symbol,
                    "quantity": float(pos.quantity),
                    # Changed from cost_basis
                    "buy_price": float(pos.buy_price),
                    "market_value": float(pos.market_value) if pos.market_value else None,
                    "current_price": float(pos.current_price) if pos.current_price else None,
                    "total_return": float(pos.total_return) if pos.total_return else None,
                    "total_return_percent": float(pos.total_return_percent) if pos.total_return_percent else None,
                    "is_crypto": pos.is_crypto,
                    "source": pos.source,
                    "notes": pos.notes,
                    "pulled_at": pos.pulled_at,  # Changed from created_at
                    "updated_at": pos.updated_at.isoformat() if pos.updated_at else None
                })

            return {
                "success": True,
                "data": positions_data
            }
        except Exception as e:
            return self.handle_error(e, "get_user_positions")

    async def get_portfolio_settings(self, user_id: str) -> Dict[str, Any]:
        """Get portfolio settings for a user."""
        try:
            self.log_operation("get_portfolio_settings", {"user_id": user_id})

            settings = await self.portfolio_repository.get_portfolio_settings(user_id)
            if not settings:
                # Create default settings for new users
                settings = await self.portfolio_repository.create_portfolio_settings(
                    user_id, Decimal('0')
                )
                if not settings:
                    return self.handle_error(
                        Exception("Failed to create default portfolio settings"),
                        "get_portfolio_settings")

            return {
                "success": True,
                "data": {
                    "total_portfolio_cash": float(settings.portfolio_cash),
                    "total_portfolio_btc": float(settings.total_portfolio_btc),
                    "btc_avg_buy_price": float(settings.btc_avg_buy_price),
                    "robinhood_username": settings.robinhood_username or "",
                    "robinhood_password": settings.robinhood_password or "",
                    "robinhood_mfa": settings.robinhood_mfa or "",
                    "robinhood_enabled": settings.robinhood_enabled,
                    "auto_sync": settings.auto_sync,
                    "sync_interval": settings.sync_interval,
                    "updated_at": settings.updated_at.isoformat() if settings.updated_at else None
                }
            }
        except Exception as e:
            return self.handle_error(e, "get_portfolio_settings")

    async def update_portfolio_settings(
            self, user_id: str, settings_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update portfolio settings for a user."""
        try:
            self.logger.info(
                f"Received settings update request - User: {user_id}")

            # Log incoming data (excluding sensitive info)
            safe_settings = {
                k: '***' if k in ['robinhood_password', 'robinhood_mfa'] else v
                for k, v in settings_data.items()
            }
            self.logger.debug(f"Raw settings data: {safe_settings}")

            # Map frontend key to backend key if needed
            if 'total_portfolio_cash' in settings_data and 'portfolio_cash' not in settings_data:
                settings_data['portfolio_cash'] = settings_data['total_portfolio_cash']

            # Also map the reverse for consistency
            if 'portfolio_cash' in settings_data and 'total_portfolio_cash' not in settings_data:
                settings_data['total_portfolio_cash'] = settings_data['portfolio_cash']

            # Convert numeric fields to Decimal
            numeric_fields = [
                'portfolio_cash',
                'total_portfolio_cash',
                'total_portfolio_btc',
                'btc_avg_buy_price']
            for field in numeric_fields:
                if field in settings_data:
                    try:
                        settings_data[field] = Decimal(
                            str(settings_data[field]))
                    except (TypeError, ValueError) as e:
                        self.logger.error(
                            f"Error converting {field} to Decimal: {
                                str(e)}")
                        return self.handle_error(
                            ValueError(
                                f"Invalid value for {field}. Must be a valid number."),
                            "update_portfolio_settings")

            # Create PortfolioSettings instance
            try:
                # Use the correct cash field (prioritize portfolio_cash,
                # fallback to total_portfolio_cash)
                cash_value = settings_data.get(
                    'portfolio_cash', settings_data.get(
                        'total_portfolio_cash', Decimal('0')))

                settings = PortfolioSettings(
                    user_id=user_id,
                    portfolio_cash=cash_value,
                    total_portfolio_btc=settings_data.get(
                        'total_portfolio_btc',
                        Decimal('0')),
                    btc_avg_buy_price=settings_data.get(
                        'btc_avg_buy_price',
                        Decimal('0')),
                    robinhood_enabled=bool(
                        settings_data.get(
                            'robinhood_enabled',
                            False)),
                    robinhood_username=settings_data.get('robinhood_username'),
                    robinhood_password=settings_data.get('robinhood_password'),
                    robinhood_mfa=settings_data.get('robinhood_mfa'),
                    auto_sync=settings_data.get(
                        'auto_sync',
                        True),
                    sync_interval=settings_data.get(
                        'sync_interval',
                        600))
            except Exception as e:
                self.logger.error(
                    f"Error creating PortfolioSettings: {
                        str(e)}")
                return self.handle_error(
                    ValueError(f"Invalid settings data: {str(e)}"),
                    "update_portfolio_settings"
                )

            # Update settings in repository
            self.logger.debug("Updating settings in repository...")
            settings_dict = settings.model_dump(
                exclude={'id', 'created_at', 'updated_at'})

            result = await self.portfolio_repository.update_portfolio_settings(
                user_id, settings_dict)

            if not result:
                self.logger.error("Repository update returned None")
                return self.handle_error(
                    Exception("Failed to update portfolio settings"),
                    "update_portfolio_settings")

            # Prepare response data (use frontend keys for cash)
            response_data = {
                # This maps to total_portfolio_cash in DB
                "total_portfolio_cash": float(result.portfolio_cash),
                "total_portfolio_btc": float(result.total_portfolio_btc),
                "btc_avg_buy_price": float(result.btc_avg_buy_price),
                "robinhood_enabled": result.robinhood_enabled,
                "robinhood_username": result.robinhood_username,
                "robinhood_password": result.robinhood_password,
                "robinhood_mfa": result.robinhood_mfa,
                "auto_sync": result.auto_sync,
                "sync_interval": result.sync_interval,
                "updated_at": result.updated_at.isoformat() if result.updated_at else None
            }

            self.logger.info(
                f"Settings updated successfully for user: {user_id}")
            return {
                "success": True,
                "data": response_data
            }
        except Exception as e:
            self.logger.error(f"Error in update_portfolio_settings: {str(e)}")
            self.logger.exception(e)  # Log full traceback
            return self.handle_error(e, "update_portfolio_settings")

    # Position CRUD operations
    async def create_position(
            self, user_id: str, position_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new position."""
        try:
            # Convert frontend data to PositionCreate format
            position_create = PositionCreate(
                symbol=position_data.get('symbol'),
                quantity=Decimal(str(position_data.get('amount', 0))),
                buy_price=Decimal(str(position_data.get('avg_buy_price', 0))),
                is_crypto=position_data.get('is_crypto', False),
                source=position_data.get('source', 'manual'),
                notes=position_data.get('notes')
            )

            # Validate and create position
            result = await self.portfolio_repository.create_position(user_id, position_create)
            if not result:
                return self.handle_error(
                    Exception("Failed to create position"),
                    "create_position")

            # Convert back to frontend format for response
            return {
                "success": True,
                "data": result.to_frontend_dict()
            }
        except Exception as e:
            return self.handle_error(e, "create_position")

    async def update_position(self, position_id: str,
                              position_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing position."""
        try:
            # Convert frontend data to PositionUpdate format
            position_update = PositionUpdate(
                quantity=Decimal(str(position_data.get('amount', 0))) if 'amount' in position_data else None,
                buy_price=Decimal(str(position_data.get('avg_buy_price', 0))) if 'avg_buy_price' in position_data else None,
                market_value=Decimal(str(position_data.get('market_value', 0))) if 'market_value' in position_data else None,
                current_price=Decimal(str(position_data.get('current_price', 0))) if 'current_price' in position_data else None,
                notes=position_data.get('notes')
            )

            # Validate and update position
            result = await self.portfolio_repository.update_position(position_id, position_update)
            if not result:
                return self.handle_error(
                    Exception("Failed to update position"),
                    "update_position")

            # Convert back to frontend format for response
            return {
                "success": True,
                "data": result.to_frontend_dict()
            }
        except Exception as e:
            return self.handle_error(e, "update_position")

    async def delete_position(self, position_id: str) -> Dict[str, Any]:
        """Delete a position."""
        try:
            self.log_operation("delete_position", {"position_id": position_id})

            success = await self.portfolio_repository.delete_position(position_id)

            if not success:
                return self.handle_error(
                    Exception("Failed to delete position"),
                    "delete_position")

            return {
                "success": True,
                "data": {"message": "Position deleted successfully"}
            }
        except Exception as e:
            return self.handle_error(e, "delete_position")

    # Symbol operations
    async def search_symbols(self, query: str) -> Dict[str, Any]:
        """Search for symbols."""
        try:
            self.log_operation("search_symbols", {"query": query})

            # For now, return a simple mock response
            # This should be implemented with actual symbol search logic
            symbols = [
                {"symbol": "AAPL", "name": "Apple Inc."},
                {"symbol": "GOOGL", "name": "Alphabet Inc."},
                {"symbol": "MSFT", "name": "Microsoft Corporation"},
                {"symbol": "TSLA", "name": "Tesla Inc."},
                {"symbol": "NVDA", "name": "NVIDIA Corporation"}
            ]

            # Filter by query
            filtered_symbols = [s for s in symbols if query.upper(
            ) in s["symbol"].upper() or query.upper() in s["name"].upper()]

            return {
                "success": True,
                "data": filtered_symbols
            }
        except Exception as e:
            return self.handle_error(e, "search_symbols")

    async def get_latest_price(self, symbol: str) -> Dict[str, Any]:
        """Get latest price for a symbol."""
        try:
            self.log_operation("get_latest_price", {"symbol": symbol})

            # Get price from market data service
            price_data = await self.market_data_service.get_latest_price(symbol)

            return {
                "success": True,
                "data": {
                    "symbol": symbol,
                    "price": price_data.get("price"),
                    "timestamp": price_data.get("timestamp")
                }
            }
        except Exception as e:
            return self.handle_error(e, "get_latest_price")

    # Portfolio management operations
    async def get_portfolio_cash(self, user_id: str) -> Dict[str, Any]:
        """Get portfolio cash for a user."""
        try:
            self.log_operation("get_portfolio_cash", {"user_id": user_id})

            settings = await self.portfolio_repository.get_portfolio_settings(user_id)
            if not settings:
                # Create default settings for new users
                settings = await self.portfolio_repository.create_portfolio_settings(
                    user_id, Decimal('0')
                )
                if not settings:
                    return self.handle_error(
                        Exception("Failed to create default portfolio settings"),
                        "get_portfolio_cash")

            return {
                "success": True,
                "data": {
                    "cash": float(settings.portfolio_cash)
                }
            }
        except Exception as e:
            return self.handle_error(e, "get_portfolio_cash")

    async def set_portfolio_cash(
            self, user_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Set portfolio cash for a user."""
        try:
            self.log_operation("set_portfolio_cash", {"user_id": user_id})

            cash_amount = Decimal(str(data.get("cash", 0)))
            settings_data = {"portfolio_cash": cash_amount}

            settings = await self.portfolio_repository.update_portfolio_settings(
                user_id, settings_data)

            if not settings:
                return self.handle_error(
                    Exception("Failed to update portfolio cash"),
                    "set_portfolio_cash")

            return {
                "success": True,
                "data": {
                    "cash": float(settings.portfolio_cash)
                }
            }
        except Exception as e:
            return self.handle_error(e, "set_portfolio_cash")

    async def get_portfolio_btc(self, user_id: str) -> Dict[str, Any]:
        """Get portfolio BTC for a user."""
        try:
            self.log_operation("get_portfolio_btc", {"user_id": user_id})

            # For now, return default values since BTC fields are not in the
            # current model
            return {
                "success": True,
                "data": {
                    "btc_amount": 0.0,
                    "btc_value": 0.0,
                    "btc_avg_price": 0.0
                }
            }
        except Exception as e:
            return self.handle_error(e, "get_portfolio_btc")

    async def set_portfolio_btc(
            self, user_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Set portfolio BTC for a user."""
        try:
            self.log_operation("set_portfolio_btc", {"user_id": user_id})

            # For now, return success since BTC fields are not in the current
            # model
            return {
                "success": True,
                "data": {
                    "message": "BTC settings updated successfully"
                }
            }
        except Exception as e:
            return self.handle_error(e, "set_portfolio_btc")

    async def refresh_symbol_data(self, user_id: str) -> Dict[str, Any]:
        """Refresh symbol data for a user's portfolio."""
        try:
            self.log_operation("refresh_symbol_data", {"user_id": user_id})

            # Get user's positions to get symbols
            positions = await self.portfolio_repository.get_user_positions(user_id)
            symbols = [pos.symbol for pos in positions if pos.symbol != 'CASH']

            if symbols:
                # Refresh market data for positions
                await self.market_data_service.refresh_symbols(symbols)

            return {
                "success": True,
                "data": {
                    "message": f"Refreshed data for {len(symbols)} symbols",
                    "symbols": symbols
                }
            }
        except Exception as e:
            return self.handle_error(e, "refresh_symbol_data")
