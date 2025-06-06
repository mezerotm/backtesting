#!/usr/bin/env python
"""
Financial Analysis CLI Tool
Fetches and analyzes financial statements and key metrics from Polygon
"""

import argparse
import os
import logging
import json
import pandas as pd
from typing import Dict, List
from utils.data_fetchers.market_data import MarketDataFetcher
from utils.financial_report_generator import generate_financial_report

# Update logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('financial_analysis.log')
    ]
)

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
            # Initialize market data fetcher
            market_data = MarketDataFetcher()
            
            # Fetch financial statements
            financial_data = {
                'quarterly_financials': market_data.fetch_polygon_financials(symbol, "quarterly", args.years * 4),
                'annual_financials': market_data.fetch_polygon_financials(symbol, "annual", args.years)
            }
            logger.info(f"Fetched financial data keys: {financial_data.keys()}")
            
            # Fetch company metrics
            company_metrics = market_data.fetch_polygon_fundamentals(symbol)
            logger.info(f"Fetched company metrics: {company_metrics}")
            
            # Add fundamentals data to the report data
            report_data = {
                **financial_data,
                'fundamentals': company_metrics,
                **{'name': company_metrics.get('name', symbol),
                   'sector': company_metrics.get('sector', 'N/A'),
                   'description': company_metrics.get('description', 'N/A'),
                   'exchange': company_metrics.get('exchange', 'N/A')}
            }
            
            logger.info(f"Combined report data keys: {report_data.keys()}")
            
            # Generate report
            report_path = generate_financial_report(
                symbol=symbol,
                data=report_data,
                metrics=company_metrics
            )
            
            if report_path:
                logger.info(f"Report generated: {report_path}")
                metrics_file = os.path.join(os.path.dirname(report_path), 'metrics.json')
                if os.path.exists(metrics_file):
                    logger.info(f"Successfully saved metrics to {metrics_file}")
            else:
                logger.error(f"Failed to generate report for {symbol}")
                
        except Exception as e:
            logger.error(f"Error processing {symbol}: {e}", exc_info=True)
            continue

if __name__ == "__main__":
    main() 