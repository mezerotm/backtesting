#!/usr/bin/env python
"""
Financial Analysis CLI Tool
Fetches and analyzes financial statements and key metrics
"""

import argparse
import os
import logging
import json
import pandas as pd
from typing import Dict, List
from utils.data_fetcher import fetch_financial_statements, fetch_key_metrics, fetch_market_indices, fetch_economic_indicators
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
    
    for symbol in args.symbols:
        logger.info(f"Analyzing {symbol}...")
        
        try:
            # Fetch financial data
            financial_data = fetch_financial_statements(symbol, args.years)
            
            # Fetch company metrics
            company_metrics = fetch_key_metrics(symbol)
            
            # Add market data
            market_data = {
                'market_indices': fetch_market_indices(),
                'economic_indicators': fetch_economic_indicators()
            }
            
            # Combine all data for report generation
            report_data = {
                **financial_data,
                **company_metrics,
                **market_data
            }
            
            # Generate report
            report_path = generate_financial_report(
                symbol=symbol,
                data=report_data,
                metrics=company_metrics
            )
            
            if report_path:
                logger.info(f"Report generated: {report_path}")
                # Verify and log the metrics file
                metrics_file = os.path.join(os.path.dirname(report_path), 'metrics.json')
                if os.path.exists(metrics_file):
                    with open(metrics_file, 'r') as f:
                        metrics = json.load(f)
                    logger.info(f"Successfully saved metrics to {metrics_file}")
                    logger.debug(f"Metrics structure: {json.dumps(metrics, indent=2)}")
            else:
                logger.error(f"Failed to generate report for {symbol}")
                
        except Exception as e:
            logger.error(f"Error processing {symbol}: {e}", exc_info=True)
            continue

if __name__ == "__main__":
    main() 