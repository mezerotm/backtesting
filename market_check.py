#!/usr/bin/env python
"""
Daily Market Check - Generate a report with key market indicators
"""

import argparse
import os
from datetime import datetime
import logging
from utils.market_report_generator import (
    generate_market_report,
    generate_gdp_chart,
    generate_inflation_chart,
    generate_unemployment_chart,
    generate_bond_chart
)
from utils.metadata_generator import generate_metadata, save_metadata
from utils.data_fetchers.market_data import MarketDataFetcher

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Generate daily market check report')
    
    parser.add_argument('--output-dir', type=str, default='public/results',
                      help='Directory to save the report (default: public/results)')
    parser.add_argument('--force-refresh', action='store_true', default=False,
                      help='Force refresh of data (bypass cache)')
    
    return parser.parse_args()

def create_market_report(args):
    """Generate the daily market check report."""
    # Create output directory structure
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_base_dir = os.path.join(script_dir, args.output_dir)
    
    # Create timestamped directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_dir_name = f"market_check_{timestamp}"
    report_dir = os.path.join(output_base_dir, report_dir_name)
    
    # Create directories
    os.makedirs(report_dir, exist_ok=True)
    
    # Create data fetcher
    data_fetcher = MarketDataFetcher(force_refresh=args.force_refresh)
    
    # Initialize data dictionary
    data = {
        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'date': datetime.now().strftime('%B %d, %Y'),
        'current_year': datetime.now().year,
        'now': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'gdp_chart_path': None,
        'inflation_chart_path': None,
        'unemployment_chart_path': None,
        'bond_chart_path': None
    }
    
    # Fetch market data
    data['interest_rates'] = data_fetcher.fetch_interest_rates()
    logger.info("Fetched interest rates data")
    
    data['indices'] = data_fetcher.fetch_market_indices()
    logger.info("Fetched market indices data")
    
    data['economic_indicators'] = data_fetcher.fetch_economic_indicators()
    
    try:
        # Fetch historical data
        gdp_growth_data = data_fetcher.fetch_economic_history('A191RL1Q225SBEA', 8)  # Real GDP Growth Rate, Quarterly
        inflation_data = data_fetcher.fetch_economic_history('CPIAUCSL', 24)  # Monthly data, 2 years for YoY calculation
        unemployment_data = data_fetcher.fetch_economic_history('UNRATE', 12)  # Monthly data, 1 year
        
        # Fetch both 10Y and 2Y bond data
        bond_10y_data = data_fetcher.fetch_economic_history('DGS10', 12)  # 10-year yield
        bond_2y_data = data_fetcher.fetch_economic_history('DGS2', 12)   # 2-year yield
        
        # Combine bond data
        if bond_10y_data and bond_2y_data:
            bond_data = {
                'labels': bond_10y_data['labels'],
                'values': bond_10y_data['values'],
                'values_2y': bond_2y_data['values'],
                'title': 'Treasury Yields'
            }
        else:
            bond_data = bond_10y_data  # Fallback to just 10Y if 2Y not available
        
        # Only generate charts if we have data
        if gdp_growth_data and gdp_growth_data['values']:
            data['gdp_chart_path'] = generate_gdp_chart(gdp_growth_data, report_dir)
        if inflation_data and inflation_data['values']:
            data['inflation_chart_path'] = generate_inflation_chart(inflation_data, report_dir)
        if unemployment_data and unemployment_data['values']:
            data['unemployment_chart_path'] = generate_unemployment_chart(unemployment_data, report_dir)
        if bond_data:
            data['bond_chart_path'] = generate_bond_chart(bond_data, report_dir)
        
        # Store historical data
        data.update({
            'gdp_history': gdp_growth_data,
            'inflation_history': inflation_data,
            'unemployment_history': unemployment_data,
            'bond_history': bond_data
        })
        
    except Exception as e:
        logger.error(f"Error processing economic data: {e}", exc_info=True)
    
    # Generate report using the dedicated generator
    report_path = generate_market_report(data, report_dir)
    
    # Generate metadata
    metadata = generate_metadata(
        symbol="MARKET",
        timeframe="daily",
        start_date=datetime.now().strftime('%Y-%m-%d'),
        end_date=datetime.now().strftime('%Y-%m-%d'),
        initial_capital=0,
        commission=0,
        report_type="market_check",
        directory_name=report_dir_name,
        additional_data={
            "status": "finished",
            "report_type": "market_check",
            "title": f"Market Check - {datetime.now().strftime('%Y-%m-%d')}"
        }
    )
    
    # Save metadata
    save_metadata(metadata, report_dir)
    
    # Update dashboard
    try:
        from utils.dashboard_generator import generate_dashboard_only
        dashboard_path = generate_dashboard_only()
        logger.info(f"Dashboard updated at: {dashboard_path}")
    except Exception as e:
        logger.warning(f"Could not update dashboard: {e}")
    
    return report_path

def main():
    """Main function to run the market check report."""
    args = parse_args()
    try:
        report_path = create_market_report(args)
        print(f"Market check report generated at: {report_path}")
        print(f"To view the report, run: python -m utils.dashboard_generator")
        print("Or access it via: http://localhost:8000/ (if server is already running)")
    except Exception as e:
        logger.error(f"Failed to generate market report: {e}", exc_info=True)
        exit(1)

if __name__ == "__main__":
    main() 