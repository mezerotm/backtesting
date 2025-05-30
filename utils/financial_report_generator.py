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

def format_percentage(value: Optional[float]) -> str:
    """Format percentage with 2 decimal places"""
    if value is None:
        return "N/A"
    return f"{value:.2f}%"

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

        # Debug data structure
        logger.info(f"Input data structure: {list(data.keys())}")
        
        # Handle quarterly metrics
        q_financials = data.get('quarterly_financials')
        if isinstance(q_financials, pd.DataFrame) and not q_financials.empty:
            logger.info(f"Processing quarterly data with columns: {q_financials.columns.tolist()}")
            logger.info(f"First row sample: {q_financials.iloc[0].to_dict()}")
            
            current_q = q_financials.iloc[0]
            
            # Calculate quarterly raw values
            metrics['Calculations']['Raw Values'] = {
                'Quarterly Revenue': format_currency(current_q.get('revenue', 0)),
                'Quarterly Net Income': format_currency(current_q.get('net_income', 0)),
                'Quarterly Gross Profit': format_currency(current_q.get('gross_profit', 0)),
                'Quarterly Operating Income': format_currency(current_q.get('operating_income', 0)),
                'Quarterly Operating Cash Flow': format_currency(current_q.get('operating_cash_flow', 0)),
                'Total Assets': format_currency(current_q.get('total_assets', 0)),
                'Current Assets': format_currency(current_q.get('current_assets', 0)),
                'Current Liabilities': format_currency(current_q.get('current_liabilities', 0))
            }
            
            # Calculate metrics
            metrics['Quarterly Metrics'] = calculate_period_metrics(current_q, 'Quarterly')
            metrics['Calculations']['Algorithms'] = generate_metric_formulas('Quarterly')
            metrics['Calculations']['Formulas'] = generate_actual_calculations(current_q, 'Quarterly')
            metrics['Descriptions'].update(generate_metric_descriptions('Quarterly'))
            
            logger.info(f"Quarterly metrics calculated: {metrics['Quarterly Metrics']}")
            logger.info(f"Quarterly raw values: {metrics['Calculations']['Raw Values']}")

        # Handle annual metrics (similar structure)
        a_financials = data.get('annual_financials')
        if isinstance(a_financials, pd.DataFrame) and not a_financials.empty:
            logger.info(f"Processing annual data with columns: {a_financials.columns.tolist()}")
            logger.info(f"First row sample: {a_financials.iloc[0].to_dict()}")
            
            current_a = a_financials.iloc[0]
            
            # Calculate annual raw values
            metrics['Annual Calculations']['Raw Values'] = {
                'Annual Revenue': format_currency(current_a.get('revenue', 0)),
                'Annual Net Income': format_currency(current_a.get('net_income', 0)),
                'Annual Gross Profit': format_currency(current_a.get('gross_profit', 0)),
                'Annual Operating Income': format_currency(current_a.get('operating_income', 0)),
                'Annual Operating Cash Flow': format_currency(current_a.get('operating_cash_flow', 0)),
                'Total Assets': format_currency(current_a.get('total_assets', 0)),
                'Current Assets': format_currency(current_a.get('current_assets', 0)),
                'Current Liabilities': format_currency(current_a.get('current_liabilities', 0))
            }
            
            # Calculate metrics
            metrics['Annual Metrics'] = calculate_period_metrics(current_a, 'Annual')
            metrics['Annual Calculations']['Algorithms'] = generate_metric_formulas('Annual')
            metrics['Annual Calculations']['Formulas'] = generate_actual_calculations(current_a, 'Annual')
            metrics['Annual Descriptions'].update(generate_metric_descriptions('Annual'))
            
            logger.info(f"Annual metrics calculated: {metrics['Annual Metrics']}")
            logger.info(f"Annual raw values: {metrics['Annual Calculations']['Raw Values']}")

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

