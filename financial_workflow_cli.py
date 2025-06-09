#!/usr/bin/env python
"""
Financial Analysis Workflow CLI

This CLI orchestrates the financial analysis workflow which:
1. Fetches financial data including fundamentals, statements, and metrics
2. Generates financial charts and visualizations
3. Creates comprehensive financial reports with analysis
4. Integrates with the central dashboard

The workflow is designed to provide financial snapshots and analysis
through the following components:
- workflows/financial/financial_data.py: Data fetching and processing
- workflows/financial/financial_report_generator.py: Report generation
- workflows/financial/financial_chart_generator.py: Chart creation
- workflows/financial/financial_report.html: Report template

Usage:
    python financial_workflow_cli.py [--symbols SYMBOL1 SYMBOL2 ...] [--force-refresh] [--output-dir path/to/dir]
"""

import argparse
import os
from datetime import datetime
from workflows.financial.financial_data import FinancialDataFetcher
from workflows.financial.financial_report_generator import generate_financial_report

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Generate financial analysis report')
    
    parser.add_argument('--symbols', type=str, nargs='+', required=True,
                      help='Stock symbols to analyze')
    parser.add_argument('--output-dir', type=str, default='public/results',
                      help='Directory to save the report (default: public/results)')
    parser.add_argument('--force-refresh', action='store_true', default=False,
                      help='Force refresh of data (bypass cache)')
    
    return parser.parse_args()

def create_financial_report(symbol: str, args) -> str:
    """Generate the financial analysis report for a symbol."""
    # Create output directory structure
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_base_dir = os.path.join(script_dir, args.output_dir)
    
    # Create daily directory with today's date
    today = datetime.now().strftime("%Y%m%d")
    report_dir_name = f"financial_{symbol}_{today}"
    report_dir = os.path.join(output_base_dir, report_dir_name)
    
    # Check if report already exists and force_refresh is False
    if os.path.exists(report_dir) and not args.force_refresh:
        print(f"Report for {symbol} on {today} already exists and force_refresh is False. Using existing report.")
        return os.path.join(report_dir, "index.html")
    
    # Create directories
    os.makedirs(report_dir, exist_ok=True)
    
    # Create data fetcher
    data_fetcher = FinancialDataFetcher(force_refresh=args.force_refresh)
    
    # Fetch financial data
    print(f"Fetching financial data for {symbol}...")
    data = data_fetcher.fetch_financial_statements(symbol, 4)  # Get 4 years of data
    metrics = data_fetcher.fetch_key_metrics(symbol)
    
    # Generate report
    print(f"Generating financial report for {symbol}...")
    report_path = generate_financial_report(symbol, data, metrics)
    
    if not report_path:
        raise Exception(f"Failed to generate report for {symbol}")
    
    return report_path

def main():
    """Main function to run the financial analysis report."""
    args = parse_args()
    try:
        for symbol in args.symbols:
            report_path = create_financial_report(symbol, args)
            print(f"Financial report for {symbol} generated at: {report_path}")
    except Exception as e:
        print(f"Failed to generate financial report: {e}")
        exit(1)

if __name__ == "__main__":
    main() 