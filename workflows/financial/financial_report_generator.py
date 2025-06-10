import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np
from jinja2 import Environment, FileSystemLoader
from workflows.metadata_generator import generate_metadata, save_metadata
import json
import math
from workflows.financial.metric_descriptions import METRIC_DESCRIPTIONS

def validate_percentage(value: float) -> Optional[float]:
    """Validate percentage is within acceptable range (-100% to +500%)"""
    if value is None or not isinstance(value, (int, float)):
        return None
    if -1 <= value <= 5:  # -100% to +500%
        return round(value * 100, 2)  # Convert to percentage and round to 2 decimals
    return None

def format_percentage(value: float) -> str:
    """Format a value as a percentage"""
    if value is None or pd.isna(value):
        return 'N/A'
    return f"{value * 100:.2f}%"

def format_decimal(value: Optional[float]) -> str:
    """Format decimal with 2 decimal places"""
    if value is None or value == 'N/A' or not isinstance(value, (int, float)):
        return "N/A"
    try:
        return f"{float(value):.2f}"
    except (ValueError, TypeError):
        return "N/A"

def calculate_financial_metrics(data: Dict) -> Dict:
    """Calculate financial metrics from raw data"""
    try:
        metrics = {
            'Quarterly Metrics': {},
            'Annual Metrics': {},
            'Descriptions': {},
            'Annual Descriptions': {},
            'Calculations': {'Raw Values': {}, 'Algorithms': {}, 'Formulas': {}},
            'Annual Calculations': {'Raw Values': {}, 'Algorithms': {}, 'Formulas': {}}
        }
        
        # Process quarterly data
        if isinstance(data.get('quarterly_financials'), pd.DataFrame) and not data['quarterly_financials'].empty:
            current_q = data['quarterly_financials'].iloc[0]
            metrics['Quarterly Metrics'] = calculate_period_metrics(current_q, 'Quarterly')
            metrics['Calculations']['Algorithms'] = generate_metric_formulas('Quarterly')
            metrics['Calculations']['Formulas'] = generate_actual_calculations(current_q, 'Quarterly')
            metrics['Calculations']['Raw Values'] = generate_calculation_details(current_q, 'Quarterly')['Raw Values']
        
        # Process annual data
        if isinstance(data.get('annual_financials'), pd.DataFrame) and not data['annual_financials'].empty:
            current_a = data['annual_financials'].iloc[0]
            metrics['Annual Metrics'] = calculate_period_metrics(current_a, 'Annual')
            metrics['Annual Calculations']['Algorithms'] = generate_metric_formulas('Annual')
            metrics['Annual Calculations']['Formulas'] = generate_actual_calculations(current_a, 'Annual')
            metrics['Annual Calculations']['Raw Values'] = generate_calculation_details(current_a, 'Annual')['Raw Values']
        
        # Add descriptions
        metrics['Descriptions'] = generate_metric_descriptions('Quarterly')
        metrics['Annual Descriptions'] = generate_metric_descriptions('Annual')
        
        return metrics
        
    except Exception as e:
        return {
            'Quarterly Metrics': {},
            'Annual Metrics': {},
            'Descriptions': {},
            'Annual Descriptions': {},
            'Calculations': {'Raw Values': {}, 'Algorithms': {}, 'Formulas': {}},
            'Annual Calculations': {'Raw Values': {}, 'Algorithms': {}, 'Formulas': {}}
        }

def generate_metric_descriptions(period: str) -> Dict[str, str]:
    """Generate descriptions for financial metrics"""
    return {
        'Market Cap': 'Total market value of outstanding shares',
        'Enterprise Value': 'Market Cap + Total Debt - Cash and Equivalents',
        'EV/EBITDA': 'Enterprise Value divided by EBITDA (valuation multiple)',
        'PEG Ratio': 'Price/Earnings ratio divided by earnings growth rate. Values under 1 may indicate undervaluation.',
        'Sector': 'Industry sector classification',
        'Weighted Shares': 'Weighted average of outstanding shares',
        'Float': 'Number of shares available for public trading',
        'Employees': 'Total number of employees'
    }

