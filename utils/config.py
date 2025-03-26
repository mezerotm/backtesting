import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Environment configuration
ENV = os.getenv('ENV', 'development').lower()  # Default to development if not set
IS_PRODUCTION = ENV == 'production'

# Polygon API configuration
POLYGON_API_KEY = os.getenv('POLYGON_API_KEY')
if not POLYGON_API_KEY:
    raise ValueError("POLYGON_API_KEY environment variable is not set")

# OpenAI API configuration
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
if not OPENAI_API_KEY:
    print("Warning: OPENAI_API_KEY environment variable is not set. AI explanations will not be available.")

# AI explanations configuration
ENABLE_AI_EXPLANATIONS = IS_PRODUCTION and OPENAI_API_KEY is not None
if not ENABLE_AI_EXPLANATIONS and IS_PRODUCTION and OPENAI_API_KEY:
    print("Note: AI explanations are disabled in non-production environments.") 