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
import logging
from server.services.report_workflow_service import generate_financial_report as _service_generate

logger = logging.getLogger(__name__)

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
    """Generate the financial analysis report for a symbol — delegates to the report workflow service."""
    logger.info("Financial report generation requested via CLI for %s", symbol)
    return _service_generate(
        symbol=symbol,
        output_dir=args.output_dir,
        force_refresh=args.force_refresh,
    )

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