def generate_metric_formulas(period: str) -> Dict[str, str]:
    """Generate formulas for financial metrics"""
    return {
        'Gross Margin': 'Gross Profit / Revenue',
        'Operating Margin': 'Operating Income / Revenue',
        'Net Margin': 'Net Income / Revenue',
        'FCF Margin': '(Operating Cash Flow - CapEx) / Revenue',
        'Operating Cash Ratio': 'Operating Cash Flow / Current Liabilities',
        'Quick Ratio': '(Current Assets - Inventory) / Current Liabilities',
        'Current Ratio': 'Current Assets / Current Liabilities'
    }

def format_large_number(value: Optional[float], include_currency: bool = True) -> str:
    """Format large numbers with K, M, B suffixes and optional currency symbol"""
    if value is None or pd.isna(value):
        return "N/A"
    
    try:
        value = float(value)
        if value == 0:
            return "$0" if include_currency else "0"
            
        suffixes = ['', 'K', 'M', 'B', 'T']
        magnitude = max(0, min(len(suffixes) - 1, int(math.floor(math.log10(abs(value)) / 3))))
        scaled_value = value / (1000 ** magnitude)
        suffix = suffixes[magnitude]
        
        formatted = f"{scaled_value:.2f}{suffix}"
        return f"${formatted}" if include_currency else formatted
        
    except (ValueError, TypeError):
        return "N/A"

def generate_actual_calculations(data: pd.Series, period: str) -> Dict[str, str]:
    """Generate actual calculations with formatted values"""
    revenue = data.get('revenue', 0)
    gross_profit = data.get('gross_profit', 0)
    operating_income = data.get('operating_income', 0)
    net_income = data.get('net_income', 0)
    operating_cash_flow = data.get('operating_cash_flow', 0)
    capex = data.get('capital_expenditure', 0)
    current_assets = data.get('current_assets', 0)
    current_liabilities = data.get('current_liabilities', 0)
    inventory = data.get('inventory', 0)

    return {
        'Gross Margin': f'{format_large_number(gross_profit)} / {format_large_number(revenue)}',
        'Operating Margin': f'{format_large_number(operating_income)} / {format_large_number(revenue)}',
        'Net Margin': f'{format_large_number(net_income)} / {format_large_number(revenue)}',
        'FCF Margin': f'({format_large_number(operating_cash_flow)} - {format_large_number(capex)}) / {format_large_number(revenue)}',
        'Operating Cash Ratio': f'{format_large_number(operating_cash_flow)} / {format_large_number(current_liabilities)}',
        'Quick Ratio': f'({format_large_number(current_assets)} - {format_large_number(inventory)}) / {format_large_number(current_liabilities)}',
        'Current Ratio': f'{format_large_number(current_assets)} / {format_large_number(current_liabilities)}'
    }

def calculate_period_metrics(data: pd.Series, period: str) -> Dict:
    """Calculate financial metrics for a given period"""
    try:
        # Get raw values with better None handling
        revenue = data.get('revenue', 0)
        gross_profit = data.get('gross_profit', 0)
        operating_income = data.get('operating_income', 0)
        net_income = data.get('net_income', 0)
        operating_cash_flow = data.get('operating_cash_flow', 0)
        capital_expenditure = data.get('capital_expenditure', 0)
        current_assets = data.get('current_assets', 0)
        current_liabilities = data.get('current_liabilities', 0)
        inventory = data.get('inventory', 0)
        total_assets = data.get('total_assets', 0)
        
        # Calculate metrics only if we have valid revenue
        metrics = {}
        
        if revenue > 0:
            metrics = {
                f'{period} Revenue': format_large_number(revenue),
                f'{period} Net Income': format_large_number(net_income),
                'Gross Margin': format_percentage(gross_profit / revenue) if revenue else 'N/A',
                'Operating Margin': format_percentage(operating_income / revenue) if revenue else 'N/A',
                'Net Margin': format_percentage(net_income / revenue) if revenue else 'N/A',
                'FCF Margin': format_percentage((operating_cash_flow - capital_expenditure) / revenue) if revenue else 'N/A',
                'Operating Cash Ratio': format_decimal(operating_cash_flow / current_liabilities) if current_liabilities else 'N/A',
                'Quick Ratio': format_decimal((current_assets - inventory) / current_liabilities) if current_liabilities else 'N/A',
                'Current Ratio': format_decimal(current_assets / current_liabilities) if current_liabilities else 'N/A'
            }
        
        return metrics
        
    except Exception as e:
        return {}

