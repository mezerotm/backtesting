#!/usr/bin/env python3
"""
Database initialization script for PocketBase.
Sets up collections and initial data structure.

IMPORTANT NOTES:
- This script MUST be run from the project root directory
- The Python path is set up to allow imports from utils/
- If you get "ModuleNotFoundError: No module named 'utils'", make sure you're running from the project root
- Use: python utils/db_init.py or make db-init from the project root
"""

from utils.pocketbase_client import PocketBaseClient
import requests
import logging
import sys
import os
import json

# CRITICAL: Add the project root to Python path BEFORE any utils imports
project_root = os.path.join(os.path.dirname(__file__), '..')
sys.path.insert(0, project_root)

# Now import after path is set

# Verify we're in the right directory structure


def verify_project_structure():
    """Verify that we're running from the correct project structure."""
    current_dir = os.getcwd()
    utils_dir = os.path.join(current_dir, 'utils')
    server_dir = os.path.join(current_dir, 'server')

    if not os.path.exists(utils_dir) or not os.path.exists(server_dir):
        logger.error(f"""
ERROR: Incorrect directory structure detected!
Current directory: {current_dir}
Expected to find: utils/ and server/ directories

SOLUTION: Make sure you're running this script from the project root directory.
Run: cd /path/to/backtesting && python utils/db_init.py
Or use: make db-init from the project root
""")
        sys.exit(1)

    logger.info(f"Project structure verified. Running from: {current_dir}")


# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def ensure_users_collection(pb):
    """Ensure the users collection exists."""
    logger.info("Ensuring users collection exists...")

    # For initial setup, we'll assume the users collection exists
    # since PocketBase creates it automatically
    logger.info("Assuming users collection exists (created by PocketBase)")
    return True


def get_users_collection_id(pb):
    """Get the collection ID for the users collection."""
    logger.info("Getting users collection ID...")

    try:
        # Authenticate first
        if not pb.authenticate():
            logger.error(
                "Failed to authenticate for getting users collection ID")
            return None

        # List all collections to find the users collection
        response = requests.get(
            f"{pb.base_url}/api/collections",
            headers={"Authorization": f"Bearer {pb._admin_token}"},
            timeout=10
        )
        if response.status_code == 200:
            collections_data = response.json()
            collections = collections_data.get("items", [])
            logger.info(f"Found {len(collections)} collections")

            for collection in collections:
                if collection.get("name") == "users":
                    collection_id = collection.get("id")
                    logger.info(f"Found users collection ID: {collection_id}")
                    return collection_id

            logger.error("Users collection not found in collections list")
            return None
        else:
            logger.error(f"Failed to get collections: {
                         response.status_code} - {response.text}")
            return None
    except Exception as e:
        logger.error(f"Error getting users collection ID: {e}")
        return None


def create_initial_portfolio_record(pb, user_id: str):
    """Create initial portfolio record for a user if it doesn't exist."""
    logger.info(f"Creating initial portfolio record for user {user_id}...")

    try:
        # Check if portfolio record already exists for this user
        existing_records = pb.get_records("portfolio", f"user='{user_id}'")
        if existing_records:
            logger.info(f"Portfolio record already exists for user {user_id}")
            return True

        # Create initial portfolio record
        initial_data = {
            "user": user_id,
            "total_portfolio_cash": 0.0,
            "total_portfolio_btc": 0.0,
            "btc_avg_buy_price": 0.0,
            "robinhood_enabled": False,
            "robinhood_display": False,
            "robinhood_username": "",
            "robinhood_password": "",
            "robinhood_mfa": ""
        }

        if pb.create_record("portfolio", initial_data):
            logger.info(f"Created initial portfolio record for user {user_id}")
            return True
        else:
            logger.error(
                f"Failed to create initial portfolio record for user {user_id}")
            return False

    except Exception as e:
        logger.error(f"Error creating initial portfolio record: {e}")
        return False


