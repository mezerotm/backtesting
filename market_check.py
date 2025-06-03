#!/usr/bin/env python
"""
Daily Market Check - Generate a report with key market indicators
"""

import argparse
import os
from datetime import datetime
import logging
from utils.market_report_generator import generate_market_report
from utils.metadata_generator import generate_metadata, save_metadata
from utils.data_fetcher import fetch_interest_rates, fetch_market_indices

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Generate daily market check report')
    
    parser.add_argument('--output-dir', type=str, default='public/results',
                      help='Directory to save the report (default: public/results)')
    parser.add_argument('--include-rates', action='store_true', default=True,
                      help='Include interest rate data')
    parser.add_argument('--include-indices', action='store_true', default=True,
                      help='Include major market indices')
    parser.add_argument('--include-economic', action='store_true', default=True,
                      help='Include economic indicators')
    parser.add_argument('--force-refresh', action='store_true', default=False,
                      help='Force refresh of data (bypass cache)')
    
    return parser.parse_args()

def create_market_report(args):
    """Generate the daily market check report."""
    # Create output directory structure
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_base_dir = os.path.join(script_dir, args.output_dir)
    os.makedirs(output_base_dir, exist_ok=True)
    
    # Create timestamped directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_dir_name = f"market_check_{timestamp}"
    report_dir = os.path.join(output_base_dir, report_dir_name)
    
    # Gather data
    current_time = datetime.now()
    data = {
        'generated_at': current_time.strftime('%Y-%m-%d %H:%M:%S'),
        'date': current_time.strftime('%B %d, %Y'),
        'current_year': current_time.year,
        'now': current_time.strftime('%Y-%m-%d %H:%M:%S')
    }
    
    # Fetch market data based on arguments
    if args.include_rates:
        data['interest_rates'] = fetch_interest_rates()
        logger.info("Fetched interest rates data")
    
    if args.include_indices:
        data['indices'] = fetch_market_indices()
        logger.info("Fetched market indices data")
    
    if args.include_economic:
        from utils.data_fetcher import fetch_economic_indicators, fetch_economic_history
        from utils.chart_generator import (
            generate_gdp_chart,
            generate_inflation_chart,
            generate_unemployment_chart,
            generate_bond_chart
        )
        
        # Fetch economic indicators and history
        data['economic_indicators'] = fetch_economic_indicators(force_refresh=args.force_refresh)
        
        try:
            # Fetch historical data
            gdp_data = fetch_economic_history('A191RL1Q225SBEA', 12, args.force_refresh)
            inflation_data = fetch_economic_history('CPIAUCSL', 24, args.force_refresh)
            unemployment_data = fetch_economic_history('UNRATE', 24, args.force_refresh)
            bond_data = fetch_economic_history('DGS10', 24, args.force_refresh)
            
            # Generate charts
            data['gdp_chart_path'] = generate_gdp_chart(gdp_data, report_dir)
            data['inflation_chart_path'] = generate_inflation_chart(inflation_data, report_dir)
            data['unemployment_chart_path'] = generate_unemployment_chart(unemployment_data, report_dir)
            data['bond_chart_path'] = generate_bond_chart(bond_data, report_dir)
            
            # Store historical data
            data.update({
                'gdp_history': gdp_data,
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
        start_date=current_time.strftime('%Y-%m-%d'),
        end_date=current_time.strftime('%Y-%m-%d'),
        initial_capital=0,
        commission=0,
        report_type="market_check",
        directory_name=report_dir_name,
        additional_data={
            "status": "finished",
            "report_type": "market_check",
            "title": f"Market Check - {current_time.strftime('%Y-%m-%d')}"
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