def generate_actual_calculations(data: pd.Series, period: str) -> Dict[str, str]:
    """Generate actual calculations with values"""
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
        'Gross Margin': f'{gross_profit:,.2f} / {revenue:,.2f}',
        'Operating Margin': f'{operating_income:,.2f} / {revenue:,.2f}',
        'Net Margin': f'{net_income:,.2f} / {revenue:,.2f}',
        'FCF Margin': f'({operating_cash_flow:,.2f} - {capex:,.2f}) / {revenue:,.2f}',
        'Operating Cash Ratio': f'{operating_cash_flow:,.2f} / {current_liabilities:,.2f}',
        'Quick Ratio': f'({current_assets:,.2f} - {inventory:,.2f}) / {current_liabilities:,.2f}',
        'Current Ratio': f'{current_assets:,.2f} / {current_liabilities:,.2f}'
    }

def calculate_period_metrics(data: pd.Series, period: str) -> Dict:
    """Calculate metrics for a given period"""
    metrics = {}
    try:
        # Debug the input data
        logger.debug(f"{period} data fields: {data.index.tolist()}")
        
        revenue = float(data.get('revenue', 0))
        if revenue > 0:
            metrics.update({
                f'{period} Revenue': format_currency(revenue),
                f'{period} Net Income': format_currency(float(data.get('net_income', 0))),
                'Gross Margin': format_percentage(float(data.get('gross_profit', 0)) / revenue if revenue else 0),
                'Operating Margin': format_percentage(float(data.get('operating_income', 0)) / revenue if revenue else 0),
                'Net Margin': format_percentage(float(data.get('net_income', 0)) / revenue if revenue else 0)
            })
            
            # Calculate FCF Margin
            operating_cash_flow = float(data.get('operating_cash_flow', 0))
            capex = float(data.get('capital_expenditure', 0))
            metrics['FCF Margin'] = format_percentage((operating_cash_flow - capex) / revenue if revenue else 0)
            
            # Calculate liquidity ratios
            current_liabilities = float(data.get('current_liabilities', 0))
            if current_liabilities > 0:
                current_assets = float(data.get('current_assets', 0))
                inventory = float(data.get('inventory', 0))
                
                metrics.update({
                    'Operating Cash Ratio': format_decimal(operating_cash_flow / current_liabilities),
                    'Quick Ratio': format_decimal((current_assets - inventory) / current_liabilities),
                    'Current Ratio': format_decimal(current_assets / current_liabilities)
                })
        
        logger.debug(f"Calculated {period} metrics: {metrics}")
        return metrics
        
    except Exception as e:
        logger.error(f"Error calculating {period.lower()} metrics: {e}", exc_info=True)
        return metrics

def generate_calculation_details(data: pd.Series, period: str) -> Dict:
    """Generate calculation details for transparency"""
    return {
        'Raw Values': {
            f'{period} Revenue': format_currency(data.get('revenue', 0)),
            f'{period} Net Income': format_currency(data.get('net_income', 0)),
            f'{period} Gross Profit': format_currency(data.get('gross_profit', 0)),
            f'{period} Operating Income': format_currency(data.get('operating_income', 0)),
            f'{period} Operating Cash Flow': format_currency(data.get('operating_cash_flow', 0)),
            'Total Assets': format_currency(data.get('total_assets', 0)),
            'Current Assets': format_currency(data.get('current_assets', 0)),
            'Current Liabilities': format_currency(data.get('current_liabilities', 0))
        },
        'Algorithms': generate_metric_formulas(period),
        'Formulas': generate_actual_calculations(data, period)
    }