def create_test_user(pb, email: str = "test@example.com",
                     password: str = "testpass123"):
    """Create a test user for development purposes."""
    logger.info(f"Creating test user: {email}")

    try:
        # Check if user already exists
        existing_users = pb.get_records("users", f"email='{email}'")
        if existing_users:
            user_id = existing_users[0].id
            logger.info(f"Test user already exists with ID: {user_id}")
            return user_id

        # Create test user
        user_data = {
            "email": email,
            "password": password,
            "passwordConfirm": password,
            "name": "Test User"
        }

        result = pb.create_record("users", user_data)
        if result:
            user_id = result.id
            logger.info(f"Created test user with ID: {user_id}")

            # Create initial portfolio record for this user
            create_initial_portfolio_record(pb, user_id)

            return user_id
        else:
            logger.error("Failed to create test user")
            return None

    except Exception as e:
        logger.error(f"Error creating test user: {e}")
        return None


def init_database():
    """Initialize PocketBase database with collections."""

    # Debug: Show what credentials are loaded
    from utils.config import POCKETBASE_EMAIL, POCKETBASE_PASSWORD
    logger.info(f"Loaded credentials - Email: {POCKETBASE_EMAIL}, Password: {
                '*' * len(POCKETBASE_PASSWORD) if POCKETBASE_PASSWORD else 'None'}")

    with PocketBaseClient() as pb:
        if not pb.is_server_running():
            logger.error("PocketBase server is not running")
            return False

        logger.info("Initializing PocketBase database...")

        # Ensure users collection exists
        if not ensure_users_collection(pb):
            logger.error("Failed to ensure users collection exists")
            return False

        # Get the users collection ID for relations
        users_collection_id = get_users_collection_id(pb)
        if not users_collection_id:
            logger.error("Failed to get users collection ID")
            return False

        # Import collection schemas from data models
        from server.models.data_models import get_collection_schemas
        collections = get_collection_schemas()

        # Update collection IDs to use the correct users collection ID
        for collection_name, fields in collections.items():
            for field_name, field_config in fields.items():
                if field_config.get("type") == "relation" and field_config.get(
                        "options", {}).get("collectionId") == "users":
                    field_config["options"]["collectionId"] = users_collection_id

        # Create or recreate collections with proper fields
        created_count = 0

        # Special handling for profit_loss collection to ensure nonZero is
        # False
        if "profit_loss" in collections:
            logger.info("🔧 Special handling for profit_loss collection...")
            profit_loss_fields = collections["profit_loss"]
            logger.info(
                f"Profit loss amount field config: {
                    profit_loss_fields.get(
                        'amount', {})}")

            # Always recreate profit_loss collection to ensure proper schema
            if pb.collection_exists("profit_loss"):
                logger.info(
                    "🔄 Force recreating profit_loss collection to fix nonZero constraint...")
                if pb.recreate_collection("profit_loss", profit_loss_fields):
                    logger.info(
                        "✅ Successfully recreated profit_loss collection with nonZero=False")
                    created_count += 1
                else:
                    logger.error("❌ Failed to recreate profit_loss collection")
                    return False
            else:
                logger.info(
                    "🆕 Creating new profit_loss collection with nonZero=False...")
                if pb.create_collection("profit_loss", profit_loss_fields):
                    logger.info(
                        "✅ Successfully created profit_loss collection with nonZero=False")
                    created_count += 1
                else:
                    logger.error("❌ Failed to create profit_loss collection")
                    return False

        # Handle other collections
        for collection_name, fields in collections.items():
            if collection_name == "profit_loss":
                continue  # Already handled above

            if pb.collection_exists(collection_name):
                logger.info(
                    f"🔄 Recreating collection with proper fields: {collection_name}")
                if pb.recreate_collection(collection_name, fields):
                    logger.info(f"✅ Recreated collection: {collection_name}")
                    created_count += 1
                else:
                    logger.error(
                        f"❌ Failed to recreate collection: {collection_name}")
            else:
                if pb.create_collection(collection_name, fields):
                    logger.info(f"✅ Created collection: {collection_name}")
                    created_count += 1
                else:
                    logger.error(
                        f"❌ Failed to create collection: {collection_name}")

        logger.info(f"Database initialization complete. Processed {
                    created_count} collections.")
        logger.info(
            "Note: Collections with user relations require user authentication to work properly.")
        return True


def main():
    """Main function."""
    # Verify project structure first
    verify_project_structure()

    success = init_database()

    # Optionally create a test user for development
    if success and os.getenv("CREATE_TEST_USER", "false").lower() == "true":
        with PocketBaseClient() as pb:
            if pb.is_server_running():
                create_test_user(pb)

    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
