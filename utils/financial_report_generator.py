import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np
from jinja2 import Environment, FileSystemLoader
from utils.metadata_generator import generate_metadata, save_metadata
import logging
import json

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    if value is None:
        return "N/A"
    return f"{value:.2f}"

def calculate_growth(current: float, prior: float) -> Optional[float]:
    """Calculate growth rate with validation"""
    if not all(isinstance(x, (int, float)) for x in [current, prior]):
        return None
    if prior == 0:
        return None
    growth = (current - prior) / prior
    return validate_percentage(growth)

def calculate_cagr(series: pd.Series, years: int) -> Optional[float]:
    """Calculate Compound Annual Growth Rate with validation"""
    if len(series) < 2:
        return None
    
    first_value = series.iloc[-1]
    last_value = series.iloc[0]
    
    if first_value <= 0 or last_value <= 0:
        return None
        
    growth = (last_value / first_value) ** (1/years) - 1
    return validate_percentage(growth)

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
        logger.error(f"Error calculating financial metrics: {e}", exc_info=True)
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
        f'{period} Revenue': 'Total revenue generated during the period',
        f'{period} Net Income': 'Net profit after all expenses and taxes',
        'Gross Margin': 'Percentage of revenue remaining after direct costs',
        'Operating Margin': 'Percentage of revenue remaining after operating expenses',
        'Net Margin': 'Percentage of revenue converted to profit',
        'FCF Margin': 'Free cash flow as a percentage of revenue',
        'Operating Cash Ratio': 'Operating cash flow relative to current liabilities',
        'Quick Ratio': 'Ability to pay short-term obligations with liquid assets',
        'Current Ratio': 'Ability to pay short-term obligations with all current assets'
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

