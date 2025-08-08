"""
Robinhood repository for database operations.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from server.database.models.robinhood import (
    RobinhoodCredentials, RobinhoodPosition, RobinhoodOrder,
    RobinhoodCredentialsCreate, RobinhoodCredentialsUpdate
)
from server.database.connection import db_connection
from config.backend.logger import get_api_logger


class RobinhoodRepository:
    """Repository for Robinhood-related database operations."""

    def __init__(self):
        self.logger = get_api_logger(__name__)
        self.pb_client = db_connection.get_pocketbase_client()

    # Credentials operations
    async def create_credentials(
            self,
            user_id: str,
            credentials: RobinhoodCredentialsCreate) -> Optional[RobinhoodCredentials]:
        """Create Robinhood credentials for a user."""
        try:
            data = {
                "user_id": user_id,
                "access_token": credentials.access_token,
                "refresh_token": credentials.refresh_token,
                "token_type": credentials.token_type,
                "expires_at": credentials.expires_at.isoformat(),
                "scope": credentials.scope,
                "is_active": True,
                "sync_status": "idle",
                "created_at": datetime.now().isoformat()
            }

            result = await self.pb_client.create_robinhood_credentials(data)
            return RobinhoodCredentials(**result) if result else None
        except Exception as e:
            self.logger.error(f"Error creating Robinhood credentials: {e}")
            return None

    async def get_credentials_by_user_id(
            self, user_id: str) -> Optional[RobinhoodCredentials]:
        """Get Robinhood credentials for a user."""
        try:
            result = await self.pb_client.get_robinhood_credentials_by_user_id(user_id)
            return RobinhoodCredentials(**result) if result else None
        except Exception as e:
            self.logger.error(f"Error getting Robinhood credentials: {e}")
            return None

    async def update_credentials(
            self,
            user_id: str,
            credentials: RobinhoodCredentialsUpdate) -> Optional[RobinhoodCredentials]:
        """Update Robinhood credentials for a user."""
        try:
            update_data = credentials.dict(exclude_unset=True)
            if update_data:
                # Convert datetime to string
                if "expires_at" in update_data:
                    update_data["expires_at"] = update_data["expires_at"].isoformat()

                update_data["updated_at"] = datetime.now().isoformat()
                result = await self.pb_client.update_robinhood_credentials(user_id, update_data)
                return RobinhoodCredentials(**result) if result else None
            return None
        except Exception as e:
            self.logger.error(f"Error updating Robinhood credentials: {e}")
            return None

    async def delete_credentials(self, user_id: str) -> bool:
        """Delete Robinhood credentials for a user."""
        try:
            await self.pb_client.delete_robinhood_credentials(user_id)
            return True
        except Exception as e:
            self.logger.error(f"Error deleting Robinhood credentials: {e}")
            return False

    # Position operations
    async def create_robinhood_position(
            self, user_id: str, position_data: Dict[str, Any]) -> Optional[RobinhoodPosition]:
        """Create a Robinhood position."""
        try:
            data = {
                "user_id": user_id,
                "robinhood_id": position_data["id"],
                "symbol": position_data["symbol"],
                "quantity": position_data["quantity"],
                "cost_basis": position_data["cost_basis"],
                "average_buy_price": position_data["average_buy_price"],
                "instrument_id": position_data["instrument_id"],
                "instrument_url": position_data["instrument_url"],
                "is_crypto": position_data.get("is_crypto", False),
                "created_at": datetime.now().isoformat()
            }

            result = await self.pb_client.create_robinhood_position(data)
            return RobinhoodPosition(**result) if result else None
        except Exception as e:
            self.logger.error(f"Error creating Robinhood position: {e}")
            return None

    async def get_robinhood_positions(
            self, user_id: str) -> List[RobinhoodPosition]:
        """Get all Robinhood positions for a user."""
        try:
            results = await self.pb_client.get_robinhood_positions(user_id)
            return [RobinhoodPosition(**pos)
                    for pos in results] if results else []
        except Exception as e:
            self.logger.error(f"Error getting Robinhood positions: {e}")
            return []

    async def update_robinhood_position(self,
                                        position_id: str,
                                        position_data: Dict[str,
                                                            Any]) -> Optional[RobinhoodPosition]:
        """Update a Robinhood position."""
        try:
            update_data = {
                "quantity": position_data["quantity"],
                "cost_basis": position_data["cost_basis"],
                "average_buy_price": position_data["average_buy_price"],
                "updated_at": datetime.now().isoformat()
            }

            result = await self.pb_client.update_robinhood_position(position_id, update_data)
            return RobinhoodPosition(**result) if result else None
        except Exception as e:
            self.logger.error(f"Error updating Robinhood position: {e}")
            return None

    async def delete_robinhood_position(self, position_id: str) -> bool:
        """Delete a Robinhood position."""
        try:
            await self.pb_client.delete_robinhood_position(position_id)
            return True
        except Exception as e:
            self.logger.error(f"Error deleting Robinhood position: {e}")
            return False

    # Order operations
    async def create_robinhood_order(
            self, user_id: str, order_data: Dict[str, Any]) -> Optional[RobinhoodOrder]:
        """Create a Robinhood order."""
        try:
            data = {
                "user_id": user_id,
                "robinhood_id": order_data["id"],
                "symbol": order_data["symbol"],
                "side": order_data["side"],
                "quantity": order_data["quantity"],
                "price": order_data["price"],
                "state": order_data["state"],
                "type": order_data["type"],
                "time_in_force": order_data["time_in_force"],
                "created_at": datetime.now().isoformat()
            }

            result = await self.pb_client.create_robinhood_order(data)
            return RobinhoodOrder(**result) if result else None
        except Exception as e:
            self.logger.error(f"Error creating Robinhood order: {e}")
            return None

    async def get_robinhood_orders(self, user_id: str) -> List[RobinhoodOrder]:
        """Get all Robinhood orders for a user."""
        try:
            results = await self.pb_client.get_robinhood_orders(user_id)
            return [RobinhoodOrder(**order)
                    for order in results] if results else []
        except Exception as e:
            self.logger.error(f"Error getting Robinhood orders: {e}")
            return []

    async def update_robinhood_order(
            self, order_id: str, order_data: Dict[str, Any]) -> Optional[RobinhoodOrder]:
        """Update a Robinhood order."""
        try:
            update_data = {
                "state": order_data["state"],
                "updated_at": datetime.now().isoformat()
            }

            result = await self.pb_client.update_robinhood_order(order_id, update_data)
            return RobinhoodOrder(**result) if result else None
        except Exception as e:
            self.logger.error(f"Error updating Robinhood order: {e}")
            return None
