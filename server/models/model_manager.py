"""
Model manager providing unified access to all data models.
Handles PocketBase integration for database operations.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
from server.database.pocketbase_client import PocketBaseClient
from config.backend.logger import get_api_logger, get_data_validation_logger


class ModelManager:
    """Manager for all data models with PocketBase integration."""

    def __init__(self):
        """Initialize the model manager."""
        self.logger = get_api_logger("model_manager")
        self.validation_logger = get_data_validation_logger("model_manager")
        self.logger.info("Initializing ModelManager...")

        # Initialize PocketBase client
        self.logger.debug("Creating PocketBase client...")
        self.pb_client = PocketBaseClient()

        # Check if PocketBase is already running, if not start it
        if not self.pb_client.is_server_running():
            self.logger.info("PocketBase server not running, starting it...")
            if not self.pb_client.start_server():
                self.logger.error("Failed to start PocketBase server")
                raise RuntimeError("PocketBase server could not be started")
            self.logger.info("PocketBase server started successfully")
        else:
            self.logger.info("PocketBase server is already running")

        # Authenticate with PocketBase
        self.logger.debug("Attempting to authenticate with PocketBase...")
        if not self.pb_client.authenticate():
            self.logger.warning(
                "Failed to authenticate with PocketBase, some operations may fail")
        else:
            self.logger.info("Successfully authenticated with PocketBase")

        self.logger.info("ModelManager initialization complete")

    def get_portfolio_data(self, user_id: str) -> Dict[str, Any]:
        """Get portfolio data from PocketBase for a specific user."""
        self.logger.info(
            f"Getting portfolio data for user {user_id} from PocketBase...")
        try:
            records = self.pb_client.get_records(
                "portfolio", f"user='{user_id}'")
            self.logger.info(
                f"Retrieved {len(records)} portfolio records for user {user_id} from PocketBase")

            if records:
                # Handle both Record objects (from SDK) and dictionaries (from
                # REST API)
                if hasattr(records[0], '__dict__'):
                    # SDK Record object
                    portfolio_data = vars(records[0])
                else:
                    # REST API dictionary
                    portfolio_data = records[0]
                self.logger.debug(
                    f"Portfolio data keys: {list(portfolio_data.keys())}")
                return portfolio_data
            else:
                self.logger.warning(
                    f"No portfolio records found in PocketBase for user {user_id}")
                return {}
        except Exception as e:
            self.logger.error(f"Error getting portfolio data: {e}")
            return {}

    def update_portfolio_data(
            self, user_id: str, data: Dict[str, Any]) -> bool:
        """Update portfolio data in PocketBase for a specific user."""
        self.logger.info(
            f"Updating portfolio data for user {user_id} in PocketBase...")
        self.logger.debug(
            f"Update data keys: {list(data.keys()) if data else 'None'}")

        try:
            # Get portfolio record for specific user
            records = self.pb_client.get_records(
                "portfolio", f"user='{user_id}'")
            if records:
                # Handle both Record objects (from SDK) and dictionaries (from
                # REST API)
                if hasattr(records[0], '__dict__'):
                    # SDK Record object
                    record_dict = vars(records[0])
                else:
                    # REST API dictionary
                    record_dict = records[0]
                record_id = record_dict["id"]
                result = self.pb_client.update_record(
                    "portfolio", record_id, data) is not None
                self.logger.info(
                    f"Updated portfolio record for user {user_id}: {result}")
                return result
            else:
                # Create new portfolio record for user
                if data:
                    data["user"] = user_id
                result = self.pb_client.create_record(
                    "portfolio", data) is not None
                self.logger.info(
                    f"Created portfolio record for user {user_id}: {result}")
                return result
        except Exception as e:
            self.logger.error(f"Error updating portfolio data: {e}")
            return False

    def get_positions(
            self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get positions from PocketBase, optionally filtered by user ID."""
        self.logger.info("Getting positions from PocketBase...")
        self.logger.debug(f"PocketBase client: {self.pb_client}")
        self.logger.debug(
            f"PocketBase server running: {self.pb_client.is_server_running()}")
        self.logger.debug(f"PocketBase base URL: {self.pb_client.base_url}")

        try:
            if user_id:
                # Filter by user ID
                records = self.pb_client.get_records(
                    "positions", f"user='{user_id}'")
                self.logger.info(
                    f"Retrieved {len(records)} positions for user {user_id} from PocketBase")
            else:
                # Get all positions
                records = self.pb_client.get_records("positions")
                self.logger.info(
                    f"Retrieved {len(records)} positions from PocketBase")

            if records:
                # Handle both Record objects (from SDK) and dictionaries (from
                # REST API)
                if hasattr(records[0], '__dict__'):
                    # SDK Record objects
                    positions = [vars(record) for record in records]
                else:
                    # REST API dictionaries
                    positions = records
                self.logger.debug(
                    f"First position keys: {list(positions[0].keys())}")
                return positions
            else:
                if user_id:
                    self.logger.warning(
                        f"No positions found in PocketBase for user {user_id}")
                else:
                    self.logger.warning("No positions found in PocketBase")
                return []
        except Exception as e:
            self.logger.error(f"Error getting positions: {e}")
            return []

    def add_position(self, position: Dict[str, Any]) -> bool:
        """Add a new position to PocketBase."""
        self.logger.info("Adding new position to PocketBase...")
        self.logger.debug(f"Position data keys: {list(position.keys())}")

        try:
            result = self.pb_client.create_record(
                "positions", position) is not None
            self.logger.info(f"Position added successfully: {result}")
            return result
        except Exception as e:
            self.logger.error(f"Error adding position: {e}")
            return False

    def update_position(self, position_id: str, data: Dict[str, Any]) -> bool:
        """Update a position in PocketBase."""
        self.logger.info(f"Updating position {position_id} in PocketBase...")
        self.logger.debug(f"Update data keys: {list(data.keys())}")

        try:
            result = self.pb_client.update_record(
                "positions", position_id, data) is not None
            self.logger.info(f"Position updated successfully: {result}")
            return result
        except Exception as e:
            self.logger.error(f"Error updating position {position_id}: {e}")
            return False

    def delete_position(self, position_id: str) -> bool:
        """Delete a position from PocketBase."""
        self.logger.info(f"Deleting position {position_id} from PocketBase...")

        try:
            result = self.pb_client.delete_record("positions", position_id)
            self.logger.info(f"Position deleted successfully: {result}")
            return result
        except Exception as e:
            self.logger.error(f"Error deleting position {position_id}: {e}")
            return False

    def get_orders(
            self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get orders from PocketBase, optionally filtered by user ID."""
        self.logger.info("Getting orders from PocketBase...")

        try:
            if user_id:
                # Filter by user ID
                records = self.pb_client.get_records(
                    "orders", f"user='{user_id}'")
                self.logger.info(
                    f"Retrieved {len(records)} orders for user {user_id} from PocketBase")
            else:
                # Get all orders
                records = self.pb_client.get_records("orders")
                self.logger.info(
                    f"Retrieved {len(records)} orders from PocketBase")

            if records:
                # Handle both Record objects (from SDK) and dictionaries (from
                # REST API)
                if hasattr(records[0], '__dict__'):
                    # SDK Record objects
                    orders = [vars(record) for record in records]
                else:
                    # REST API dictionaries
                    orders = records
                self.logger.debug(
                    f"First order keys: {list(orders[0].keys())}")
                return orders
            else:
                if user_id:
                    self.logger.warning(
                        f"No orders found in PocketBase for user {user_id}")
                else:
                    self.logger.warning("No orders found in PocketBase")
                return []
        except Exception as e:
            self.logger.error(f"Error getting orders: {e}")
            return []

    def add_orders(self, orders: List[Dict[str, Any]]) -> bool:
        """Add multiple orders to PocketBase."""
        self.logger.info(f"Adding {len(orders)} orders to PocketBase...")

        try:
            success_count = 0
            for i, order in enumerate(orders):
                if self.pb_client.create_record("orders", order):
                    success_count += 1
                    self.logger.debug(
                        f"Order {i + 1}/{len(orders)} added successfully")
                else:
                    self.logger.warning(
                        f"Failed to add order {i + 1}/{len(orders)}")

            self.logger.info(
                f"Orders added: {success_count}/{len(orders)} successful")
            return success_count == len(orders)
        except Exception as e:
            self.logger.error(f"Error adding orders: {e}")
            return False

    def get_dividends(
            self, user_id: Optional[str] = None,
            limit: Optional[int] = None,
            offset: Optional[int] = None,
            sort: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get dividends from PocketBase, optionally filtered by user ID and paginated."""
        self.logger.info("Getting dividends from PocketBase...")

        try:
            if user_id:
                # Filter by user ID
                records = self.pb_client.get_records(
                    "dividends", f"user='{user_id}'",
                    limit=limit, skip=offset, sort=sort)
                self.logger.info(
                    f"Retrieved {len(records)} dividends for user {user_id} from PocketBase (limit={limit}, offset={offset})")
            else:
                # Get all dividends
                records = self.pb_client.get_records(
                    "dividends", limit=limit, skip=offset, sort=sort)
                self.logger.info(
                    f"Retrieved {len(records)} dividends from PocketBase (limit={limit}, offset={offset})")

            if records:
                # Handle both Record objects (from SDK) and dictionaries (from
                # REST API)
                if hasattr(records[0], '__dict__'):
                    # SDK Record objects
                    dividends = [vars(record) for record in records]
                else:
                    # REST API dictionaries
                    dividends = records
                self.logger.debug(
                    f"First dividend keys: {list(dividends[0].keys())}")
                return dividends
            else:
                if user_id:
                    self.logger.warning(
                        f"No dividends found in PocketBase for user {user_id}")
                else:
                    self.logger.warning("No dividends found in PocketBase")
                return []
        except Exception as e:
            self.logger.error(f"Error getting dividends: {e}")
            return []

    def add_dividends(self, dividends: List[Dict[str, Any]]) -> bool:
        """Add multiple dividends to PocketBase."""
        self.logger.info(f"Adding {len(dividends)} dividends to PocketBase...")

        try:
            success_count = 0
            for i, dividend in enumerate(dividends):
                if self.pb_client.create_record("dividends", dividend):
                    success_count += 1
                    self.logger.debug(
                        f"Dividend {i + 1}/{len(dividends)} added successfully")
                else:
                    self.logger.warning(
                        f"Failed to add dividend {i + 1}/{len(dividends)}")

            self.logger.info(
                f"Dividends added: {success_count}/{len(dividends)} successful")
            return success_count == len(dividends)
        except Exception as e:
            self.logger.error(f"Error adding dividends: {e}")
            return False

    def get_symbol_cache(self) -> List[Dict[str, Any]]:
        """Get symbol cache data from PocketBase."""
        self.logger.info("Getting symbol cache from PocketBase...")

        try:
            records = self.pb_client.get_records("symbol_cache")
            self.logger.info(
                f"Retrieved {len(records)} symbol cache records from PocketBase")
            if records:
                # Handle both Record objects (from SDK) and dictionaries (from
                # REST API)
                if hasattr(records[0], '__dict__'):
                    # SDK Record objects
                    symbol_cache = [vars(record) for record in records]
                else:
                    # REST API dictionaries
                    symbol_cache = records
                self.logger.debug(
                    f"First symbol cache keys: {list(symbol_cache[0].keys())}")
                return symbol_cache
            else:
                self.logger.warning(
                    "No symbol cache records found in PocketBase")
                return []
        except Exception as e:
            self.logger.error(f"Error getting symbol cache: {e}")
            return []

    def update_symbol_cache(self, symbol: str, data: Dict[str, Any]) -> bool:
        """Update symbol cache data in PocketBase."""
        self.logger.info(f"Updating symbol cache for symbol: {symbol}")
        self.logger.debug(f"Cache data keys: {list(data.keys())}")

        try:
            # Check if record exists
            records = self.pb_client.get_records(
                "symbol_cache", f"symbol='{symbol}'")
            if records:
                # Handle both Record objects (from SDK) and dictionaries (from
                # REST API)
                if hasattr(records[0], '__dict__'):
                    # SDK Record object
                    record_dict = vars(records[0])
                else:
                    # REST API dictionary
                    record_dict = records[0]
                record_id = record_dict["id"]
                result = self.pb_client.update_record(
                    "symbol_cache", record_id, data) is not None
                self.logger.info(
                    f"Updated symbol cache record for {symbol}: {result}")
                return result
            else:
                data["symbol"] = symbol
                result = self.pb_client.create_record(
                    "symbol_cache", data) is not None
                self.logger.info(
                    f"Symbol cache created for {symbol}: {result}")
                return result
        except Exception as e:
            self.logger.error(f"Error updating symbol cache for {symbol}: {e}")
            return False

    def upsert_symbol_cache_records(
            self, symbol_data_list: List[Dict[str, Any]]) -> Dict[str, int]:
        """Upsert multiple symbol cache records in PocketBase with deduplication before save."""
        self.logger.info(
            f"Upserting {len(symbol_data_list)} symbol cache records...")

        if not symbol_data_list:
            return {"created": 0, "updated": 0, "errors": 0}

        try:
            # STEP 1: Get all existing symbol cache records in one query
            existing_records = self.pb_client.get_records("symbol_cache")
            existing_by_symbol = {}

            # Group existing records by symbol and handle duplicates
            for record in existing_records:
                if hasattr(record, '__dict__'):
                    record_dict = vars(record)
                else:
                    record_dict = record

                symbol = record_dict.get('symbol')
                if symbol:
                    if symbol not in existing_by_symbol:
                        existing_by_symbol[symbol] = record_dict
                    else:
                        # Found duplicate - delete the extra one
                        self.logger.debug(
                            f"Found duplicate symbol cache record for {symbol}, deleting extra")
                        self.pb_client.delete_record(
                            "symbol_cache", record_dict['id'])

            # STEP 2: Process new data with deduplication
            created_count = 0
            updated_count = 0
            error_count = 0

            for data in symbol_data_list:
                try:
                    symbol = data.get('symbol')
                    if not symbol:
                        self.logger.warning(
                            f"Skipping record without symbol: {data}")
                        error_count += 1
                        continue

                    # STEP 3: Check if symbol exists and update/create
                    # accordingly
                    if symbol in existing_by_symbol:
                        # Update existing record
                        existing_record = existing_by_symbol[symbol]
                        if self._symbol_cache_data_changed(
                                existing_record, data):
                            if self.pb_client.update_record(
                                    "symbol_cache", existing_record['id'], data):
                                updated_count += 1
                                self.logger.debug(
                                    f"Updated symbol cache for {symbol}")
                            else:
                                error_count += 1
                                self.logger.warning(
                                    f"Failed to update symbol cache for {symbol}")
                        else:
                            self.logger.debug(
                                f"Symbol cache unchanged for {symbol}, skipping update")
                    else:
                        # Create new record
                        if self.pb_client.create_record("symbol_cache", data):
                            created_count += 1
                            self.logger.debug(
                                f"Created new symbol cache for {symbol}")
                        else:
                            error_count += 1
                            self.logger.warning(
                                f"Failed to create symbol cache for {symbol}")

                except Exception as e:
                    self.logger.error(
                        f"Error processing symbol cache record for {data.get('symbol', 'unknown')}: {e}")
                    error_count += 1

            result = {
                "created": created_count,
                "updated": updated_count,
                "errors": error_count
            }

            self.logger.info(f"Symbol cache upsert complete: {result}")
            return result

        except Exception as e:
            self.logger.error(f"Error in symbol cache upsert: {e}")
            return {
                "created": 0,
                "updated": 0,
                "errors": len(symbol_data_list)}

    def create_symbol_cache_record(self, data: Dict[str, Any]) -> bool:
        """Create a new symbol cache record in PocketBase."""
        self.logger.info(
            f"Creating symbol cache record for symbol: {data.get('symbol','unknown')}")
        self.logger.debug(f"Cache data keys: {list(data.keys())}")

        try:
            result = self.pb_client.create_record(
                "symbol_cache", data) is not None
            self.logger.info(f"Symbol cache record created: {result}")
            return result
        except Exception as e:
            self.logger.error(f"Error creating symbol cache record: {e}")
            return False

    def upsert_profit_loss_records(
            self, profit_loss_data: List[Dict[str, Any]], user_id: str) -> Dict[str, int]:
        """Upsert profit/loss records to PocketBase with duplicate prevention."""
        self.logger.info(
            f"Upserting {len(profit_loss_data)} profit/loss records for user {user_id}")
        self.validation_logger.info(
            f"Starting profit/loss upsert for user {user_id}")

        try:
            # Get existing profit/loss records for this user
            existing_records = self.get_profit_loss_records(user_id)

            # Create unique key for each existing record
            existing_by_key = {}
            for record in existing_records:
                key = self._get_profit_loss_key(record)
                existing_by_key[key] = record

            created_count = 0
            updated_count = 0
            error_count = 0

            # Process each new profit/loss record
            for record in profit_loss_data:
                try:

                    # Add user_id and calculated_at if not present
                    record["user"] = user_id
                    if "calculated_at" not in record:
                        record["calculated_at"] = datetime.now().isoformat()

                    # Generate unique key
                    key = self._get_profit_loss_key(record)

                    if key in existing_by_key:
                        # Update existing record
                        existing_record = existing_by_key[key]
                        if self._profit_loss_data_changed(
                                existing_record, record):
                            if self.pb_client.update_record(
                                    "profit_loss", existing_record['id'], record):
                                updated_count += 1
                                self.logger.debug(
                                    f"Updated profit/loss record: {key}")
                            else:
                                error_count += 1
                                self.logger.warning(
                                    f"Failed to update profit/loss record: {key}")
                        else:
                            self.logger.debug(
                                f"Profit/loss record unchanged, skipping: {key}")
                    else:
                        # Create new record
                        if self.pb_client.create_record("profit_loss", record):
                            created_count += 1
                            self.logger.debug(
                                f"Created new profit/loss record: {key}")
                        else:
                            error_count += 1
                            self.logger.warning(
                                f"Failed to create profit/loss record: {key}")

                except Exception as e:
                    self.logger.error(
                        f"Error processing profit/loss record for {record.get('symbol', 'unknown')}: {e}")
                    error_count += 1

            result = {
                'created': created_count,
                'updated': updated_count,
                'errors': error_count
            }

            self.logger.info(f"Profit/loss upsert complete: {result}")
            self.validation_logger.info(
                f"Profit/loss upsert summary: {result}")
            return result

        except Exception as e:
            self.logger.error(f"Error upserting profit/loss records: {e}")
            return {
                'created': 0,
                'updated': 0,
                'errors': len(profit_loss_data)}

    def _profit_loss_data_changed(
            self, existing: Dict[str, Any], new: Dict[str, Any]) -> bool:
        """Check if profit/loss data has changed."""
        key_fields = ['amount', 'calculated_at', 'source']
        for field in key_fields:
            if existing.get(field) != new.get(field):
                return True
        return False

    def upsert_profit_loss_cache_records(
            self, cache_data: List[Dict[str, Any]], user_id: str) -> Dict[str, int]:
        """Upsert profit/loss cache records to PocketBase with duplicate prevention."""
        self.logger.info(
            f"Upserting {len(cache_data)} profit/loss cache records for user {user_id}")
        self.validation_logger.info(
            f"Starting profit/loss cache upsert for user {user_id}")

        try:
            # Get existing profit/loss cache records for this user
            existing_records = self.pb_client.get_records(
                "profit_loss_cache", f"user='{user_id}'")

            # Create unique key for each existing record (user + period)
            existing_by_key = {}
            for record in existing_records:
                key = f"{record.get('user', '')}_{record.get('period', '')}"
                existing_by_key[key] = record

            created_count = 0
            updated_count = 0
            error_count = 0

            # Process each new cache record
            for record in cache_data:
                try:
                    # Add user_id if not present
                    record["user"] = user_id

                    # Ensure all required fields are present with defaults
                    record.setdefault("realized", 0.0)
                    record.setdefault("unrealized", 0.0)
                    record.setdefault("total", 0.0)
                    record.setdefault(
                        "calculated_at", datetime.now().isoformat())
                    record.setdefault(
                        "last_updated", datetime.now().isoformat())

                    # Generate unique key
                    key = f"{record.get('user','')}_{record.get('period','')}"

                    if key in existing_by_key:
                        # Update existing record
                        existing_record = existing_by_key[key]
                        if self._profit_loss_cache_data_changed(
                                existing_record, record):
                            if self.pb_client.update_record(
                                    "profit_loss_cache", existing_record['id'], record):
                                updated_count += 1
                                self.logger.debug(
                                    f"Updated profit/loss cache record: {key}")
                            else:
                                error_count += 1
                                self.logger.warning(
                                    f"Failed to update profit/loss cache record: {key}")
                        else:
                            self.logger.debug(
                                f"Profit/loss cache record unchanged, skipping: {key}")
                    else:
                        # Create new record
                        if self.pb_client.create_record(
                                "profit_loss_cache", record):
                            created_count += 1
                            self.logger.debug(
                                f"Created new profit/loss cache record: {key}")
                        else:
                            error_count += 1
                            self.logger.warning(
                                f"Failed to create profit/loss cache record: {key}")

                except Exception as e:
                    self.logger.error(
                        f"Error processing profit/loss cache record for {record.get('period', 'unknown')}: {e}")
                    error_count += 1

            result = {
                'created': created_count,
                'updated': updated_count,
                'errors': error_count
            }

            self.logger.info(f"Profit/loss cache upsert complete: {result}")
            self.validation_logger.info(
                f"Profit/loss cache upsert summary: {result}")
            return result

        except Exception as e:
            self.logger.error(
                f"Error upserting profit/loss cache records: {e}")
            return {
                'created': 0,
                'updated': 0,
                'errors': len(cache_data)}

    def _profit_loss_cache_data_changed(
            self, existing: Dict[str, Any], new: Dict[str, Any]) -> bool:
        """Check if profit/loss cache data has changed."""
        key_fields = [
            'total',
            'unrealized',
            'realized',
            'calculated_at',
            'last_updated']
        for field in key_fields:
            if existing.get(field) != new.get(field):
                return True
        return False

    def get_profit_loss_cache_records(
            self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get profit/loss cache records from PocketBase."""
        self.logger.info(
            "Getting profit/loss cache records from PocketBase...")
        try:
            if user_id:
                records = self.pb_client.get_records(
                    "profit_loss_cache", f"user='{user_id}'")
            else:
                records = self.pb_client.get_records("profit_loss_cache")

            # Convert to list of dictionaries
            result = []
            for record in records:
                if hasattr(record, '__dict__'):
                    # SDK Record object
                    result.append(vars(record))
                else:
                    # REST API dictionary
                    result.append(record)

            self.logger.info(
                f"Retrieved {len(result)} profit/loss cache records from PocketBase")
            return result
        except Exception as e:
            self.logger.error(f"Error getting profit/loss cache records: {e}")
            return []

    def get_profit_loss_records(
            self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get profit/loss records from PocketBase."""
        self.logger.info("Getting profit/loss records from PocketBase...")

        try:
            if user_id:
                records = self.pb_client.get_records(
                    "profit_loss", f"user='{user_id}'")
            else:
                records = self.pb_client.get_records("profit_loss")

            if records:
                # Handle both Record objects (from SDK) and dictionaries (from
                # REST API)
                if hasattr(records[0], '__dict__'):
                    # SDK Record objects
                    profit_loss_records = [vars(record) for record in records]
                else:
                    # REST API dictionaries
                    profit_loss_records = records

                self.logger.info(
                    f"Retrieved {len(profit_loss_records)} profit/loss records from PocketBase")
                return profit_loss_records
            else:
                self.logger.warning(
                    "No profit/loss records found in PocketBase")
                return []
        except Exception as e:
            self.logger.error(f"Error getting profit/loss records: {e}")
            return []

    def get_system_stats(self) -> Dict[str, Any]:
        """Get system statistics."""
        self.logger.info("Getting system statistics...")

        try:
            stats = {
                "pocketbase_running": self.pb_client.is_server_running(),
                "collections": {}
            }

            # Get stats for each collection
            collections = [
                "portfolio",
                "positions",
                "orders",
                "dividends",
                "symbol_cache"]

            for collection in collections:
                records = self.pb_client.get_records(collection)
                stats["collections"][collection] = {"count": len(records)}
                self.logger.debug(
                    f"Collection {collection}: {len(records)} records")

            self.logger.info(
                f"System stats retrieved: PocketBase running={stats['pocketbase_running']}")
            return stats
        except Exception as e:
            self.logger.error(f"Error getting system stats: {e}")
            return {"error": str(e)}

    def shutdown(self):
        """Shutdown the model manager."""
        self.logger.info("Shutting down ModelManager...")
        if self.pb_client:
            self.pb_client.stop_server()
            self.logger.info("PocketBase server stopped")
        self.logger.info("ModelManager shutdown complete")

    def upsert_positions(
            self, positions: List[Dict[str, Any]], user_id: str) -> Dict[str, int]:
        """
        Upsert positions - update existing or create new ones.
        Uses symbol + user as unique identifier.

        Returns:
            Dict with counts: {'created': int, 'updated': int, 'deleted': int}
        """
        self.logger.info(
            f"Upserting {len(positions)} positions for user {user_id}...")

        try:
            # Get existing positions for this user
            existing_positions = self.get_positions(user_id)
            existing_by_symbol = {
                pos['symbol']: pos for pos in existing_positions}

            # Track what we process
            created_count = 0
            updated_count = 0
            processed_symbols = set()

            # Process each new position
            for position in positions:
                symbol = position.get('symbol')
                if not symbol:
                    self.logger.warning(
                        f"Position missing symbol, skipping: {position}")
                    continue

                processed_symbols.add(symbol)

                if symbol in existing_by_symbol:
                    # Update existing position
                    existing_pos = existing_by_symbol[symbol]
                    position_id = existing_pos['id']

                    # Only update if data has changed
                    if self._position_data_changed(existing_pos, position):
                        if self.update_position(position_id, position):
                            updated_count += 1
                            self.logger.debug(f"Updated position for {symbol}")
                        else:
                            self.logger.warning(
                                f"Failed to update position for {symbol}")
                    else:
                        self.logger.debug(
                            f"Position {symbol} unchanged, skipping update")
                else:
                    # Create new position
                    if self.add_position(position):
                        created_count += 1
                        self.logger.debug(f"Created new position for {symbol}")
                    else:
                        self.logger.warning(
                            f"Failed to create position for {symbol}")

            # Delete positions that no longer exist (removed from Robinhood)
            deleted_count = 0
            for symbol, existing_pos in existing_by_symbol.items():
                if symbol not in processed_symbols:
                    if self.delete_position(existing_pos['id']):
                        deleted_count += 1
                        self.logger.debug(
                            f"Deleted position for {symbol} (no longer exists)")
                    else:
                        self.logger.warning(
                            f"Failed to delete position for {symbol}")

            result = {
                'created': created_count,
                'updated': updated_count,
                'deleted': deleted_count
            }

            self.logger.info(f"Position upsert complete: {result}")
            return result

        except Exception as e:
            self.logger.error(f"Error upserting positions: {e}")
            return {'created': 0, 'updated': 0, 'deleted': 0}

    def upsert_orders(
            self, orders: List[Dict[str, Any]], user_id: str) -> Dict[str, int]:
        """
        Upsert orders - update existing or create new ones.
        Uses date + symbol + quantity + price as unique identifier.

        Returns:
            Dict with counts: {'created': int, 'updated': int}
        """
        self.logger.info(
            f"Upserting {len(orders)} orders for user {user_id}...")

        try:
            # Get existing orders for this user
            existing_orders = self.get_orders(user_id)

            # Create unique key for each order
            existing_by_key = {}
            for order in existing_orders:
                key = self._get_order_key(order)
                existing_by_key[key] = order

            created_count = 0
            updated_count = 0
            processed_keys = set()

            # Process each new order
            for order in orders:
                key = self._get_order_key(order)
                processed_keys.add(key)

                if key in existing_by_key:
                    # Update existing order if data changed
                    existing_order = existing_by_key[key]
                    if self._order_data_changed(existing_order, order):
                        if self.update_order(existing_order['id'], order):
                            updated_count += 1
                            self.logger.debug(f"Updated order: {key}")
                        else:
                            self.logger.warning(
                                f"Failed to update order: {key}")
                    else:
                        self.logger.debug(f"Order unchanged, skipping: {key}")
                else:
                    # Create new order
                    if self.add_order(order):
                        created_count += 1
                        self.logger.debug(f"Created new order: {key}")
                    else:
                        self.logger.warning(f"Failed to create order: {key}")

            result = {
                'created': created_count,
                'updated': updated_count
            }

            self.logger.info(f"Order upsert complete: {result}")
            return result

        except Exception as e:
            self.logger.error(f"Error upserting orders: {e}")
            return {'created': 0, 'updated': 0}

    def upsert_dividends(
            self, dividends: List[Dict[str, Any]], user_id: str) -> Dict[str, int]:
        """
        Upsert dividends - update existing or create new ones.
        Uses symbol + date + amount as unique identifier.

        Returns:
            Dict with counts: {'created': int, 'updated': int}
        """
        self.logger.info(
            f"Upserting {len(dividends)} dividends for user {user_id}...")

        try:
            # Get existing dividends for this user
            existing_dividends = self.get_dividends(user_id)

            # Create unique key for each dividend
            existing_by_key = {}
            for dividend in existing_dividends:
                key = self._get_dividend_key(dividend)
                existing_by_key[key] = dividend

            created_count = 0
            updated_count = 0

            # Process each new dividend
            for dividend in dividends:
                key = self._get_dividend_key(dividend)

                if key in existing_by_key:
                    # Update existing dividend if data changed
                    existing_dividend = existing_by_key[key]
                    if self._dividend_data_changed(
                            existing_dividend, dividend):
                        if self.update_dividend(
                                existing_dividend['id'], dividend):
                            updated_count += 1
                            self.logger.debug(f"Updated dividend: {key}")
                        else:
                            self.logger.warning(
                                f"Failed to update dividend: {key}")
                    else:
                        self.logger.debug(
                            f"Dividend unchanged, skipping: {key}")
                else:
                    # Create new dividend
                    if self.add_dividend(dividend):
                        created_count += 1
                        self.logger.debug(f"Created new dividend: {key}")
                    else:
                        self.logger.warning(
                            f"Failed to create dividend: {key}")

            result = {
                'created': created_count,
                'updated': updated_count
            }

            self.logger.info(f"Dividend upsert complete: {result}")
            return result

        except Exception as e:
            self.logger.error(f"Error upserting dividends: {e}")
            return {'created': 0, 'updated': 0}

    # Helper methods for data comparison and key generation
    def _get_order_key(self, order: Dict[str, Any]) -> str:
        """Generate unique key for order based on source_id or date, symbol, quantity, and price."""
        # Try to use source_id if available (most unique)
        source_id = order.get('source_id', '')
        if source_id:
            return f"source_{source_id}"

        # Fallback to date + symbol + quantity + price + timestamp
        date = order.get('date', '')
        symbol = order.get('symbol', '')
        quantity = str(order.get('quantity', 0))
        price = str(order.get('price', 0))
        timestamp = order.get('pulled_at', '')
        return f"{date}_{symbol}_{quantity}_{price}_{timestamp}"

    def _get_dividend_key(self, dividend: Dict[str, Any]) -> str:
        """Generate unique key for dividend based on symbol, date, amount, and timestamp."""
        symbol = dividend.get('symbol', '')
        date = dividend.get('date', '')
        amount = str(dividend.get('amount', 0))
        timestamp = dividend.get('pulled_at', '')
        return f"{symbol}_{date}_{amount}_{timestamp}"

    def _position_data_changed(
            self, existing: Dict[str, Any], new: Dict[str, Any]) -> bool:
        """Check if position data has changed."""
        key_fields = ['quantity', 'buy_price', 'notes']
        for field in key_fields:
            if existing.get(field) != new.get(field):
                return True
        return False

    def _order_data_changed(
            self, existing: Dict[str, Any], new: Dict[str, Any]) -> bool:
        """Check if order data has changed."""
        key_fields = ['quantity', 'price', 'fees', 'notes']
        for field in key_fields:
            if existing.get(field) != new.get(field):
                return True
        return False

    def _dividend_data_changed(
            self, existing: Dict[str, Any], new: Dict[str, Any]) -> bool:
        """Check if dividend data has changed."""
        key_fields = ['amount', 'date']
        for field in key_fields:
            if existing.get(field) != new.get(field):
                return True
        return False

    def _symbol_cache_data_changed(
            self, existing: Dict[str, Any], new: Dict[str, Any]) -> bool:
        """Check if symbol cache data has changed."""
        key_fields = ['price', 'date', 'beta', 'delta']
        for field in key_fields:
            if existing.get(field) != new.get(field):
                return True
        return False

    def _get_profit_loss_key(self, record: Dict[str, Any]) -> str:
        """Generate unique key for profit/loss record based on user, symbol, type, period, and date."""
        user = record.get('user', '')
        symbol = record.get('symbol', '')
        record_type = record.get('type', '')
        period = record.get('period', 'YTD')
        date = record.get('date', '')
        return f"{user}_{symbol}_{record_type}_{period}_{date}"

    # Add missing methods for individual record operations
    def add_order(self, order: Dict[str, Any]) -> bool:
        """Add a single order to PocketBase."""
        try:
            result = self.pb_client.create_record("orders", order) is not None
            return result
        except Exception as e:
            self.logger.error(f"Error adding order: {e}")
            return False

    def update_order(self, order_id: str, data: Dict[str, Any]) -> bool:
        """Update a single order in PocketBase."""
        try:
            result = self.pb_client.update_record(
                "orders", order_id, data) is not None
            return result
        except Exception as e:
            self.logger.error(f"Error updating order {order_id}: {e}")
            return False

    def add_dividend(self, dividend: Dict[str, Any]) -> bool:
        """Add a single dividend to PocketBase."""
        try:
            result = self.pb_client.create_record(
                "dividends", dividend) is not None
            return result
        except Exception as e:
            self.logger.error(f"Error adding dividend: {e}")
            return False

    def update_dividend(self, dividend_id: str, data: Dict[str, Any]) -> bool:
        """Update a single dividend in PocketBase."""
        try:
            result = self.pb_client.update_record(
                "dividends", dividend_id, data) is not None
            return result
        except Exception as e:
            self.logger.error(f"Error updating dividend {dividend_id}: {e}")
            return False


# Global model manager instance
_model_manager = None


def get_model_manager() -> ModelManager:
    """Get the global model manager instance."""
    global _model_manager
    if _model_manager is None:
        logger = get_api_logger("model_manager")
        logger.info("Creating new global ModelManager instance...")
        _model_manager = ModelManager()
        logger.info("Global ModelManager instance created")
    return _model_manager


def shutdown_model_manager():
    """Shutdown the global model manager."""
    global _model_manager
    if _model_manager:
        _model_manager.shutdown()
        _model_manager = None
        logger = get_api_logger("model_manager")
        logger.info("Global ModelManager instance shutdown")
