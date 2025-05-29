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
    """Calculate financial metrics from statements with strict validation"""
    try:
        logger.info("Starting to calculate financial metrics")
        
        metrics = {
            'Quarterly Metrics': {},
            'Annual Metrics': {},
            'Descriptions': {},
            'Annual Descriptions': {},
            'Calculations': {'Raw Values': {}, 'Formulas': {}},
            'Annual Calculations': {'Raw Values': {}, 'Algorithms': {}, 'Formulas': {}}
        }

        # Handle quarterly metrics
        q_financials = data.get('quarterly_financials')
        if not (q_financials is None or q_financials.empty):
            current_q = q_financials.iloc[0] if not q_financials.empty else None
            
            if current_q is not None:
                # Get base values
                revenue = current_q.get('revenue', 0) or 0
                gross_profit = current_q.get('gross_profit', 0) or 0
                operating_income = current_q.get('operating_income', 0) or 0
                net_income = current_q.get('net_income', 0) or 0
                operating_cash_flow = current_q.get('operating_cash_flow', 0) or 0
                current_assets = current_q.get('current_assets', 0) or 0
                current_liabilities = current_q.get('current_liabilities', 1) or 1
                inventory = current_q.get('inventory', 0) or 0
                interest_expense = current_q.get('interest_expense', 0) or 0
                capex = current_q.get('capital_expenditure', 0) or 0
                
                # Store raw values for transparency (only the ones we use)
                metrics['Calculations']['Raw Values'] = {
                    'Revenue': f"{revenue:,.2f}",
                    'Gross Profit': f"{gross_profit:,.2f}",
                    'Operating Income': f"{operating_income:,.2f}",
                    'Net Income': f"{net_income:,.2f}",
                    'Operating Cash Flow': f"{operating_cash_flow:,.2f}",
                    'Current Assets': f"{current_assets:,.2f}",
                    'Current Liabilities': f"{current_liabilities:,.2f}"
                }
                
                # Store formulas for transparency
                metrics['Calculations']['Formulas'] = {
                    'Gross Margin': f"Gross Profit / Revenue = ${gross_profit:,.2f} / ${revenue:,.2f}",
                    'Operating Margin': f"Operating Income / Revenue = ${operating_income:,.2f} / ${revenue:,.2f}",
                    'Net Margin': f"Net Income / Revenue = ${net_income:,.2f} / ${revenue:,.2f}",
                    'FCF Margin': f"(Operating Cash Flow - CapEx) / Revenue = (${operating_cash_flow:,.2f} - ${capex:,.2f}) / ${revenue:,.2f}",
                    'Operating Cash Ratio': f"Operating Cash Flow / Current Liabilities = ${operating_cash_flow:,.2f} / ${current_liabilities:,.2f}",
                    'Interest Coverage': f"Operating Income / Interest Expense = ${operating_income:,.2f} / ${abs(interest_expense):,.2f}",
                    'Quick Ratio': f"(Current Assets - Inventory) / Current Liabilities = (${current_assets:,.2f} - ${inventory:,.2f}) / ${current_liabilities:,.2f}",
                    'Current Ratio': f"Current Assets / Current Liabilities = ${current_assets:,.2f} / ${current_liabilities:,.2f}"
                }
                
                # Calculate metrics
                metrics['Quarterly Metrics'].update({
                    'Gross Margin': format_percentage(gross_profit / revenue if revenue != 0 else None),
                    'Operating Margin': format_percentage(operating_income / revenue if revenue != 0 else None),
                    'Net Margin': format_percentage(net_income / revenue if revenue != 0 else None),
                    'FCF Margin': format_percentage((operating_cash_flow - capex) / revenue if revenue != 0 else None),
                    'Operating Cash Ratio': format_decimal(operating_cash_flow / current_liabilities),
                    'Interest Coverage': format_decimal(operating_income / abs(interest_expense) if interest_expense != 0 else None),
                    'Quick Ratio': format_decimal((current_assets - inventory) / current_liabilities),
                    'Current Ratio': format_decimal(current_assets / current_liabilities)
                })
                
                # Add descriptions
                metrics['Descriptions'] = {
                    'Gross Margin': 'Percentage of revenue remaining after direct costs, indicating pricing power and production efficiency',
                    'Operating Margin': 'Percentage of revenue remaining after operating expenses, showing operational efficiency',
                    'Net Margin': 'Percentage of revenue converted to profit, indicating overall profitability',
                    'FCF Margin': 'Free cash flow as a percentage of revenue, showing cash generation efficiency',
                    'Operating Cash Ratio': 'Operating cash flow relative to current liabilities, indicating short-term debt coverage',
                    'Interest Coverage': 'Operating income relative to interest expenses, showing debt service capability',
                    'Quick Ratio': 'Liquid assets relative to current liabilities, indicating immediate solvency (excluding inventory)',
                    'Current Ratio': 'Current assets relative to current liabilities, showing short-term solvency'
                }

        # Handle annual metrics
        a_financials = data.get('annual_financials')
        if not (a_financials is None or a_financials.empty):
            current_a = a_financials.iloc[0] if not a_financials.empty else None
            
            if current_a is not None:
                # Get base annual values
                revenue = current_a.get('revenue', 0) or 0
                gross_profit = current_a.get('gross_profit', 0) or 0
                operating_income = current_a.get('operating_income', 0) or 0
                net_income = current_a.get('net_income', 0) or 0
                operating_cash_flow = current_a.get('operating_cash_flow', 0) or 0
                total_assets = current_a.get('total_assets', 0) or 0
                total_equity = current_a.get('total_equity', 0) or 0
                total_debt = current_a.get('total_debt', 0) or 0
                interest_expense = current_a.get('interest_expense', 0) or 0
                depreciation = current_a.get('depreciation_amortization', 0) or 0
                rd_expense = current_a.get('research_development', 0) or 0
                sga_expense = current_a.get('selling_general_administrative', 0) or 0
                capex = current_a.get('capital_expenditure', 0) or 0
                
                # Calculate invested capital
                invested_capital = total_equity + total_debt - (current_a.get('cash_equivalents', 0) or 0)
                
                # Store annual raw values
                metrics['Annual Calculations']['Raw Values'] = {
                    'Annual Revenue': f"${revenue:,.2f}",
                    'Annual Net Income': f"${net_income:,.2f}",
                    'Annual Gross Profit': f"${gross_profit:,.2f}",
                    'Annual Operating Income': f"${operating_income:,.2f}",
                    'Annual Operating Cash Flow': f"${operating_cash_flow:,.2f}",
                    'Total Assets': f"${total_assets:,.2f}",
                    'Total Equity': f"${total_equity:,.2f}",
                    'Invested Capital': f"${invested_capital:,.2f}",
                    'Interest Expense': f"${abs(interest_expense):,.2f}",
                    'Depreciation': f"${depreciation:,.2f}",
                    'R&D Expense': f"${rd_expense:,.2f}",
                    'SG&A Expense': f"${sga_expense:,.2f}"
                }

                # Calculate annual metrics
                metrics['Annual Metrics'] = {
                    'Annual Revenue': f"${revenue:,.2f}",
                    'Annual Net Income': f"${net_income:,.2f}",
                    'Gross Margin': format_percentage(gross_profit / revenue if revenue != 0 else None),
                    'Operating Margin': format_percentage(operating_income / revenue if revenue != 0 else None),
                    'Net Margin': format_percentage(net_income / revenue if revenue != 0 else None),
                    'FCF Margin': format_percentage((operating_cash_flow - capex) / revenue if revenue != 0 else None),
                    'Return on Assets (ROA)': format_percentage(net_income / total_assets if total_assets != 0 else None),
                    'Return on Equity (ROE)': format_percentage(net_income / total_equity if total_equity != 0 else None),
                    'Return on Invested Capital (ROIC)': format_percentage(operating_income * (1 - 0.21) / invested_capital if invested_capital != 0 else None),
                    'Interest Coverage Ratio': format_decimal(operating_income / abs(interest_expense) if interest_expense != 0 else None),
                    'Depreciation % of Revenue': format_percentage(depreciation / revenue if revenue != 0 else None),
                    'R&D % of Revenue': format_percentage(rd_expense / revenue if revenue != 0 else None),
                    'SG&A % of Revenue': format_percentage(sga_expense / revenue if revenue != 0 else None)
                }

                # Store annual calculation formulas
                metrics['Annual Calculations']['Algorithms'] = {
                    'Gross Margin': 'Annual Gross Profit / Annual Revenue',
                    'Operating Margin': 'Annual Operating Income / Annual Revenue',
                    'Net Margin': 'Annual Net Income / Annual Revenue',
                    'FCF Margin': '(Annual Operating Cash Flow - Annual CapEx) / Annual Revenue',
                    'Return on Assets': 'Annual Net Income / Total Assets',
                    'Return on Equity': 'Annual Net Income / Total Equity',
                    'Return on Invested Capital': 'Annual Operating Income * (1 - Tax Rate) / Invested Capital',
                    'Interest Coverage Ratio': 'Annual Operating Income / Interest Expense',
                    'Depreciation % of Revenue': 'Annual Depreciation / Annual Revenue',
                    'R&D % of Revenue': 'Annual R&D Expense / Annual Revenue',
                    'SG&A % of Revenue': 'Annual SG&A Expense / Annual Revenue'
                }

                # Store actual calculations
                metrics['Annual Calculations']['Formulas'] = {
                    'Gross Margin': f"${gross_profit:,.2f} / ${revenue:,.2f}",
                    'Operating Margin': f"${operating_income:,.2f} / ${revenue:,.2f}",
                    'Net Margin': f"${net_income:,.2f} / ${revenue:,.2f}",
                    'FCF Margin': f"(${operating_cash_flow:,.2f} - ${capex:,.2f}) / ${revenue:,.2f}",
                    'Return on Assets': f"${net_income:,.2f} / ${total_assets:,.2f}",
                    'Return on Equity': f"${net_income:,.2f} / ${total_equity:,.2f}",
                    'Return on Invested Capital': f"(${operating_income:,.2f} * 0.79) / ${invested_capital:,.2f}",
                    'Interest Coverage Ratio': f"${operating_income:,.2f} / ${abs(interest_expense):,.2f}",
                    'Depreciation % of Revenue': f"${depreciation:,.2f} / ${revenue:,.2f}",
                    'R&D % of Revenue': f"${rd_expense:,.2f} / ${revenue:,.2f}",
                    'SG&A % of Revenue': f"${sga_expense:,.2f} / ${revenue:,.2f}"
                }

        # Add descriptions for annual metrics
        metrics['Annual Descriptions'] = {
            'Annual Revenue': 'Total annual sales revenue',
            'Annual Net Income': 'Total annual profit after all expenses and taxes',
            'Gross Margin': 'Annual percentage of revenue remaining after direct costs',
            'Operating Margin': 'Annual percentage of revenue remaining after operating expenses',
            'Net Margin': 'Annual percentage of revenue converted to profit',
            'FCF Margin': 'Annual free cash flow as a percentage of revenue',
            'Return on Assets (ROA)': 'Annual net income relative to total assets, showing asset efficiency',
            'Return on Equity (ROE)': 'Annual net income relative to shareholder equity, showing equity efficiency',
            'Return on Invested Capital (ROIC)': 'Annual after-tax operating income relative to invested capital',
            'Interest Coverage Ratio': 'Annual operating income relative to interest expenses',
            'Depreciation % of Revenue': 'Annual depreciation and amortization as a percentage of revenue',
            'R&D % of Revenue': 'Annual research and development expenses as a percentage of revenue',
            'SG&A % of Revenue': 'Annual selling, general, and administrative expenses as a percentage of revenue'
        }

        return metrics

    except Exception as e:
        logger.error(f"Error in calculate_financial_metrics: {e}", exc_info=True)
        return {
            'Quarterly Metrics': {},
            'Annual Metrics': {},
            'Descriptions': {},
            'Annual Descriptions': {},
            'Calculations': {'Raw Values': {}, 'Formulas': {}},
            'Annual Calculations': {'Raw Values': {}, 'Algorithms': {}, 'Formulas': {}}
        }

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