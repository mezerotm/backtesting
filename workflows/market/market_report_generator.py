import os
from datetime import datetime
import logging
import json
from jinja2 import Environment, FileSystemLoader
from workflows.metadata_generator import generate_metadata, save_metadata
from workflows.market.market_chart_generator import (
    generate_gdp_chart,
    generate_inflation_chart,
    generate_unemployment_chart,
    generate_bond_chart,
    generate_market_index_chart,
    generate_style_box_heatmap
)
from typing import Dict
from workflows.market.market_data import MarketDataFetcher

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define CustomEncoder class at module level
class CustomEncoder(json.JSONEncoder):
    def default(self, obj):
        if callable(obj):
            return str(obj)
        try:
            return json.JSONEncoder.default(self, obj)
        except TypeError:
            return str(obj)

def generate_market_report(data: dict, report_dir: str, force_refresh: bool = False) -> str:
    """Generate market analysis report
    
    Args:
        data (dict): Market data dictionary containing indices, rates, etc.
        report_dir (str): Directory to save the report
        force_refresh (bool): Whether to force refresh cached data
        
    Returns:
        str: Path to generated report
    """
    try:
        logger.info("Starting market report generation")
        logger.info(f"Received data keys: {data.keys()}")
        
        # Create output directory if it doesn't exist
        os.makedirs(report_dir, exist_ok=True)
        
        # Get the templates directory relative to this file
        template_dirs = [
            os.path.dirname(__file__),  # current dir
            os.path.dirname(os.path.dirname(__file__)),  # parent dir
        ]
        env = Environment(loader=FileSystemLoader(template_dirs))
        
        # Add custom filter for JSON serialization
        env.filters['safe_tojson'] = lambda obj: json.dumps(obj, cls=CustomEncoder)
        
        # --- Fetch top movers and news ---
        fetcher = MarketDataFetcher()
        market_movers = fetcher.fetch_top_movers_and_news()

        # --- Fetch today's events (top movers + news) ---
        todays_events = fetcher.fetch_todays_events()

        # --- Extract VIX value from indices ---
        vix_value = None
        indices = data.get('indices', {})
        for group in indices.values():
            for idx in group:
                if idx.get('name') == 'VIX':
                    vix_value = idx.get('value')

        # --- Extract Market Sentiment Data ---
        sentiment_data = {}
        # Helper to find by name in all groups
        def find_index(name):
            for group in indices.values():
                for idx in group:
                    if idx.get('name') == name:
                        return idx
            return None
        for key, label in [
            ('dxy', 'Dollar Index'),
            ('oil', 'Oil (WTI)'),
            ('spy', 'S&P 500'),
            ('vix', 'VIX'),
            ('ten_year', '10Y Treasury'),
        ]:
            idx = find_index(label)
            if idx:
                sentiment_data[key] = {
                    'name': label,
                    'value': idx.get('value'),
                    'change': idx.get('change'),
                    'direction': idx.get('direction'),
                }

        # --- Generate market index charts ---
        market_index_charts = {}
        # Map display names to tickers
        index_tickers = {
            'S&P 500': 'SPY',
            'Dow Jones': 'DIA',
            'Nasdaq-100': 'QQQ',
            'S&P 400 MidCap': 'MDY',
            'Russell 2000': 'IWM',
            'S&P 500 Growth': 'IVW',
            'S&P 500 Value': 'IVE',
            'Dollar Index': 'UUP',
            'Oil (WTI)': 'USO',
            'VIX': 'VIXY',
        }
        for group, group_indices in indices.items():
            for idx in group_indices:
                name = idx.get('name')
                ticker = index_tickers.get(name)
                if ticker:
                    hist_data = fetcher.fetch_index_history(ticker, periods=60)
                    chart_path = generate_market_index_chart(hist_data, report_dir, name)
                    market_index_charts[name] = chart_path

        # Remove 10Y and 2Y Treasury from the 'Rates' group in indices to avoid duplicate rendering
        if 'Rates' in indices:
            indices['Rates'] = [idx for idx in indices['Rates'] if idx.get('name') not in ['10Y Treasury', '2Y Treasury']]

        # --- Use style box heatmap path from data if present, else generate ---
        style_box_heatmap_path = data.get('style_box_heatmap_path')
        if not style_box_heatmap_path:
            style_box_data = fetcher.fetch_style_box_etf_data()
            if style_box_data and style_box_data.get('z'):
                style_box_heatmap_path = generate_style_box_heatmap(style_box_data, report_dir)

        # Prepare template data
        template_data = {
            'date': datetime.now().strftime('%B %d, %Y'),
            'generated_at': datetime.now().strftime('%I:%M %p'),
            'market_status': data.get('market_status', {
                'status': 'Unknown',
                'hours': 'Status Unavailable'
            }),
            'economic_events': data.get('economic_events', {}).get('events', []),
            'indices': indices,
            'interest_rates': data.get('interest_rates', {}),
            'economic_indicators': data.get('economic_indicators', {}),
            'gdp_history': data.get('gdp_history', {}),
            'inflation_history': data.get('inflation_history', {}),
            'unemployment_history': data.get('unemployment_history', {}),
            'bond_history': data.get('bond_history', {}),
            'gdp_data': data.get('gdp_history', {}),
            'inflation_data': data.get('inflation_history', {}),
            'unemployment_data': data.get('unemployment_history', {}),
            'bond_data': data.get('bond_history', {}),
            'todays_events': todays_events,
            'sentiment_data': sentiment_data,
            'vix_value': sentiment_data.get('vix', {}).get('value'),
            'market_index_charts': market_index_charts,
            'ten_year_chart_path': data.get('ten_year_chart_path'),
            'two_year_chart_path': data.get('two_year_chart_path'),
            'style_box_heatmap_path': style_box_heatmap_path,
        }
        
        # Generate charts if data is available
        if 'gdp_history' in data and data['gdp_history'].get('values'):
            template_data['gdp_chart_path'] = generate_gdp_chart(data['gdp_history'], report_dir)
            
        if 'inflation_history' in data and data['inflation_history'].get('values'):
            template_data['inflation_chart_path'] = generate_inflation_chart(data['inflation_history'], report_dir)
            
        if 'unemployment_history' in data and data['unemployment_history'].get('values'):
            template_data['unemployment_chart_path'] = generate_unemployment_chart(data['unemployment_history'], report_dir)
            
        if 'bond_history' in data and data['bond_history'].get('values'):
            template_data['bond_chart_path'] = generate_bond_chart(data['bond_history'], report_dir)
        
        # Load and render the template (use market_report.html)
        template = env.get_template('market_report.html')
        report_html = template.render(**template_data)
        
        # Save the report
        report_path = os.path.join(report_dir, "index.html")
        with open(report_path, 'w') as f:
            f.write(report_html)
        
        # Save raw data
        raw_data_path = os.path.join(report_dir, 'raw_data.json')
        with open(raw_data_path, 'w') as f:
            json.dump(data, f, indent=2, cls=CustomEncoder)
            
        # Generate and save metadata
        current_date = datetime.now().strftime('%Y-%m-%d')
        metadata = generate_metadata(
            symbol="MARKET",
            timeframe="snapshot",
            start_date=current_date,
            end_date=current_date,
            initial_capital=0,
            commission=0,
            report_type="market",
            directory_name=os.path.basename(report_dir),
            additional_data={
                "status": "finished",
                "title": "Daily Market Check",
                "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "report_type": "snapshot"
            }
        )
        save_metadata(metadata, report_dir)
            
        logger.info(f"Report generated at: {report_path}")
        return report_path
        
    except Exception as e:
        logger.error(f"Error generating market report: {e}", exc_info=True)
        raise 