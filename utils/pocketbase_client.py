"""
PocketBase client for database operations using the official Python SDK.
"""

import os
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import subprocess
import time
import requests
from pocketbase import PocketBase
from utils.config import POCKETBASE_EMAIL, POCKETBASE_PASSWORD
from utils.logger import get_server_logger


class PocketBaseClient:
    """Client for PocketBase database operations using the official SDK."""

    def __init__(
            self,
            pb_binary_path: str = "libs/pocketbase",
            pb_data_dir: str = "pb_data",
            port: int = 8090):
        """
        Initialize PocketBase client.

        Args:
            pb_binary_path: Path to PocketBase binary
            pb_data_dir: Directory for PocketBase data
            port: Port for PocketBase server
        """
        self.pb_binary_path = pb_binary_path
        self.pb_data_dir = pb_data_dir
        self.port = port
        self.base_url = f"http://127.0.0.1:{port}"
        self.logger = get_server_logger("pocketbase")
        self.process = None
        self.is_running = False

        # Initialize PocketBase SDK client
        self.client = PocketBase(self.base_url)

        # Initialize admin token
        self._admin_token = None

        # Ensure data directory exists
        os.makedirs(pb_data_dir, exist_ok=True)

    def _serialize_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Serialize data to ensure it's JSON-compatible, handling datetime objects and invalid values."""
        if not data:
            return data

        serialized = {}
        for key, value in data.items():
            if isinstance(value, datetime):
                serialized[key] = value.isoformat()
            elif isinstance(value, dict):
                serialized[key] = self._serialize_data(value)
            elif isinstance(value, list):
                serialized[key] = [
                    self._serialize_data(item) if isinstance(
                        item, dict) else item for item in value]
            elif value is None:
                # Handle None values - convert to appropriate defaults based on
                # field type
                if key in [
                    'amount',
                    'quantity',
                    'price',
                    'buy_price',
                    'pl',
                        'fees']:
                    serialized[key] = 0.0
                else:
                    serialized[key] = ""
            elif isinstance(value, (int, float)):
                # Handle invalid numbers (NaN, inf)
                if isinstance(
                        value, float) and (
                        value != value or value == float('inf') or value == float('-inf')):
                    if key in [
                        'amount',
                        'quantity',
                        'price',
                        'buy_price',
                        'pl',
                            'fees']:
                        serialized[key] = 0.0
                    else:
                        serialized[key] = 0
                else:
                    serialized[key] = value
            else:
                serialized[key] = value

        return serialized

    def start_server(self) -> bool:
        """Start PocketBase server."""
        if self.is_running:
            return True

        try:
            # Check if binary exists
            if not os.path.exists(self.pb_binary_path):
                self.logger.error(
                    f"PocketBase binary not found at {
                        self.pb_binary_path}")
                return False

            # Start PocketBase server
            cmd = [
                self.pb_binary_path,
                "serve",
                f"--http=127.0.0.1:{self.port}",
                f"--dir={self.pb_data_dir}"
            ]

            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # Wait for server to start
            for _ in range(30):  # Wait up to 30 seconds
                try:
                    response = requests.get(
                        f"{self.base_url}/api/health", timeout=1)
                    if response.status_code == 200:
                        self.is_running = True
                        self.logger.info(
                            f"PocketBase server started on port {
                                self.port}")
                        return True
                except requests.RequestException:
                    pass
                time.sleep(1)

            self.logger.error("Failed to start PocketBase server")
            return False

        except Exception as e:
            self.logger.error(f"Error starting PocketBase server: {e}")
            return False

    def stop_server(self) -> bool:
        """Stop PocketBase server."""
        if self.process:
            self.process.terminate()
            self.process.wait()
            self.process = None
            self.is_running = False
            self.logger.info("PocketBase server stopped")
            return True
        return False

    def is_server_running(self) -> bool:
        """Check if PocketBase server is running."""
        try:
            response = requests.get(f"{self.base_url}/api/health", timeout=1)
            if response.status_code == 200:
                self.is_running = True
                return True
            else:
                self.is_running = False
                return False
        except requests.RequestException:
            self.is_running = False
            return False

    def authenticate(self) -> bool:
        """Authenticate with PocketBase using admin credentials."""
        if not self.is_server_running():
            return False

        if not POCKETBASE_EMAIL or not POCKETBASE_PASSWORD:
            self.logger.warning(
                "PocketBase credentials not provided, skipping authentication")
            return False

        try:
            # Use direct REST API for admin authentication
            auth_data = {
                "identity": POCKETBASE_EMAIL,
                "password": POCKETBASE_PASSWORD
            }

            response = requests.post(
                f"{self.base_url}/api/admins/auth-with-password",
                json=auth_data,
                timeout=10
            )

            if response.status_code == 200:
                auth_result = response.json()
                if auth_result.get("token"):
                    # Store the token for later use
                    self._admin_token = auth_result["token"]

                    # Skip SDK authentication for now - use REST API only
                    # The SDK has compatibility issues with PocketBase v0.18.5
                    self.logger.info(
                        "Using REST API authentication only (SDK auth skipped for compatibility)")

                    self.logger.info(
                        "Successfully authenticated with PocketBase")
                    return True
                else:
                    self.logger.error(
                        "Authentication failed: no token in response")
                    return False
            else:
                self.logger.error(f"Authentication failed: {
                                  response.status_code} - {response.text}")
                return False
        except Exception as e:
            self.logger.error(f"Error during authentication: {e}")
            return False

    def authenticate_user(
            self, email: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate a user with email and password."""
        if not self.is_server_running():
            return None

        try:
            auth_data = {
                "identity": email,
                "password": password
            }

            response = requests.post(
                f"{self.base_url}/api/collections/users/auth-with-password",
                json=auth_data,
                timeout=10
            )

            if response.status_code == 200:
                auth_result = response.json()
                if auth_result.get("token"):
                    self.logger.info(
                        f"User {email} authenticated successfully")
                    record = auth_result.get("record", {})
                    return {
                        "token": auth_result["token"],
                        "user_id": record.get("id"),
                        "name": record.get(
                            "name",
                            record.get(
                                "username",
                                email))}
                else:
                    self.logger.error(
                        "User authentication failed: no token in response")
                    return None
            else:
                self.logger.error(f"User authentication failed: {
                                  response.status_code} - {response.text}")
                return None
        except Exception as e:
            self.logger.error(f"Error during user authentication: {e}")
            return None

    def register_user(self, email: str, password: str,
                      name: str) -> Optional[Dict[str, Any]]:
        """Register a new user account."""
        if not self.is_server_running():
            return None

        try:
            user_data = {
                "email": email,
                "password": password,
                "passwordConfirm": password,
                "name": name
            }

            response = requests.post(
                f"{self.base_url}/api/collections/users/records",
                json=user_data,
                timeout=10
            )

            if response.status_code == 201:
                user_result = response.json()
                self.logger.info(f"User {email} registered successfully")
                return {
                    "user_id": user_result.get("id"),
                    "email": user_result.get("email"),
                    "name": user_result.get(
                        "name",
                        user_result.get(
                            "username",
                            name))}
            else:
                self.logger.error(f"User registration failed: {
                                  response.status_code} - {response.text}")
                return None
        except Exception as e:
            self.logger.error(f"Error during user registration: {e}")
            return None

    def collection_exists(self, name: str) -> bool:
        """Check if a collection exists."""
        if not self.is_server_running():
            return False

        try:
            # Try to authenticate first
            if not self.authenticate():
                self.logger.warning(
                    "Failed to authenticate for collection check")
                return False

            # Try to get the collection using REST API with authentication
            headers = {"Authorization": f"Bearer {self._admin_token}"}
            response = requests.get(
                f"{self.base_url}/api/collections/{name}",
                headers=headers,
                timeout=5)
            return response.status_code == 200
        except Exception as e:
            self.logger.warning(
                f"Error checking if collection {name} exists: {e}")
            return False

    def flatten_fields_to_schema(
            self, fields_dict: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Convert fields dictionary to PocketBase schema format.

        Args:
            fields_dict: Dictionary of field definitions

        Returns:
            List of field definitions in PocketBase schema format
        """
        schema = []
        for name, field in fields_dict.items():
            field_def = {
                "name": name,
                "type": field["type"],
                "required": field.get("required", False),
                "unique": field.get("unique", False),
                "options": field.get("options", {})
            }
            schema.append(field_def)
        return schema

    def create_collection(self, name: str, fields: Dict[str, Any]) -> bool:
        """Create a new collection in PocketBase using REST API."""
        if not self.is_server_running():
            return False

        try:
            # Try to authenticate first, but don't fail if it doesn't work
            token = None
            try:
                # Try to use stored token first
                if hasattr(self, '_admin_token') and self._admin_token:
                    token = self._admin_token
                    self.logger.info(
                        "Using stored admin token for collection creation")
                else:
                    # Authenticate to get a new token
                    auth_data = {
                        "identity": POCKETBASE_EMAIL,
                        "password": POCKETBASE_PASSWORD
                    }

                    auth_response = requests.post(
                        f"{self.base_url}/api/admins/auth-with-password",
                        json=auth_data,
                        timeout=10
                    )

                    if auth_response.status_code == 200:
                        auth_result = auth_response.json()
                        token = auth_result.get("token")
                        if token:
                            self._admin_token = token
                            self.logger.info(
                                "Using authenticated admin token for collection creation")
                        else:
                            self.logger.warning(
                                "Admin authentication failed: no token received")
                    else:
                        self.logger.warning(f"Admin authentication failed: {
                                            auth_response.status_code} - {auth_response.text}")
            except Exception as e:
                self.logger.warning(f"Admin authentication failed: {e}")

            # Convert our field definitions to PocketBase field format
            pb_fields = []
            for field_name, field_config in fields.items():
                field_type = field_config.get("type", "text")
                required = field_config.get("required", False)

                # Create field definition based on type with proper PocketBase
                # format
                if field_type == "text":
                    field_def = {
                        "name": field_name,
                        "type": "text",
                        "required": required,
                        "unique": False,
                        "options": {
                            "min": None,
                            "max": None,
                            "pattern": ""
                        }
                    }
                elif field_type == "number":
                    # Use custom options if provided, otherwise use defaults
                    custom_options = field_config.get("options", {})
                    field_def = {
                        "name": field_name,
                        "type": "number",
                        "required": required,
                        "unique": False,
                        "options": {
                            "min": custom_options.get("min", None),
                            "max": custom_options.get("max", None),
                            # Default to True, but allow override
                            "nonZero": custom_options.get("nonZero", True)
                        }
                    }
                elif field_type == "bool":
                    field_def = {
                        "name": field_name,
                        "type": "bool",
                        "required": required,
                        "unique": False,
                        "options": {}
                    }
                elif field_type == "relation":
                    # Handle relation fields
                    options = field_config.get("options", {})
                    collection_id = options.get("collectionId", "")
                    self.logger.info(f"Creating relation field '{
                                     field_name}' with collectionId: '{collection_id}'")
                    field_def = {
                        "name": field_name,
                        "type": "relation",
                        "required": required,
                        "unique": False,
                        "options": {
                            "collectionId": collection_id,
                            "cascadeDelete": options.get("cascadeDelete", False),
                            # Default to 1 for single relation
                            "maxSelect": options.get("maxSelect", 1),
                            "displayFields": options.get("displayFields", ["username", "email"])
                        }
                    }
                else:
                    # Default to text
                    field_def = {
                        "name": field_name,
                        "type": "text",
                        "required": required,
                        "unique": False,
                        "options": {
                            "min": None,
                            "max": None,
                            "pattern": ""
                        }
                    }

                pb_fields.append(field_def)

            # Check if we have fields to create
            if not pb_fields:
                self.logger.warning(
                    f"No valid fields to create for collection: {name}")
                return False

            # Create collection using REST API
            collection_payload = {
                "name": name,
                "type": "base",
                "schema": pb_fields,
                "listRule": "",
                "viewRule": "",
                "createRule": "",
                "updateRule": ""
            }

            # Debug: Log the payload for relation fields
            if any(field.get("type") == "relation" for field in pb_fields):
                self.logger.info(f"Collection payload for {
                                 name}: {collection_payload}")

            # Special debugging for profit_loss collection
            if name == "profit_loss":
                self.logger.info(f"🔧 PROFIT_LOSS COLLECTION CREATION:")
                self.logger.info(f"Collection name: {name}")
                self.logger.info(f"Full payload: {collection_payload}")
                # Find the amount field and log its configuration
                for field in pb_fields:
                    if field.get("name") == "amount":
                        self.logger.info(f"Amount field config: {field}")
                        self.logger.info(
                            f"Amount field options: {
                                field.get(
                                    'options', {})}")
                        self.logger.info(
                            f"Amount field nonZero setting: {
                                field.get(
                                    'options', {}).get(
                                    'nonZero', 'NOT_SET')}")
                        break

            headers = {
                "Content-Type": "application/json"
            }
            if token:
                headers["Authorization"] = f"Bearer {token}"

            response = requests.post(
                f"{self.base_url}/api/collections",
                json=collection_payload,
                headers=headers,
                timeout=10
            )

            if response.status_code in [200, 201]:
                self.logger.info(f"Successfully created collection: {name}")
                # Log the response to see what was actually created
                try:
                    response_data = response.json()
                    self.logger.info(f"Collection response: {response_data}")
                except BaseException:
                    pass
                return True
            else:
                self.logger.error(f"Failed to create collection {name}: {
                                  response.status_code} - {response.text}")
                return False
        except Exception as e:
            self.logger.error(f"Error creating collection {name}: {e}")
            return False

    def delete_collection(self, name: str) -> bool:
        """Delete a collection from PocketBase using REST API."""
        if not self.is_server_running():
            return False

        try:
            # Try to authenticate first, but don't fail if it doesn't work
            token = None
            try:
                # Try to use stored token first
                if hasattr(self, '_admin_token') and self._admin_token:
                    token = self._admin_token
                    self.logger.info(
                        "Using stored admin token for collection deletion")
                else:
                    # Authenticate to get a new token
                    auth_data = {
                        "identity": POCKETBASE_EMAIL,
                        "password": POCKETBASE_PASSWORD
                    }

                    auth_response = requests.post(
                        f"{self.base_url}/api/admins/auth-with-password",
                        json=auth_data,
                        timeout=10
                    )

                    if auth_response.status_code == 200:
                        auth_result = auth_response.json()
                        token = auth_result.get("token")
                        if token:
                            self._admin_token = token
                            self.logger.info(
                                "Using authenticated admin token for collection deletion")
                        else:
                            self.logger.warning(
                                "Admin authentication failed: no token received")
                    else:
                        self.logger.warning(f"Admin authentication failed: {
                                            auth_response.status_code} - {auth_response.text}")
            except Exception as e:
                self.logger.warning(f"Admin authentication failed: {e}")

            headers = {
                "Content-Type": "application/json"
            }
            if token:
                headers["Authorization"] = f"Bearer {token}"

            response = requests.delete(
                f"{self.base_url}/api/collections/{name}",
                headers=headers,
                timeout=10
            )

            if response.status_code == 204:
                self.logger.info(f"Successfully deleted collection: {name}")
                return True
            else:
                self.logger.error(f"Failed to delete collection {name}: {
                                  response.status_code} - {response.text}")
                return False
        except Exception as e:
            self.logger.error(f"Error deleting collection {name}: {e}")
            return False

    def recreate_collection(self, name: str, fields: Dict[str, Any]) -> bool:
        """Delete and recreate a collection with new schema."""
        if not self.is_server_running():
            return False

        try:
            # Delete existing collection if it exists
            if self.collection_exists(name):
                self.delete_collection(name)

            # Create new collection
            return self.create_collection(name, fields)
        except Exception as e:
            self.logger.error(f"Error recreating collection {name}: {e}")
            return False

    def get_records(self, collection: str,
                    filters: str = "") -> List[Dict[str, Any]]:
        """Get records from a collection using REST API."""
        if not self.is_server_running():
            return []

        try:
            headers = {}
            if hasattr(self, '_admin_token') and self._admin_token:
                headers["Authorization"] = f"Bearer {self._admin_token}"

            url = f"{self.base_url}/api/collections/{collection}/records"
            if filters:
                import urllib.parse
                encoded_filter = urllib.parse.quote(filters)
                url += f"?filter={encoded_filter}"

            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                result = response.json()
                return result.get("items", [])
            else:
                self.logger.error(f"Failed to get records from {collection}: {
                                  response.status_code} - {response.text}")
                return []
        except Exception as e:
            self.logger.error(f"Error getting records from {collection}: {e}")
            return []

    def create_record(self, collection: str,
                      data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new record in a collection using REST API."""
        if not self.is_server_running():
            return None

        try:
            # Serialize data to handle datetime objects
            serialized_data = self._serialize_data(data)

            # CRITICAL: Log exactly what we're sending for profit_loss
            if collection == "profit_loss":
                self.logger.debug(f"PROFIT_LOSS SEND: Raw data: {data}")
                self.logger.debug(
                    f"PROFIT_LOSS SEND: Serialized data: {serialized_data}")
                self.logger.debug(
                    f"PROFIT_LOSS SEND: Amount in raw: {
                        data.get('amount')}")
                self.logger.debug(
                    f"PROFIT_LOSS SEND: Amount in serialized: {
                        serialized_data.get('amount')}")
                self.logger.debug(
                    f"PROFIT_LOSS SEND: All keys in serialized: {
                        list(
                            serialized_data.keys())}")

            self.logger.debug(f"Sending data to PocketBase: {serialized_data}")

            # Debug: Check for None or invalid values before sending
            for key, value in serialized_data.items():
                if value is None:
                    self.logger.warning(
                        f"Found None value for key '{key}' in {collection}")
                elif isinstance(value, float) and (value != value or value == float('inf') or value == float('-inf')):
                    self.logger.warning(f"Found invalid number for key '{
                                        key}': {value} in {collection}")

            headers = {
                "Content-Type": "application/json"
            }
            if hasattr(self, '_admin_token') and self._admin_token:
                headers["Authorization"] = f"Bearer {self._admin_token}"

            response = requests.post(
                f"{self.base_url}/api/collections/{collection}/records",
                json=serialized_data,
                headers=headers,
                timeout=10
            )

            if response.status_code in [200, 201]:
                result = response.json()
                self.logger.info(
                    f"Successfully created record in {collection}")
                return result
            else:
                self.logger.error(f"Failed to create record in {collection}: {
                                  response.status_code} - {response.text}")
                return None
        except Exception as e:
            self.logger.error(f"Error creating record in {collection}: {e}")
            return None

    def update_record(self, collection: str, record_id: str,
                      data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update a record in a collection using REST API."""
        if not self.is_server_running():
            return None

        try:
            # Serialize data to handle datetime objects
            serialized_data = self._serialize_data(data)

            headers = {
                "Content-Type": "application/json"
            }
            if hasattr(self, '_admin_token') and self._admin_token:
                headers["Authorization"] = f"Bearer {self._admin_token}"

            response = requests.patch(
                f"{self.base_url}/api/collections/{collection}/records/{record_id}",
                json=serialized_data,
                headers=headers,
                timeout=10
            )

            if response.status_code == 200:
                result = response.json()
                self.logger.info(f"Successfully updated record {
                                 record_id} in {collection}")
                return result
            else:
                self.logger.error(f"Failed to update record {record_id} in {
                                  collection}: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            self.logger.error(f"Error updating record {
                              record_id} in {collection}: {e}")
            return None

    def delete_record(self, collection: str, record_id: str) -> bool:
        """Delete a record from a collection using REST API."""
        if not self.is_server_running():
            return False

        try:
            headers = {}
            if hasattr(self, '_admin_token') and self._admin_token:
                headers["Authorization"] = f"Bearer {self._admin_token}"

            response = requests.delete(
                f"{self.base_url}/api/collections/{collection}/records/{record_id}",
                headers=headers,
                timeout=10
            )

            if response.status_code == 204:
                self.logger.info(f"Successfully deleted record {
                                 record_id} from {collection}")
                return True
            else:
                self.logger.error(f"Failed to delete record {record_id} from {
                                  collection}: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            self.logger.error(f"Error deleting record {
                              record_id} from {collection}: {e}")
            return False

    def __enter__(self):
        """Context manager entry."""
        self.start_server()
        if self.is_server_running():
            self.authenticate()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop_server()
