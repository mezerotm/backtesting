import pandas as pd
from typing import Dict
from datetime import datetime
import logging
from .base_fetcher import BaseFetcher
from polygon import RESTClient
from config import POLYGON_API_KEY

logger = logging.getLogger(__name__)

class FinancialDataFetcher(BaseFetcher):
    """Fetcher for financial analysis workflow data"""
    
    def __init__(self, force_refresh: bool = False):
        super().__init__(force_refresh, cache_subdir='financial')
        self.client = RESTClient(POLYGON_API_KEY)
    
    def fetch_financial_statements(self, symbol: str, years: int) -> Dict:
        """Fetch financial statements from Polygon"""
        # Implementation moved from data_fetcher.py
    
    def fetch_key_metrics(self, symbol: str) -> Dict:
        """Fetch key company metrics"""
        # Implementation moved from data_fetcher.py 