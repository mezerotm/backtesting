import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Polygon API configuration
POLYGON_API_KEY = os.getenv('POLYGON_API_KEY')
if not POLYGON_API_KEY:
    raise ValueError("POLYGON_API_KEY environment variable is not set") 