def format_currency(value: float) -> str:
    """Format currency values with proper handling of None/zero"""
    try:
        if value is None or value == 0:
            return "$0.00"
        return f"${value:,.2f}"
    except Exception as e:
        logger.error(f"Error formatting currency: {e}")
        return "$0.00"

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
        logger.info(f"Generating financial report for {symbol}")
        
        # Always use the default results directory
        report_dir = os.path.join('public', 'results', f"{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        os.makedirs(report_dir, exist_ok=True)
        
        # Get latest date from data
        formatted_date = datetime.now().strftime('%Y-%m-%d')
        fiscal_quarter_date = formatted_date
        fiscal_year_date = formatted_date
        
        # Save individual statement files
        statement_types = {
            'quarterly_income': data.get('quarterly_financials', pd.DataFrame()),
            'annual_income': data.get('annual_financials', pd.DataFrame()),
            'quarterly_balance': data.get('quarterly_financials', pd.DataFrame()),
            'annual_balance': data.get('annual_financials', pd.DataFrame()),
            'quarterly_cash_flow': data.get('quarterly_financials', pd.DataFrame()),
            'annual_cash_flow': data.get('annual_financials', pd.DataFrame())
        }
        
        for name, df in statement_types.items():
            try:
                if not df.empty:
                    # Create a copy to avoid modifying original data
                    df_copy = df.copy()
                    
                    # Handle date columns safely
                    date_columns = ['date', 'end_date']
                    for col in date_columns:
                        if col in df_copy.columns:
                            # Convert dates safely
                            df_copy[col] = df_copy[col].apply(lambda x: 
                                pd.to_datetime(x, errors='coerce').strftime('%Y-%m-%d') 
                                if pd.notna(x) and x != 'N/A' 
                                else 'N/A'
                            )
                    
                    # Save to JSON
                    file_path = os.path.join(report_dir, f"{name}.json")
                    df_copy.to_json(file_path, orient='records', date_format='iso')
                    logger.info(f"Successfully saved {name}.json")
                    
                    # Update fiscal dates if available
                    if name == 'quarterly_income' and 'end_date' in df_copy.columns:
                        valid_dates = df_copy[df_copy['end_date'] != 'N/A']['end_date']
                        if not valid_dates.empty:
                            fiscal_quarter_date = valid_dates.iloc[0]
                    
                    if name == 'annual_income' and 'end_date' in df_copy.columns:
                        valid_dates = df_copy[df_copy['end_date'] != 'N/A']['end_date']
                        if not valid_dates.empty:
                            fiscal_year_date = valid_dates.iloc[0]
                            
            except Exception as e:
                logger.error(f"Error saving {name}.json: {e}", exc_info=True)
                continue
        
        # Save raw data
        try:
            raw_data_path = os.path.join(report_dir, 'raw_data.json')
            with open(raw_data_path, 'w') as f:
                # Convert DataFrames to records for JSON serialization
                serializable_data = {
                    k: v.to_dict('records') if isinstance(v, pd.DataFrame) else v
                    for k, v in data.items()
                }
                json.dump(serializable_data, f, indent=2, default=str)
            logger.info("Successfully saved raw_data.json")
        except Exception as e:
            logger.error(f"Error saving raw data: {e}", exc_info=True)
        
        # Setup Jinja2 environment
        env = Environment(loader=FileSystemLoader('templates'))
        template = env.get_template('financial_report.html')
        
        # Prepare report data with default values
        report_data = {
            'symbol': symbol,
            'company_info': {
                'name': metrics.get('name', 'N/A'),
                'description': metrics.get('description', 'N/A'),
                'sector': metrics.get('sector', 'N/A')
            },
            'dates': {
                'latest': formatted_date,
                'fiscal_quarter': fiscal_quarter_date,
                'fiscal_year': fiscal_year_date,
                'generated_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            },
            'metrics': {
                'Quarterly Metrics': {},
                'Annual Metrics': {},
                'Growth Metrics': {},
                'Valuation Metrics': {},
                'Liquidity Metrics': {}
            },
            'generated_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Only calculate metrics if we have the required data
        if ('quarterly_financials' in data and isinstance(data['quarterly_financials'], pd.DataFrame) and 
            'annual_financials' in data and isinstance(data['annual_financials'], pd.DataFrame)):
            report_data['metrics'] = calculate_financial_metrics(data)
        
        # Generate HTML
        html_content = template.render(**report_data)
        
        # Save report
        report_path = os.path.join(report_dir, 'index.html')
        with open(report_path, 'w') as f:
            f.write(html_content)
        
        # Generate and save metadata
        metadata = generate_metadata(
            symbol=symbol,
            timeframe="N/A",
            start_date=formatted_date,
            end_date=formatted_date,
            initial_capital=0,
            commission=0,
            report_type="financial",
            directory_name=os.path.basename(report_dir),
            additional_data={
                "status": "finished",
                "title": f"Financial Analysis - {symbol}"
            }
        )
        save_metadata(metadata, report_dir)
        
        return report_path
        
    except Exception as e:
        logger.error(f"Error generating financial report: {e}", exc_info=True)
        return None