def generate_calculation_details(data: pd.Series, period: str) -> Dict:
    """Generate calculation details for transparency"""
    return {
        'Raw Values': {
            f'{period} Revenue': format_large_number(data.get('revenue', 0)),
            f'{period} Net Income': format_large_number(data.get('net_income', 0)),
            f'{period} Gross Profit': format_large_number(data.get('gross_profit', 0)),
            f'{period} Operating Income': format_large_number(data.get('operating_income', 0)),
            f'{period} Operating Cash Flow': format_large_number(data.get('operating_cash_flow', 0)),
            'Total Assets': format_large_number(data.get('total_assets', 0)),
            'Current Assets': format_large_number(data.get('current_assets', 0)),
            'Current Liabilities': format_large_number(data.get('current_liabilities', 0))
        },
        'Algorithms': generate_metric_formulas(period),
        'Formulas': generate_actual_calculations(data, period)
    }

def format_currency(value: Optional[float]) -> str:
    """Format currency with better handling of zero and None values"""
    if value is None:
        return 'N/A'
    if value == 0:
        return '-'  # Show dash instead of $0.00
    return f"${value:,.2f}"

def calculate_financial_ratios(fundamentals: Dict, data: Dict) -> Dict:
    """Calculate financial ratios from available data"""
    try:
        # Get market cap and PEG ratio
        market_cap = fundamentals.get('market_cap', 0)
        peg_ratio = fundamentals.get('peg_ratio')  # Get PEG from fundamentals
        
        # Get latest quarterly data
        quarterly_data = None
        if isinstance(data.get('quarterly_financials'), pd.DataFrame) and not data['quarterly_financials'].empty:
            quarterly_data = data['quarterly_financials'].iloc[0]
            
        # Calculate Enterprise Value
        total_debt = float(quarterly_data.get('liabilities', 0) or 0) if quarterly_data is not None else 0
        cash_and_equiv = float(quarterly_data.get('current_assets', 0) or 0) if quarterly_data is not None else 0
        enterprise_value = market_cap + total_debt - cash_and_equiv
        
        # Calculate EBITDA and related metrics
        revenue = float(quarterly_data.get('revenue', 0) or 0) if quarterly_data is not None else 0
        operating_income = float(quarterly_data.get('operating_income', 0) or 0) if quarterly_data is not None else 0
        net_income = float(quarterly_data.get('net_income', 0) or 0) if quarterly_data is not None else 0
        
        # Annualize quarterly numbers
        revenue_annual = revenue * 4
        operating_income_annual = operating_income * 4
        
        # Calculate ratios
        ev_ebitda = enterprise_value / operating_income_annual if operating_income_annual and operating_income_annual > 0 else None
        ev_revenue = enterprise_value / revenue_annual if revenue_annual and revenue_annual > 0 else None
        net_margin = (net_income / revenue) if revenue and revenue > 0 else None
        
        # If PEG is None, try calculating it directly
        if peg_ratio is None and isinstance(data.get('annual_financials'), pd.DataFrame) and not data['annual_financials'].empty:
            annual_data = data['annual_financials']
            if len(annual_data) >= 2:
                current_earnings = annual_data.iloc[0].get('net_income', 0)
                prev_earnings = annual_data.iloc[1].get('net_income', 0)
                
                if prev_earnings > 0 and current_earnings > 0:
                    growth_rate = (current_earnings - prev_earnings) / prev_earnings
                    if growth_rate > 0:
                        pe_ratio = market_cap / (current_earnings * 4)
                        peg_ratio = pe_ratio / growth_rate
                        # Validate PEG ratio range
                        if peg_ratio <= 0 or peg_ratio > 100:
                            peg_ratio = None
        
        result = {
            'enterprise_value': enterprise_value,
            'ev_ebitda': ev_ebitda,
            'ev_revenue': ev_revenue,
            'net_margin': net_margin,
            'operating_income': operating_income,
            'revenue': revenue,
            'peg_ratio': peg_ratio
        }
        return result
    except Exception as e:
        return {
            'enterprise_value': None,
            'ev_ebitda': None,
            'ev_revenue': None,
            'net_margin': None,
            'operating_income': None,
            'revenue': None,
            'peg_ratio': None
        }

