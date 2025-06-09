import pandas as pd
from typing import Dict, Optional
from datetime import datetime
import logging
from ..base_fetcher import BaseFetcher
from polygon import RESTClient
from utils.config import POLYGON_API_KEY
import time
import requests

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
    
    def _fetch_polygon_financials(self, symbol: str, period: str, limit: int) -> pd.DataFrame:
        """
        Internal method to fetch financial statements from Polygon.io
        
        Args:
            symbol: Stock symbol
            period: 'quarterly' or 'annual'
            limit: Number of periods to fetch
            
        Returns:
            DataFrame with financial data
        """
        try:
            # Add delay to avoid rate limiting
            time.sleep(0.2)  # Polygon allows 5 requests per second
            
            # Try using the client library first
            try:
                logger.info(f"Attempting to fetch {period} financials for {symbol} using client library")
                financials = self.client.list_financials(
                    ticker=symbol,
                    period=period,
                    limit=limit
                )
                
                if not financials:
                    logger.warning(f"No financial data found for {symbol}")
                    return pd.DataFrame()
                
                logger.info(f"Successfully fetched {len(financials)} {period} financial records for {symbol}")
                
                # Convert to DataFrame with required columns
                df = pd.DataFrame([{
                    'date': datetime.fromtimestamp(f.filing_date/1000).strftime('%Y-%m-%d'),
                    'fiscal_period': f.fiscal_period,
                    'fiscal_year': f.fiscal_year,
                    'total_assets': f.total_assets,
                    'current_assets': f.current_assets,
                    'current_liabilities': f.current_liabilities,
                    'inventory': f.inventory,
                    'liabilities': f.total_liabilities,
                    'revenue': f.revenue,
                    'net_income': f.net_income,
                    'eps': f.eps,
                    'total_equity': f.total_equity,
                    'operating_cash_flow': f.operating_cash_flow,
                    'free_cash_flow': f.free_cash_flow,
                    'gross_profit': f.gross_profit,
                    'operating_income': f.operating_income,
                    'ebitda': f.ebitda,
                    'ebit': f.ebit,
                    'research_and_development': f.research_and_development,
                    'interest_expense': f.interest_expense,
                    'income_tax_expense': f.income_tax_expense,
                    'total_debt': f.total_debt,
                    'accounts_receivable': f.accounts_receivable,
                    'accounts_payable': f.accounts_payable,
                    'retained_earnings': f.retained_earnings,
                    'dividends_paid': f.dividends_paid,
                    'capital_expenditure': f.capital_expenditure,
                    'depreciation_and_amortization': f.depreciation_and_amortization
                } for f in financials])
                
            except (AttributeError, Exception) as e:
                # Fall back to REST API if client library method is not available
                logger.info(f"Falling back to REST API for {symbol} financials: {str(e)}")
                
                # Try different API endpoints
                endpoints = [
                    f"https://api.polygon.io/v2/reference/financials/{symbol}",
                    f"https://api.polygon.io/vX/reference/financials/{symbol}",
                    f"https://api.polygon.io/v3/reference/financials/{symbol}"
                ]
                
                for endpoint in endpoints:
                    try:
                        params = {
                            'apiKey': POLYGON_API_KEY,
                            'limit': limit,
                            'type': period
                        }
                        
                        logger.info(f"Trying endpoint: {endpoint}")
                        response = requests.get(endpoint, params=params)
                        
                        if response.status_code == 200:
                            data = response.json()
                            if data.get('results'):
                                logger.info(f"Successfully fetched data from {endpoint}")
                                break
                        else:
                            logger.warning(f"Endpoint {endpoint} returned status {response.status_code}")
                            continue
                            
                    except Exception as e:
                        logger.error(f"Error with endpoint {endpoint}: {str(e)}")
                        continue
                else:
                    logger.error(f"All endpoints failed for {symbol}")
                    return pd.DataFrame()
                
                if not data.get('results'):
                    logger.warning(f"No financial data found for {symbol}")
                    return pd.DataFrame()
                
                # Convert to DataFrame with required columns
                df = pd.DataFrame([{
                    'date': datetime.fromtimestamp(f['filing_date']/1000).strftime('%Y-%m-%d'),
                    'fiscal_period': f['fiscal_period'],
                    'fiscal_year': f['fiscal_year'],
                    'total_assets': f.get('total_assets'),
                    'current_assets': f.get('current_assets'),
                    'current_liabilities': f.get('current_liabilities'),
                    'inventory': f.get('inventory'),
                    'liabilities': f.get('total_liabilities'),
                    'revenue': f.get('revenue'),
                    'net_income': f.get('net_income'),
                    'eps': f.get('eps'),
                    'total_equity': f.get('total_equity'),
                    'operating_cash_flow': f.get('operating_cash_flow'),
                    'free_cash_flow': f.get('free_cash_flow'),
                    'gross_profit': f.get('gross_profit'),
                    'operating_income': f.get('operating_income'),
                    'ebitda': f.get('ebitda'),
                    'ebit': f.get('ebit'),
                    'research_and_development': f.get('research_and_development'),
                    'interest_expense': f.get('interest_expense'),
                    'income_tax_expense': f.get('income_tax_expense'),
                    'total_debt': f.get('total_debt'),
                    'accounts_receivable': f.get('accounts_receivable'),
                    'accounts_payable': f.get('accounts_payable'),
                    'retained_earnings': f.get('retained_earnings'),
                    'dividends_paid': f.get('dividends_paid'),
                    'capital_expenditure': f.get('capital_expenditure'),
                    'depreciation_and_amortization': f.get('depreciation_and_amortization')
                } for f in data['results']])
            
            if df.empty:
                logger.error(f"No data returned for {symbol}")
                return pd.DataFrame()
            
            # Log DataFrame info for debugging
            logger.info(f"DataFrame columns for {symbol}: {df.columns.tolist()}")
            logger.info(f"DataFrame shape: {df.shape}")
            
            # Set date as index
            df.set_index('date', inplace=True)
            df.index = pd.to_datetime(df.index)
            
            return df
            
        except Exception as e:
            logger.error(f"Error fetching financials for {symbol}: {e}", exc_info=True)
            return pd.DataFrame()
    
    def fetch_financial_statements(self, symbol: str, years: int) -> Dict:
        """
        Fetch financial statements from Polygon
        
        Args:
            symbol: Stock symbol
            years: Number of years of historical data to fetch
            
        Returns:
            Dict containing quarterly and annual financial statements
        """
        try:
            # Calculate limits based on years
            quarterly_limit = years * 4  # 4 quarters per year
            annual_limit = years
            
            logger.info(f"Fetching financial statements for {symbol} ({years} years)")
            
            # Fetch quarterly financials
            quarterly_cache_key = f"quarterly_financials_{symbol}_{quarterly_limit}"
            if not self.force_refresh:
                cached_data = self._load_from_cache(quarterly_cache_key)
                if cached_data:
                    logger.info(f"Using cached quarterly data for {symbol}")
                    quarterly_financials = pd.DataFrame.from_dict(cached_data)
                else:
                    logger.info(f"Fetching fresh quarterly data for {symbol}")
                    quarterly_financials = self._fetch_polygon_financials(symbol, "quarterly", quarterly_limit)
            else:
                logger.info(f"Force refreshing quarterly data for {symbol}")
                quarterly_financials = self._fetch_polygon_financials(symbol, "quarterly", quarterly_limit)
            
            # Fetch annual financials
            annual_cache_key = f"annual_financials_{symbol}_{annual_limit}"
            if not self.force_refresh:
                cached_data = self._load_from_cache(annual_cache_key)
                if cached_data:
                    logger.info(f"Using cached annual data for {symbol}")
                    annual_financials = pd.DataFrame.from_dict(cached_data)
                else:
                    logger.info(f"Fetching fresh annual data for {symbol}")
                    annual_financials = self._fetch_polygon_financials(symbol, "annual", annual_limit)
            else:
                logger.info(f"Force refreshing annual data for {symbol}")
                annual_financials = self._fetch_polygon_financials(symbol, "annual", annual_limit)
            
            # Log DataFrame info
            logger.info(f"Quarterly financials shape: {quarterly_financials.shape}")
            logger.info(f"Annual financials shape: {annual_financials.shape}")
            
            return {
                'quarterly_financials': quarterly_financials,
                'annual_financials': annual_financials
            }
            
        except Exception as e:
            logger.error(f"Error fetching financial statements for {symbol}: {e}", exc_info=True)
            return {
                'quarterly_financials': pd.DataFrame(),
                'annual_financials': pd.DataFrame()
            }
    
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
            market_cap = details.market_cap if hasattr(details, 'market_cap') else None
            
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