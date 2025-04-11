#!/usr/bin/env python
"""
Daily Market Check - Generate a report with key market indicators
"""

import argparse
import os
import json
from datetime import datetime, timedelta
import pandas as pd
from jinja2 import Environment, FileSystemLoader
from utils.metadata_generator import generate_metadata, save_metadata
from utils.data_fetcher import fetch_interest_rates, fetch_market_indices

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Generate daily market check report')
    
    # Optional parameters with defaults
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
    # Create output directory if it doesn't exist
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_base_dir = os.path.join(script_dir, args.output_dir)
    os.makedirs(output_base_dir, exist_ok=True)
    
    # Create a timestamped directory for this report
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_dir_name = f"market_check_{timestamp}"
    report_dir = os.path.join(output_base_dir, report_dir_name)
    os.makedirs(report_dir, exist_ok=True)
    
    # Gather data
    current_time = datetime.now()
    data = {
        'generated_at': current_time.strftime('%Y-%m-%d %H:%M:%S'),
        'date': current_time.strftime('%B %d, %Y'),
        'current_year': current_time.year,  # Add current year for the footer
        'now': current_time.strftime('%Y-%m-%d %H:%M:%S')  # Add now for the footer
    }
    
    # Add interest rates if requested
    if args.include_rates:
        interest_rates = fetch_interest_rates()
        data['interest_rates'] = interest_rates
        print(f"DEBUG - Interest Rates: {interest_rates}")
    
    # Add market indices if requested
    if args.include_indices:
        indices = fetch_market_indices()
        data['indices'] = indices
        print(f"DEBUG - Market Indices: {indices}")
    
    # Add economic indicators if requested
    if args.include_economic:
        from utils.data_fetcher import fetch_economic_indicators, fetch_economic_history
        from utils.chart_generator import (
            generate_gdp_chart,
            generate_inflation_chart,
            generate_unemployment_chart,
            generate_bond_chart
        )
        
        economic_indicators = fetch_economic_indicators(force_refresh=args.force_refresh)
        data['economic_indicators'] = economic_indicators
        
        try:
            # Fetch data
            gdp_data = fetch_economic_history('A191RL1Q225SBEA', 12, args.force_refresh)
            inflation_data = fetch_economic_history('CPIAUCSL', 24, args.force_refresh)
            unemployment_data = fetch_economic_history('UNRATE', 24, args.force_refresh)
            bond_data = fetch_economic_history('DGS10', 24, args.force_refresh)
            print(f"DEBUG - Bond data fetched: {bond_data}")  # Debug print
            
            # Generate charts
            data['gdp_chart_path'] = generate_gdp_chart(gdp_data, report_dir)
            data['inflation_chart_path'] = generate_inflation_chart(inflation_data, report_dir)
            data['unemployment_chart_path'] = generate_unemployment_chart(unemployment_data, report_dir)
            data['bond_chart_path'] = generate_bond_chart(bond_data, report_dir)
            print(f"DEBUG - Bond chart generated at: {data['bond_chart_path']}")  # Debug print
            
            # Store data for template
            data['gdp_history'] = gdp_data
            data['inflation_history'] = inflation_data
            data['unemployment_history'] = unemployment_data
            data['bond_history'] = bond_data
            
        except Exception as e:
            print(f"ERROR - Failed to process economic data: {e}")
    
    # Get the templates directory
    templates_dir = os.path.join(script_dir, 'templates')
    env = Environment(loader=FileSystemLoader(templates_dir))
    
    # Add a custom filter to handle non-serializable objects
    def safe_tojson(obj):
        class CustomEncoder(json.JSONEncoder):
            def default(self, obj):
                if callable(obj):
                    return str(obj)
                try:
                    return json.JSONEncoder.default(self, obj)
                except TypeError:
                    return str(obj)
        
        return json.dumps(obj, cls=CustomEncoder)
    
    env.filters['safe_tojson'] = safe_tojson
    
    # Load the template
    template = env.get_template('market_check.html')
    
    # Debug data being passed to template
    print(f"DEBUG - Template Data Keys: {data.keys()}")
    
    # Render the template with our data
    report_html = template.render(**data)
    
    # Save the report to the specified file in the output directory
    report_path = os.path.join(report_dir, "index.html")
    with open(report_path, 'w') as f:
        f.write(report_html)
    
    # Create metadata for the dashboard
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
    
    # Generate the dashboard
    try:
        from utils.dashboard_generator import generate_dashboard_only
        dashboard_path = generate_dashboard_only()
        print(f"Dashboard updated at: {dashboard_path}")
    except Exception as e:
        print(f"Warning: Could not update dashboard: {e}")
    
    print(f"Market check report generated at: {report_path}")
    return report_path

def main():
    """Main function to run the market check report."""
    args = parse_args()
    report_path = create_market_report(args)
    print(f"To view the report, run: python -m utils.dashboard_generator")
    print("Or access it via: http://localhost:8000/ (if server is already running)")

if __name__ == "__main__":
    main() 