def calculate_peg_ratio(fundamentals: Dict, data: Dict) -> Optional[float]:
    try:
        # Calculate P/E ratio
        market_cap = fundamentals.get('market_cap', 0)
        if isinstance(data.get('annual_financials'), pd.DataFrame) and not data['annual_financials'].empty:
            latest_earnings = data['annual_financials'].iloc[0].get('net_income', 0)
            pe_ratio = market_cap / (latest_earnings * 4) if latest_earnings > 0 else None
            
            # Calculate earnings growth (using last 2 years)
            if len(data['annual_financials']) >= 2:
                current_earnings = data['annual_financials'].iloc[0].get('net_income', 0)
                prev_earnings = data['annual_financials'].iloc[1].get('net_income', 0)
                growth_rate = ((current_earnings - prev_earnings) / prev_earnings) if prev_earnings > 0 else None
                
                # Calculate PEG
                if pe_ratio and growth_rate and growth_rate > 0:
                    return pe_ratio / growth_rate
                    
        return None
    except Exception as e:
        return None

def generate_financial_report(symbol: str, data: Dict, metrics: Dict) -> Optional[str]:
    """Generate financial analysis report
    
    Args:
        symbol (str): Stock symbol
        data (Dict): Financial data dictionary
        metrics (Dict): Calculated metrics
        
    Returns:
        Optional[str]: Path to generated report or None if failed
    """
    try:
        print(f"[DEBUG] Starting financial report generation for {symbol}")
        print(f"[DEBUG] Received data keys: {data.keys()}")
        print(f"[DEBUG] Received metrics: {metrics}")
        
        # Use fundamentals from metrics, not data
        fundamentals = metrics.get('fundamentals', {})
        print(f"[DEBUG] Retrieved fundamentals: {fundamentals}")
        
        # Calculate financial ratios
        financial_ratios = calculate_financial_ratios(fundamentals, data)
        
        # Format market metrics with debug logging
        market_metrics = {
            'Sector': fundamentals.get('sector', 'N/A'),
            'Market Cap': format_large_number(fundamentals.get('market_cap', 0)),
            'Enterprise Value': format_large_number(financial_ratios.get('enterprise_value')),
            'EV/EBITDA': format_decimal(financial_ratios.get('ev_ebitda')),
            'EV/Revenue': format_decimal(financial_ratios.get('ev_revenue')),
            'PEG Ratio': format_decimal(fundamentals.get('peg_ratio', financial_ratios.get('peg_ratio'))),
            'Weighted Shares': format_large_number(fundamentals.get('weighted_shares', 0), include_currency=False),
            'Float': format_large_number(fundamentals.get('float', 0), include_currency=False),
            'Employees': format_large_number(fundamentals.get('employees', 0), include_currency=False)
        }
        print(f"[DEBUG] Generated market metrics: {market_metrics}")
        
        # Create report directory with daily-based structure
        today = datetime.now().strftime("%Y%m%d")
        directory_name = f"financial_{symbol}_{today}"
        report_dir = os.path.join('public', 'results', directory_name)
        print(f"[DEBUG] Creating report directory: {report_dir}")
        os.makedirs(report_dir, exist_ok=True)
        print(f"[DEBUG] Report directory created: {os.path.exists(report_dir)}")
        
        # Get company info including all relevant fields
        company_info = {
            'name': metrics.get('name', 'N/A'),
            'description': metrics.get('description', 'N/A'),
            'sector': metrics.get('sector', 'N/A'),
            'logo_url': metrics.get('logo_url', None),
            'employees': fundamentals.get('employees', 'N/A'),
            'weighted_shares': fundamentals.get('weighted_shares', 'N/A'),
            'float': fundamentals.get('float', 'N/A'),
        }
        print(f"[DEBUG] Company info: {company_info}")
        
        # Create common metadata
        common_metadata = {
            "symbol": symbol,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "company_info": company_info
        }
        
        # Calculate all metrics first
        calculated_metrics = calculate_financial_metrics(data)
        
        # Add descriptions to metrics dictionary
        calculated_metrics['Descriptions'] = METRIC_DESCRIPTIONS
        
        # Save metrics with metadata (raw data output)
        metrics_file = os.path.join(report_dir, 'metrics.json')
        metrics_data = {
            **common_metadata,
            'market_metrics': market_metrics,
            'metrics': calculated_metrics
        }
        
        print(f"[DEBUG] Saving metrics to: {metrics_file}")
        with open(metrics_file, 'w') as f:
            json.dump(metrics_data, f, indent=2)
        print(f"[DEBUG] Metrics saved: {os.path.exists(metrics_file)}")
        
        # Get latest date from data
        formatted_date = datetime.now().strftime('%Y-%m-%d')
        fiscal_quarter_date = formatted_date
        fiscal_year_date = formatted_date
        
        # Setup Jinja2 environment with the correct template path
        template_dir = os.path.join(os.path.dirname(__file__), '..')
        print(f"[DEBUG] Template directory: {template_dir}")
        env = Environment(loader=FileSystemLoader(template_dir))
        template = env.get_template('financial/financial_report.html')
        
        # Prepare report data
        report_data = {
            'symbol': symbol,
            'company_info': company_info,
            'market_metrics': market_metrics,
            'dates': {
                'latest': formatted_date,
                'fiscal_quarter': fiscal_quarter_date,
                'fiscal_year': fiscal_year_date
            },
            'metrics': calculated_metrics,
            'generated_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Generate HTML
        html_content = template.render(**report_data)
        
        # Save report
        report_path = os.path.join(report_dir, 'index.html')
        print(f"[DEBUG] Saving report to: {report_path}")
        with open(report_path, 'w') as f:
            f.write(html_content)
        print(f"[DEBUG] Report saved: {os.path.exists(report_path)}")
        
        # Generate and save metadata
        current_date = datetime.now().strftime('%Y-%m-%d')
        metadata = generate_metadata(
            symbol=symbol,
            timeframe="snapshot",
            start_date=current_date,
            end_date=current_date,
            initial_capital=0,
            commission=0,
            report_type="financial",
            directory_name=directory_name,
            additional_data={
                "status": "finished",
                "title": f"Financial Analysis - {symbol}",
                "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "report_type": "snapshot"
            }
        )
        save_metadata(metadata, report_dir)
        print(f"[DEBUG] Metadata saved to: {report_dir}")
        
        return report_path
        
    except Exception as e:
        print(f"[ERROR] Error generating financial report: {str(e)}")
        import traceback
        print(f"[ERROR] Traceback: {traceback.format_exc()}")
        return None

def generate_market_metrics(data: Dict) -> Dict:
    """Generate market metrics including PEG ratio"""
    metrics = {}
    
    # Add PEG ratio calculation
    try:
        pe_ratio = float(data.get('market_metrics', {}).get('P/E Ratio', 0))
        growth_rate = float(data.get('annual_metrics', {}).get('Earnings Growth Rate', 0))
        
        if pe_ratio > 0 and growth_rate > 0:
            peg_ratio = pe_ratio / growth_rate
            metrics['PEG Ratio'] = f"{peg_ratio:.2f}"
        else:
            metrics['PEG Ratio'] = 'N/A'
    except (ValueError, TypeError):
        metrics['PEG Ratio'] = 'N/A'
    
    # Add description for PEG
    metrics['Descriptions']['PEG Ratio'] = "Price/Earnings to Growth ratio. A value under 1 may indicate the stock is undervalued given its growth rate."
    
    return metrics