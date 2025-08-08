"""
Database layer for data access and management.
This layer provides abstraction over PocketBase and other data sources.
"""

from .connection import DatabaseConnection
from .models import *
from .repositories import *

__all__ = [
    'DatabaseConnection',
]
