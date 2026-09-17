"""
Portfolio repository for database operations.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from server.database.models.portfolio import (
    Position, Portfolio, PortfolioSettings, PositionCreate, PositionUpdate
)
from server.database.connection import db_connection
from config.backend.logger import get_api_logger


class PortfolioRepository:
    """Repository for portfolio-related database operations."""

    def __init__(self):
        self.logger = get_api_logger(__name__)
        self.pb_client = db_connection.get_pocketbase_client()

    # Position operations
    async def create_position(
            self,
            user_id: str,
            position_data: PositionCreate) -> Optional[Position]:
        """Create a new position."""
        try:
            data = {
                "user": user_id,  # Changed from user_id to user
                "symbol": position_data.symbol,
                "quantity": str(position_data.quantity),
                # Changed from cost_basis
                "buy_price": str(position_data.buy_price),
                "is_crypto": position_data.is_crypto,
                "source": position_data.source,
                "notes": position_data.notes,
                "pulled_at": datetime.now().isoformat()  # Use pulled_at instead of created_at
            }

            result = await self.pb_client.create_position(data)
            if result:
                # Map back to Position model
                mapped_data = {
                    "id": result.get("id"),
                    "user": result.get("user"),
                    "symbol": result.get("symbol"),
                    "quantity": Decimal(str(result.get("quantity", 0))),
                    "buy_price": Decimal(str(result.get("buy_price", 0))),
                    "is_crypto": result.get("is_crypto", False),
                    "source": result.get("source", "manual"),
                    "notes": result.get("notes"),
                    "pulled_at": result.get("pulled_at"),
                    "updated_at": datetime.fromisoformat(result.get("updated", datetime.now().isoformat())) if result.get("updated") else None
                }
                return Position(**mapped_data)
            return None
        except Exception as e:
            self.logger.error(f"Error creating position: {e}")
            return None

    async def get_position_by_id(self, position_id: str) -> Optional[Position]:
        """Get position by ID."""
        try:
            result = await self.pb_client.get_position_by_id(position_id)
            return Position(**result) if result else None
        except Exception as e:
            self.logger.error(f"Error getting position by ID: {e}")
            return None

    async def get_user_positions(self, user_id: str) -> List[Position]:
        """Get all positions for a user."""
        try:
            results = await self.pb_client.get_user_positions(user_id)
            positions = []
            for pos in results:
                # Map database fields to Position model
                mapped_data = {
                    "id": pos.get("id"),
                    "user": pos.get("user"),  # Keep as 'user' to match DB
                    "symbol": pos.get("symbol"),
                    "quantity": Decimal(str(pos.get("quantity", 0))),
                    # Map buy_price
                    "buy_price": Decimal(str(pos.get("buy_price", 0))),
                    "market_value": Decimal(str(pos.get("market_value", 0))) if pos.get("market_value") else None,
                    "current_price": Decimal(str(pos.get("current_price", 0))) if pos.get("current_price") else None,
                    "total_return": Decimal(str(pos.get("total_return", 0))) if pos.get("total_return") else None,
                    "total_return_percent": Decimal(str(pos.get("total_return_percent", 0))) if pos.get("total_return_percent") else None,
                    "is_crypto": pos.get("is_crypto", False),
                    "source": pos.get("source", "manual"),
                    "notes": pos.get("notes"),
                    # Map pulled_at instead of created_at
                    "pulled_at": pos.get("pulled_at"),
                    "updated_at": datetime.fromisoformat(pos.get("updated", datetime.now().isoformat())) if pos.get("updated") else None
                }
                positions.append(Position(**mapped_data))
            return positions
        except Exception as e:
            self.logger.error(f"Error getting user positions: {e}")
            return []

    async def update_position(
            self,
            position_id: str,
            position_data: PositionUpdate) -> Optional[Position]:
        """Update a position."""
        try:
            update_data = position_data.dict(exclude_unset=True)
            if update_data:
                # Convert Decimal to string for storage
                for key, value in update_data.items():
                    if isinstance(value, Decimal):
                        update_data[key] = str(value)

                update_data["updated_at"] = datetime.now().isoformat()
                result = await self.pb_client.update_position(position_id, update_data)
                return Position(**result) if result else None
            return None
        except Exception as e:
            self.logger.error(f"Error updating position: {e}")
            return None

    async def delete_position(self, position_id: str) -> bool:
        """Delete a position."""
        try:
            await self.pb_client.delete_position(position_id)
            return True
        except Exception as e:
            self.logger.error(f"Error deleting position: {e}")
            return False

    # Portfolio settings operations
    async def get_portfolio_settings(
            self, user_id: str) -> Optional[PortfolioSettings]:
        """Get portfolio settings for a user."""
        try:
            result = await self.pb_client.get_portfolio_settings(user_id)
            if result:
                # Map database fields to PortfolioSettings model
                mapped_data = {
                    "id": result.get("id"),
                    "user_id": result.get("user"),  # Database field is 'user'
                    # Database field is 'total_portfolio_cash'
                    "portfolio_cash": Decimal(str(result.get("total_portfolio_cash", 0))),
                    "total_portfolio_btc": Decimal(str(result.get("total_portfolio_btc", 0))),
                    "btc_avg_buy_price": Decimal(str(result.get("btc_avg_buy_price", 0))),
                    "robinhood_enabled": result.get("robinhood_enabled", False),
                    "robinhood_username": result.get("robinhood_username", ""),
                    "robinhood_password": result.get("robinhood_password", ""),
                    "robinhood_mfa": result.get("robinhood_mfa", ""),
                    "auto_sync": result.get("auto_sync", True),
                    "sync_interval": result.get("sync_interval", 600),
                    "created_at": datetime.fromisoformat(result.get("created", datetime.now().isoformat())),
                    "updated_at": datetime.fromisoformat(result.get("updated", datetime.now().isoformat())) if result.get("updated") else None
                }
                return PortfolioSettings(**mapped_data)
            return None
        except Exception as e:
            self.logger.error(f"Error getting portfolio settings: {e}")
            return None

    async def create_portfolio_settings(
            self,
            user_id: str,
            portfolio_cash: Decimal) -> Optional[PortfolioSettings]:
        """Create portfolio settings for a user."""
        try:
            data = {
                "user": user_id,  # Database field is 'user'
                # Database field is 'total_portfolio_cash'
                "total_portfolio_cash": str(portfolio_cash),
                "total_portfolio_btc": "0",
                "btc_avg_buy_price": "0",
                "robinhood_enabled": False,
                "robinhood_username": "",
                "robinhood_password": "",
                "robinhood_mfa": "",
                "auto_sync": True,
                "sync_interval": 600,
                "created_at": datetime.now().isoformat()
            }

            result = await self.pb_client.create_portfolio_settings(data)
            if result:
                # Map database fields to PortfolioSettings model
                mapped_data = {
                    "id": result.get("id"),
                    "user_id": result.get("user"),  # Database field is 'user'
                    # Database field is 'total_portfolio_cash'
                    "portfolio_cash": Decimal(str(result.get("total_portfolio_cash", 0))),
                    "total_portfolio_btc": Decimal(str(result.get("total_portfolio_btc", 0))),
                    "btc_avg_buy_price": Decimal(str(result.get("btc_avg_buy_price", 0))),
                    "robinhood_enabled": result.get("robinhood_enabled", False),
                    "robinhood_username": result.get("robinhood_username", ""),
                    "robinhood_password": result.get("robinhood_password", ""),
                    "robinhood_mfa": result.get("robinhood_mfa", ""),
                    "auto_sync": result.get("auto_sync", True),
                    "sync_interval": result.get("sync_interval", 600),
                    "created_at": datetime.fromisoformat(result.get("created", datetime.now().isoformat())),
                    "updated_at": datetime.fromisoformat(result.get("updated", datetime.now().isoformat())) if result.get("updated") else None
                }
                return PortfolioSettings(**mapped_data)
            return None
        except Exception as e:
            self.logger.error(f"Error creating portfolio settings: {e}")
            return None

    async def update_portfolio_settings(
            self,
            user_id: str,
            settings_data: Dict[str, Any]) -> Optional[PortfolioSettings]:
        """Update portfolio settings for a user."""
        try:
            self.logger.info(f"Updating portfolio settings - User: {user_id}")
            self.logger.debug(f"Received settings data: {settings_data}")

            # The data should already be in the correct format from the service
            # layer
            data = {
                **settings_data,
                "updated_at": datetime.now().isoformat()
            }
            self.logger.debug(f"Prepared data for database: {data}")

            # Get existing record or create new one
            self.logger.debug("Checking for existing settings...")
            existing = await self.pb_client.get_portfolio_settings(user_id)

            if not existing:
                self.logger.debug(
                    "No existing settings found, creating new record")
                # Create new settings record
                # Required for new records (database field is 'user')
                data["user"] = user_id
                data["created_at"] = datetime.now().isoformat()
                result = await self.pb_client.create_portfolio_settings(data)
                self.logger.debug(f"Created new settings: {result}")
            else:
                self.logger.debug(f"Found existing settings: {existing}")
                # Update existing record
                result = await self.pb_client.update_portfolio_settings(user_id, data)
                self.logger.debug(f"Updated settings: {result}")

            if not result:
                self.logger.error("PocketBase operation returned None")
                return None

            self.logger.debug(
                "Converting PocketBase record to PortfolioSettings model")
            try:
                settings = PortfolioSettings(
                    id=result.get("id"),
                    user_id=user_id,
                    # Database field is 'total_portfolio_cash'
                    portfolio_cash=Decimal(
                        str(result.get("total_portfolio_cash", 0))),
                    total_portfolio_btc=Decimal(
                        str(result.get("total_portfolio_btc", 0))),
                    btc_avg_buy_price=Decimal(
                        str(result.get("btc_avg_buy_price", 0))),
                    robinhood_enabled=result.get("robinhood_enabled", False),
                    robinhood_username=result.get("robinhood_username", ""),
                    robinhood_password=result.get("robinhood_password", ""),
                    robinhood_mfa=result.get("robinhood_mfa", ""),
                    auto_sync=result.get("auto_sync", True),
                    sync_interval=result.get("sync_interval", 600),
                    created_at=datetime.fromisoformat(
                        result.get("created", datetime.now().isoformat())),
                    updated_at=datetime.fromisoformat(
                        result.get(
                            "updated",
                            datetime.now().isoformat())) if result.get("updated") else None
                )
                self.logger.debug(
                    f"Successfully created PortfolioSettings model: {settings.model_dump()}")
                return settings
            except Exception as e:
                self.logger.error(
                    f"Error creating PortfolioSettings model: {str(e)}")
                raise

        except Exception as e:
            self.logger.error(f"Error updating portfolio settings: {str(e)}")
            return None

    async def update_or_create_portfolio_settings(
            self, user_id: str, settings_data: Dict[str, Any]) -> Optional[PortfolioSettings]:
        """Update or create portfolio settings."""
        try:
            existing = await self.get_portfolio_settings(user_id)
            if existing:
                return await self.update_portfolio_settings(user_id, settings_data)
            else:
                return await self.create_portfolio_settings(user_id, Decimal(settings_data["portfolio_cash"]))
        except Exception as e:
            self.logger.error(
                f"Error updating/creating portfolio settings: {e}")
            return None
