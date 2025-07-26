"""
Models package for consistent data management across the application.
Provides unified interfaces for reading, writing, and managing data using PocketBase.
"""

from .model_manager import ModelManager, get_model_manager, shutdown_model_manager

__all__ = [
    'ModelManager',
    'get_model_manager',
    'shutdown_model_manager'
]
