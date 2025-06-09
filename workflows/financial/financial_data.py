import pandas as pd
from typing import Dict, Optional
from datetime import datetime
from polygon import RESTClient
from ..base_fetcher import BaseFetcher
from utils.config import POLYGON_API_KEY

class FinancialDataFetcher(BaseFetcher):
    """Fetcher for financial analysis workflow data"""
    
    def __init__(self, force_refresh: bool = False):
        super().__init__(force_refresh, cache_subdir='financial')
        self.client = RESTClient(POLYGON_API_KEY)
    
    def calculate_peg_ratio(self, market_cap: float, annual_financials: pd.DataFrame) -> Optional[float]:
        """Calculate PEG ratio from financial data"""
        try:
            if annual_financials.empty or len(annual_financials) < 2:
                return None
                
            # Calculate P/E ratio using latest annual earnings
            latest_earnings = annual_financials.iloc[0].get('net_income', 0)
            
            if latest_earnings <= 0:
                return None
                
            pe_ratio = market_cap / (latest_earnings * 4)  # Annualize the earnings
            
            # Calculate earnings growth using last 2 years
            current_earnings = annual_financials.iloc[0].get('net_income', 0)
            prev_earnings = annual_financials.iloc[1].get('net_income', 0)
            
            if prev_earnings <= 0:
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
            return None
    
    def fetch_financial_statements(self, symbol: str, years: int) -> Dict:
        """Fetch financial statements with enhanced debugging (ported from /tmp)"""
        try:
            # Fetch quarterly and annual data using Polygon vx API
            quarterly = self._fetch_polygon_financials(symbol, "quarterly", years * 4)
            annual = self._fetch_polygon_financials(symbol, "annual", years)

            return {
                'quarterly_financials': quarterly,
                'annual_financials': annual
            }

        except Exception as e:
            return {
                'quarterly_financials': pd.DataFrame(),
                'annual_financials': pd.DataFrame()
            }

    def _fetch_polygon_financials(self, symbol: str, period: str, limit: int) -> pd.DataFrame:
        """Fetch financials from Polygon vx API and process into DataFrame (ported from /tmp)"""
        try:
            records = []
            # Use vx endpoint for financials
            financials = self.client.vx.list_stock_financials(
                ticker=symbol,
                timeframe=period,
                include_sources=True,
                limit=limit
            )
            # Get company details for sector
            company_details = self.client.get_ticker_details(symbol)
            sector = getattr(company_details, 'sic_description', None)
            for fin in financials:
                try:
                    record = {
                        'date': getattr(fin, 'filing_date', None),
                        'fiscal_period': getattr(fin, 'fiscal_period', None),
                        'fiscal_year': getattr(fin, 'fiscal_year', None),
                        'sector': sector,
                    }
                    if hasattr(fin, 'financials'):
                        # Income Statement
                        if hasattr(fin.financials, 'income_statement'):
                            inc = fin.financials.income_statement
                            record['revenue'] = self._get_value_from_datapoint(getattr(inc, 'revenues', None))
                            record['gross_profit'] = self._get_value_from_datapoint(getattr(inc, 'gross_profit', None))
                            record['operating_income'] = self._get_value_from_datapoint(getattr(inc, 'operating_income_loss', None))
                            record['net_income'] = self._get_value_from_datapoint(getattr(inc, 'net_income_loss', None))
                        # Balance Sheet
                        if hasattr(fin.financials, 'balance_sheet'):
                            bs = fin.financials.balance_sheet
                            record['total_assets'] = self._get_value_from_datapoint(getattr(bs, 'assets', None))
                            record['current_assets'] = self._get_value_from_datapoint(getattr(bs, 'current_assets', None))
                            record['current_liabilities'] = self._get_value_from_datapoint(getattr(bs, 'current_liabilities', None))
                            record['inventory'] = self._get_value_from_datapoint(getattr(bs, 'inventory', None))
                            record['liabilities'] = self._get_value_from_datapoint(getattr(bs, 'liabilities', None))
                        # Cash Flow Statement
                        if hasattr(fin.financials, 'cash_flow_statement'):
                            cf = fin.financials.cash_flow_statement
                            record['operating_cash_flow'] = self._get_value_from_datapoint(getattr(cf, 'net_cash_flow_from_operating_activities', None))
                            record['capital_expenditure'] = self._get_value_from_datapoint(getattr(cf, 'net_cash_flow_from_investing_activities', None))
                            record['financing_cash_flow'] = self._get_value_from_datapoint(getattr(cf, 'net_cash_flow_from_financing_activities', None))
                    if any(record.values()):
                        records.append(record)
                except Exception as e:
                    continue
            df = pd.DataFrame(records)
            if sector:
                df.attrs['sector'] = sector
            return df
        except Exception as e:
            return pd.DataFrame()

    def _get_value_from_datapoint(self, datapoint) -> float:
        """Extract value from Polygon API datapoint object, safely handling None."""
        if datapoint is None:
            return 0.0
        if hasattr(datapoint, 'value'):
            return float(datapoint.value) if datapoint.value is not None else 0.0
        try:
            return float(datapoint)
        except Exception:
            return 0.0
    
    def fetch_key_metrics(self, symbol: str) -> Dict:
        """Fetch key company metrics"""
        try:
            print(f"[DEBUG] Fetching ticker details for {symbol}")
            # Get company details using the correct API method
            details = self.client.get_ticker_details(symbol)
            print(f"[DEBUG] Ticker details: {details}")
            print(f"[DEBUG] Ticker details sector: {getattr(details, 'sector', None)}")
            print(f"[DEBUG] Ticker details sic_description: {getattr(details, 'sic_description', None)}")
            
            print(f"[DEBUG] Fetching fundamentals for {symbol}")
            # Get fundamentals using the correct API method
            fundamentals_data = self.client.get_ticker_financials_v2(symbol)  # Changed to v2
            print(f"[DEBUG] Fundamentals data: {fundamentals_data}")
            
            # Get latest financials for PEG calculation
            print(f"[DEBUG] Fetching financial statements for {symbol}")
            financials = self.fetch_financial_statements(symbol, 2)  # We need 2 years for growth calc
            annual_financials = financials.get('annual_financials', pd.DataFrame())
            
            # Get market cap from ticker details
            market_cap = getattr(details, 'market_cap', None)
            print(f"[DEBUG] Market cap: {market_cap}")
            
            # Use sector from details, fallback to sic_description, then DataFrame, then 'N/A'
            sector = getattr(details, 'sector', None) or getattr(details, 'sic_description', None)
            print(f"[DEBUG] Initial sector from details: {sector}")
            
            if not sector or sector == 'N/A':
                for df in [financials.get('quarterly_financials'), financials.get('annual_financials')]:
                    if isinstance(df, pd.DataFrame) and not df.empty:
                        sector = df['sector'].dropna().iloc[0] if 'sector' in df.columns and df['sector'].notna().any() else sector
                        print(f"[DEBUG] Sector from DataFrame: {sector}")
                        break
            if not sector:
                sector = 'N/A'
            print(f"[DEBUG] Final sector value: {sector}")
            
            # Get float from ticker details
            float_val = getattr(details, 'share_class_shares_outstanding', None)
            print(f"[DEBUG] Final float value: {float_val}")
            
            # Calculate PEG ratio
            peg_ratio = None
            if market_cap and not annual_financials.empty:
                peg_ratio = self.calculate_peg_ratio(market_cap, annual_financials)
            
            fundamentals = {
                'market_cap': market_cap,
                'weighted_shares': getattr(details, 'weighted_shares_outstanding', None),
                'float': float_val if float_val is not None else 'N/A',
                'employees': getattr(details, 'total_employees', None),
                'sector': sector,
                'peg_ratio': peg_ratio
            }
            print(f"[DEBUG] Final fundamentals dict: {fundamentals}")
            
            result = {
                'name': getattr(details, 'name', 'N/A'),
                'sector': sector,
                'description': getattr(details, 'description', 'N/A'),
                'exchange': getattr(details, 'primary_exchange', 'N/A'),
                'logo_url': getattr(details, 'branding', {}).get('logo_url') if hasattr(details, 'branding') else None,
                'employees': getattr(details, 'total_employees', None),
                'fundamentals': fundamentals
            }
            print(f"[DEBUG] Final result dict: {result}")
            
            # Cache the data
            self._save_to_cache(f"key_metrics_{symbol}", result)
            return result
            
        except Exception as e:
            print(f"[ERROR] Error fetching key metrics: {str(e)}")
            import traceback
            print(f"[ERROR] Traceback: {traceback.format_exc()}")
            return {
                'name': 'N/A',
                'sector': 'N/A',
                'description': 'N/A',
                'exchange': 'N/A',
                'logo_url': None,
                'employees': None,
                'fundamentals': {}
            } 