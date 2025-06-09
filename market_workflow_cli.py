#!/usr/bin/env python
"""
Market Analysis Workflow CLI

This CLI orchestrates the market analysis workflow which:
1. Fetches market data including GDP, inflation, unemployment, and bond yields
2. Generates market charts and visualizations
3. Creates comprehensive market reports with analysis
4. Integrates with the central dashboard

The workflow is designed to provide market snapshots and analysis
through the following components:
- workflows/market/market_data.py: Data fetching and processing
- workflows/market/market_report_generator.py: Report generation
- workflows/market/market_chart_generator.py: Chart creation
- workflows/market/market_report.html: Report template

Usage:
    python market_workflow_cli.py [--force-refresh] [--output-dir path/to/dir]
"""

import argparse
import os
from datetime import datetime
import logging
from workflows.market.market_data import MarketDataFetcher
from workflows.market.market_report_generator import (
    generate_market_report,
    generate_gdp_chart,
    generate_inflation_chart,
    generate_unemployment_chart,
    generate_bond_chart
)
from workflows.metadata_generator import generate_metadata, save_metadata

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Generate market analysis report')
    
    parser.add_argument('--output-dir', type=str, default='public/results',
                      help='Directory to save the report (default: public/results)')
    parser.add_argument('--force-refresh', action='store_true', default=False,
                      help='Force refresh of data (bypass cache)')
    
    return parser.parse_args()

def create_market_report(args) -> str:
    """Generate the market analysis report."""
    # Create output directory structure
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_base_dir = os.path.join(script_dir, args.output_dir)
    
    # Create timestamped directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_dir_name = f"market_{timestamp}"
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
    
    # Fetch additional data if your fetcher supports it
    if hasattr(data_fetcher, "fetch_interest_rates"):
        data['interest_rates'] = data_fetcher.fetch_interest_rates()
    if hasattr(data_fetcher, "fetch_market_indices"):
        data['indices'] = data_fetcher.fetch_market_indices()
    if hasattr(data_fetcher, "fetch_economic_indicators"):
        data['economic_indicators'] = data_fetcher.fetch_economic_indicators()
    
    try:
        # Fetch historical data
        gdp_growth_data = data_fetcher.get_gdp_data()
        inflation_data = data_fetcher.get_inflation_data()
        unemployment_data = data_fetcher.get_unemployment_data()
        bond_10y_data = data_fetcher.get_bond_data()
        bond_2y_data = bond_10y_data.get('values_2y', []) if bond_10y_data else []
        
        # Combine bond data if 2Y is available
        if bond_10y_data and bond_2y_data:
            bond_data = {
                'labels': bond_10y_data['labels'],
                'values': bond_10y_data['values'],
                'values_2y': bond_2y_data,
                'title': 'Treasury Yields'
            }
        else:
            bond_data = bond_10y_data
        
        # Only generate charts if we have data
        if gdp_growth_data and gdp_growth_data.get('values'):
            data['gdp_chart_path'] = generate_gdp_chart(gdp_growth_data, report_dir)
        if inflation_data and inflation_data.get('values'):
            data['inflation_chart_path'] = generate_inflation_chart(inflation_data, report_dir)
        if unemployment_data and unemployment_data.get('values'):
            data['unemployment_chart_path'] = generate_unemployment_chart(unemployment_data, report_dir)
        if bond_data and bond_data.get('values'):
            data['bond_chart_path'] = generate_bond_chart(bond_data, report_dir)
        
        # Store historical data
        data.update({
            'gdp_history': gdp_growth_data,
            'inflation_history': inflation_data,
            'unemployment_history': unemployment_data,
            'bond_history': bond_data
        })
        
        # Generate report
        logger.info("Generating market report...")
        report_path = generate_market_report(data, report_dir)
        
        if not report_path:
            raise Exception("Failed to generate market report")
        
        # Generate metadata
        metadata = generate_metadata(
            symbol="MARKET",
            timeframe="snapshot",
            start_date=datetime.now().strftime('%Y-%m-%d'),
            end_date=datetime.now().strftime('%Y-%m-%d'),
            initial_capital=0,
            commission=0,
            report_type="market",
            directory_name=report_dir_name,
            additional_data={
                "status": "finished",
                "title": f"Market Analysis - {datetime.now().strftime('%Y-%m-%d')}",
                "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "report_type": "snapshot"
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
        
    except Exception as e:
        logger.error(f"Failed to generate market report: {e}", exc_info=True)
        raise

def main():
    """Main function to run the market analysis report."""
    args = parse_args()
    try:
        report_path = create_market_report(args)
        print(f"Market report generated at: {report_path}")
        print(f"To view the report, run: python -m utils.dashboard_generator")
        print("Or access it via: http://localhost:8000/ (if server is already running)")
    except Exception as e:
        logger.error(f"Failed to generate market report: {e}", exc_info=True)
        exit(1)

if __name__ == "__main__":
    main() 