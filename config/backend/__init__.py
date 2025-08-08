"""
Backend configuration package.
"""

from .settings import *
from .logger import (
    get_app_logger,
    get_server_logger,
    get_widget_logger,
    get_api_logger,
    get_data_validation_logger,
    cleanup_old_logs,
    cleanup_large_logs,
    get_log_stats,
    auto_cleanup_logs,
    list_log_files
)

__all__ = [
    # Settings
    'ENV',
    'IS_PRODUCTION',
    'POLYGON_API_KEY',
    'FRED_API_KEY',
    'TRADING_ECON_API_KEY',
    'OPENAI_API_KEY',
    'ENABLE_AI_EXPLANATIONS',
    'POCKETBASE_EMAIL',
    'POCKETBASE_PASSWORD',
    'VITE_API_URL',

    # Logging
    'get_app_logger',
    'get_server_logger',
    'get_widget_logger',
    'get_api_logger',
    'get_data_validation_logger',
    'cleanup_old_logs',
    'cleanup_large_logs',
    'get_log_stats',
    'auto_cleanup_logs',
    'list_log_files'
]