def format_large_number(value: float) -> str:
    """Format large numbers to use K, M, B, T suffixes"""
    try:
        if value is None or pd.isna(value):
            return 'N/A'
        
        if value == 0:
            return '-'
            
        abs_value = abs(value)
        if abs_value >= 1_000_000_000_000:  # Trillion
            return f"${value / 1_000_000_000_000:.2f}T"
        elif abs_value >= 1_000_000_000:  # Billion
            return f"${value / 1_000_000_000:.2f}B"
        elif abs_value >= 1_000_000:  # Million
            return f"${value / 1_000_000:.2f}M"
        elif abs_value >= 1_000:  # Thousand
            return f"${value / 1_000:.2f}K"
        else:
            return f"${value:.2f}"
    except:
        return 'N/A'

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
        logger.error(f"Error calculating {period} metrics: {e}", exc_info=True)
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
        logger.info(f"Starting financial report generation for {symbol}")
        
        # Log the data structure we received
        logger.info("Received data keys:")
        for key in data.keys():
            if isinstance(data[key], pd.DataFrame):
                logger.info(f"DataFrame '{key}': {len(data[key])} rows")
            else:
                logger.info(f"Key '{key}': {type(data[key])}")

        report_dir = os.path.join('public', 'results', f"{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        os.makedirs(report_dir, exist_ok=True)
        
        # Get company info including sector
        company_info = {
            'name': metrics.get('name', 'N/A'),
            'description': metrics.get('description', 'N/A'),
            'sector': metrics.get('sector', 'N/A')
        }
        
        # Create common metadata
        common_metadata = {
            "symbol": symbol,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "company_info": company_info  # Include company info in metadata
        }
        
        # Calculate all metrics first
        calculated_metrics = calculate_financial_metrics(data)
        
        # Save metrics with metadata
        metrics_file = os.path.join(report_dir, 'metrics.json')
        metrics_data = {
            **common_metadata,
            'metrics': calculated_metrics
        }
        
        with open(metrics_file, 'w') as f:
            json.dump(metrics_data, f, indent=2)
        logger.info("Successfully saved metrics.json")
        
        # Get latest date from data
        formatted_date = datetime.now().strftime('%Y-%m-%d')
        fiscal_quarter_date = formatted_date
        fiscal_year_date = formatted_date
        
        # Update statement_types dictionary to ensure proper data mapping
        statement_types = {
            'quarterly_income': data.get('quarterly_financials', pd.DataFrame()),
            'annual_income': data.get('annual_financials', pd.DataFrame()),
            'quarterly_balance': data.get('quarterly_balance_sheet', pd.DataFrame()),
            'annual_balance': data.get('annual_balance_sheet', pd.DataFrame()),
            'quarterly_cash_flow': data.get('quarterly_cash_flow', pd.DataFrame()),
            'annual_cash_flow': data.get('annual_cash_flow', pd.DataFrame())
        }

        # Try alternative keys if primary ones aren't found
        alternative_keys = {
            'annual_balance': ['annual_balance_sheet', 'annual_balance', 'balance_sheet_annual'],
            'annual_cash_flow': ['annual_cash_flow', 'cash_flow_annual', 'annual_cashflow']
        }

        for statement_key, alt_keys in alternative_keys.items():
            if statement_types[statement_key].empty:
                for alt_key in alt_keys:
                    if alt_key in data and isinstance(data[alt_key], pd.DataFrame) and not data[alt_key].empty:
                        logger.info(f"Found alternative key {alt_key} for {statement_key}")
                        statement_types[statement_key] = data[alt_key]
                        break

        # Create balance sheet and cash flow files from the consolidated data
        if isinstance(data.get('quarterly_financials'), pd.DataFrame):
            # Create quarterly balance sheet
            quarterly_balance = data['quarterly_financials'][['date', 'fiscal_period', 'fiscal_year', 
                'total_assets', 'current_assets', 'current_liabilities', 'inventory', 'liabilities']]
            statement_types['quarterly_balance'] = quarterly_balance

            # Create quarterly cash flow
            quarterly_cash_flow = data['quarterly_financials'][['date', 'fiscal_period', 'fiscal_year',
                'operating_cash_flow', 'capital_expenditure', 'financing_cash_flow']]
            statement_types['quarterly_cash_flow'] = quarterly_cash_flow

        if isinstance(data.get('annual_financials'), pd.DataFrame):
            # Create annual balance sheet
            annual_balance = data['annual_financials'][['date', 'fiscal_period', 'fiscal_year',
                'total_assets', 'current_assets', 'current_liabilities', 'inventory', 'liabilities']]
            statement_types['annual_balance'] = annual_balance

            # Create annual cash flow
            annual_cash_flow = data['annual_financials'][['date', 'fiscal_period', 'fiscal_year',
                'operating_cash_flow', 'capital_expenditure', 'financing_cash_flow']]
            statement_types['annual_cash_flow'] = annual_cash_flow

        for name, df in statement_types.items():
            try:
                if isinstance(df, pd.DataFrame) and not df.empty:
                    logger.info(f"Processing {name} with {len(df)} rows")
                    df_copy = df.copy()
                    
                    # Handle date columns safely
                    date_columns = ['date', 'end_date']
                    for col in date_columns:
                        if col in df_copy.columns:
                            df_copy[col] = df_copy[col].apply(lambda x: 
                                pd.to_datetime(x, errors='coerce').strftime('%Y-%m-%d') 
                                if pd.notna(x) and x != 'N/A' 
                                else 'N/A'
                            )
                    
                    # Create JSON data with metadata
                    json_data = {
                        **common_metadata,
                        'data': df_copy.to_dict('records')
                    }
                    
                    # Save to JSON
                    file_path = os.path.join(report_dir, f"{name}.json")
                    with open(file_path, 'w') as f:
                        json.dump(json_data, f, indent=2)
                    logger.info(f"Successfully saved {file_path}")
                    
                    # Update fiscal dates if available
                    if name == 'quarterly_income' and 'end_date' in df_copy.columns:
                        valid_dates = df_copy[df_copy['end_date'] != 'N/A']['end_date']
                        if not valid_dates.empty:
                            fiscal_quarter_date = valid_dates.iloc[0]
                    
                    if name == 'annual_income' and 'end_date' in df_copy.columns:
                        valid_dates = df_copy[df_copy['end_date'] != 'N/A']['end_date']
                        if not valid_dates.empty:
                            fiscal_year_date = valid_dates.iloc[0]
                            
                else:
                    logger.warning(f"No data available for {name}")
                    
            except Exception as e:
                logger.error(f"Error processing {name}: {str(e)}", exc_info=True)
                continue
        
        # Save raw data with metadata
        try:
            raw_data_path = os.path.join(report_dir, 'raw_data.json')
            # Convert DataFrames to records for JSON serialization
            serializable_data = {
                k: v.to_dict('records') if isinstance(v, pd.DataFrame) else v
                for k, v in data.items()
            }
            
            raw_data_with_metadata = {
                **common_metadata,  # Add common metadata
                'data': serializable_data
            }
            
            with open(raw_data_path, 'w') as f:
                json.dump(raw_data_with_metadata, f, indent=2, default=str)
            logger.info("Successfully saved raw_data.json")
        except Exception as e:
            logger.error(f"Error saving raw data: {e}", exc_info=True)
        
        # Setup Jinja2 environment
        env = Environment(loader=FileSystemLoader('templates'))
        template = env.get_template('financial_report.html')
        
        # Prepare report data
        report_data = {
            'symbol': symbol,
            'company_info': company_info,
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
        with open(report_path, 'w') as f:
            f.write(html_content)
        
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
            directory_name=os.path.basename(report_dir),
            additional_data={
                "status": "finished",
                "title": f"Financial Analysis - {symbol}",
                "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "report_type": "snapshot"
            }
        )
        save_metadata(metadata, report_dir)
        
        return report_path
        
    except Exception as e:
        logger.error(f"Error generating financial report: {e}", exc_info=True)
        return None