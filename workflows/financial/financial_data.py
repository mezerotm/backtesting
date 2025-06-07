import pandas as pd
from typing import Dict, Optional
from datetime import datetime
import logging
from ..base_fetcher import BaseFetcher
from polygon import RESTClient
from config import POLYGON_API_KEY

logger = logging.getLogger(__name__)

class FinancialDataFetcher(BaseFetcher):
    """Fetcher for financial analysis workflow data"""
    
    def __init__(self, force_refresh: bool = False):
        super().__init__(force_refresh, cache_subdir='financial')
        self.client = RESTClient(POLYGON_API_KEY)
    
    def calculate_peg_ratio(self, market_cap: float, annual_financials: pd.DataFrame) -> Optional[float]:
        """Calculate PEG ratio from financial data"""
        try:
            if annual_financials.empty or len(annual_financials) < 2:
                logger.warning("Not enough annual data for PEG calculation")
                return None
                
            # Calculate P/E ratio using latest annual earnings
            latest_earnings = annual_financials.iloc[0].get('net_income', 0)
            
            if latest_earnings <= 0:
                logger.warning("Latest earnings negative or zero")
                return None
                
            pe_ratio = market_cap / (latest_earnings * 4)  # Annualize the earnings
            
            # Calculate earnings growth using last 2 years
            current_earnings = annual_financials.iloc[0].get('net_income', 0)
            prev_earnings = annual_financials.iloc[1].get('net_income', 0)
            
            if prev_earnings <= 0:
                logger.warning("Previous year earnings negative or zero")
                return None
                
            growth_rate = (current_earnings - prev_earnings) / prev_earnings
            
            # Calculate and validate PEG
            if growth_rate > 0:
                peg_ratio = pe_ratio / growth_rate
                # Validate PEG is within reasonable range
                if 0 < peg_ratio <= 100:
                    return peg_ratio
                    
            return None
            
        except Exception as e:
            logger.error(f"Error calculating PEG ratio: {e}", exc_info=True)
            return None
    
    def fetch_financial_statements(self, symbol: str, years: int) -> Dict:
        """Fetch financial statements from Polygon"""
        # Implementation moved from data_fetcher.py
    
    def fetch_key_metrics(self, symbol: str) -> Dict:
        """Fetch key company metrics"""
        try:
            # Get company details
            details = self.client.get_ticker_details(symbol)
            logger.info(f"Got ticker details for {symbol}")
            
            # Get latest financials for PEG calculation
            financials = self.fetch_financial_statements(symbol, 2)  # We need 2 years for growth calc
            annual_financials = financials.get('annual_financials', pd.DataFrame())
            
            # Calculate market cap
            ticker = self.client.get_ticker(symbol)
            market_cap = ticker.market_cap if hasattr(ticker, 'market_cap') else None
            
            # Calculate PEG ratio
            peg_ratio = None
            if market_cap and not annual_financials.empty:
                peg_ratio = self.calculate_peg_ratio(market_cap, annual_financials)
            
            fundamentals = {
                'market_cap': market_cap,
                'weighted_shares': details.weighted_shares_outstanding if hasattr(details, 'weighted_shares_outstanding') else None,
                'float': details.share_class_shares_outstanding if hasattr(details, 'share_class_shares_outstanding') else None,
                'employees': details.total_employees if hasattr(details, 'total_employees') else None,
                'sector': details.sector if hasattr(details, 'sector') else 'N/A',
                'peg_ratio': peg_ratio
            }
            
            return {
                'name': details.name if hasattr(details, 'name') else 'N/A',
                'sector': details.sector if hasattr(details, 'sector') else 'N/A',
                'description': details.description if hasattr(details, 'description') else 'N/A',
                'exchange': details.primary_exchange if hasattr(details, 'primary_exchange') else 'N/A',
                'logo_url': details.branding.logo_url if hasattr(details, 'branding') else None,
                'employees': details.total_employees if hasattr(details, 'total_employees') else None,
                'fundamentals': fundamentals
            }
            
        except Exception as e:
            logger.error(f"Error fetching key metrics for {symbol}: {e}", exc_info=True)
            return {
                'name': 'N/A',
                'sector': 'N/A',
                'description': 'N/A',
                'exchange': 'N/A',
                'logo_url': None,
                'employees': None,
                'fundamentals': {}
            } 