import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from .env file in config/shared/
env_path = Path(__file__).parent.parent / 'shared' / '.env'
load_dotenv(env_path)

# Environment configuration
# Default to development if not set
ENV = os.getenv('ENV', 'development').lower()
IS_PRODUCTION = ENV == 'production'
DEV_MODE = not IS_PRODUCTION  # Development mode is the opposite of production

# Polygon API configuration
POLYGON_API_KEY = os.getenv('POLYGON_API_KEY')
if not POLYGON_API_KEY:
    print("Warning: POLYGON_API_KEY environment variable is not set. Market data will not be available.")

# FRED API configuration
FRED_API_KEY = os.getenv('FRED_API_KEY')
if not FRED_API_KEY:
    print("Warning: FRED_API_KEY environment variable is not set. Interest rate data will use fallback values.")

# Trading Economics API configuration
TRADING_ECON_API_KEY = os.getenv('TRADING_ECON_API_KEY')
if not TRADING_ECON_API_KEY:
    print("Warning: TRADING_ECON_API_KEY environment variable is not set. Economic calendar data will not be available.")

# OpenAI API configuration
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
if not OPENAI_API_KEY:
    print("Warning: OPENAI_API_KEY environment variable is not set. AI explanations will not be available.")

# AI explanations configuration
ENABLE_AI_EXPLANATIONS = IS_PRODUCTION and OPENAI_API_KEY is not None
if not ENABLE_AI_EXPLANATIONS and IS_PRODUCTION and OPENAI_API_KEY:
    print("Note: AI explanations are disabled in non-production environments.")

# PocketBase configuration
POCKETBASE_EMAIL = os.getenv('PB_EMAIL')
POCKETBASE_PASSWORD = os.getenv('PB_PASSWORD')

if not POCKETBASE_EMAIL or not POCKETBASE_PASSWORD:
    print("Warning: PB_EMAIL and/or PB_PASSWORD environment variables are not set.")
    print("Database operations may require manual authentication.")

# Frontend configuration
VITE_API_URL = os.getenv('VITE_API_URL', 'http://localhost:8000')
