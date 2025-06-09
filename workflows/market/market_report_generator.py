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
    generate_bond_chart
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

        # --- Extract VIX value from indices ---
        vix_value = None
        indices = data.get('indices', {})
        for group in indices.values():
            for idx in group:
                if idx.get('name') == 'VIX':
                    vix_value = idx.get('value')

        # Prepare template data
        template_data = {
            'date': datetime.now().strftime('%B %d, %Y'),
            'generated_at': datetime.now().strftime('%I:%M %p'),
            'market_status': data.get('market_status', {
                'status': 'Unknown',
                'hours': 'Status Unavailable'
            }),
            'economic_events': data.get('economic_events', {}).get('events', []),
            'indices': data.get('indices', {}),
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
            'market_movers': market_movers,
            'vix_value': vix_value,
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
            
        logger.info(f"Report generated at: {report_path}")
        return report_path
        
    except Exception as e:
        logger.error(f"Error generating market report: {e}", exc_info=True)
        raise 