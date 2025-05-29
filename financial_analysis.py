#!/usr/bin/env python
"""
Financial Analysis CLI Tool
Fetches and analyzes financial statements and key metrics
"""

import argparse
import os
import logging
from typing import Dict, List
from utils.data_fetcher import fetch_financial_statements, fetch_key_metrics
from utils.financial_report_generator import generate_financial_report

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def parse_args():
    parser = argparse.ArgumentParser(description='Financial Analysis CLI Tool')
    
    parser.add_argument('--symbols', type=str, nargs='+', required=True,
                      help='List of stock symbols (e.g., AAPL MSFT GOOGL)')
    parser.add_argument('--years', type=int, default=5,
                      help='Number of years of historical data to analyze')
    parser.add_argument('--output-dir', type=str, default='public/results',
                      help='Output directory for reports')
    
    return parser.parse_args()

def main():
    args = parse_args()
    
    # Create default output directory
    os.makedirs('public/results', exist_ok=True)
    
    for symbol in args.symbols:
        logger.info(f"Analyzing {symbol}...")
        
        # Fetch data
        financial_data = fetch_financial_statements(symbol, args.years)
        key_metrics = fetch_key_metrics(symbol)
        
        # Log available statements
        expected_statements = [
            'quarterly_financials', 
            'annual_financials'
        ]
        
        for statement in expected_statements:
            if statement in financial_data and financial_data[statement] is not None:
                logger.info(f"Found {statement} with shape: {financial_data[statement].shape}")
            else:
                logger.warning(f"Missing {statement}")
        
        if financial_data and key_metrics:
            # Generate report with default output directory
            report_path = generate_financial_report(
                symbol=symbol,
                data=financial_data,
                metrics=key_metrics
            )
            
            if report_path:
                logger.info(f"Report generated: {report_path}")
            else:
                logger.error(f"Failed to generate report for {symbol}")
        else:
            logger.error(f"Failed to analyze {symbol}")
    
    logger.info("Analysis complete!")
    logger.info("To view reports, run: python -m utils.dashboard_generator")
    logger.info("Or access via: http://localhost:8000/")

if __name__ == "__main__":
    main() 