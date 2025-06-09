"""
Market report generator for economic indicators and market data.
"""

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
from typing import Dict, Optional

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

def generate_market_report(data: Dict, output_dir: str) -> Optional[str]:
    """Generate market analysis report.
    
    Args:
        data (Dict): Dictionary containing all market data and chart paths
        output_dir (str): Directory to save the report
        
    Returns:
        Optional[str]: Path to generated report or None if failed
    """
    try:
        logger.info("Starting market report generation")
        logger.info(f"Received data keys: {data.keys()}")
        
        # Setup Jinja2 environment
        template_dir = os.path.join(os.path.dirname(__file__), '..')
        env = Environment(loader=FileSystemLoader(template_dir))
        
        # Add custom filter for JSON serialization
        env.filters['safe_tojson'] = lambda obj: json.dumps(obj, cls=CustomEncoder)
        
        # Prepare template data with proper data structures
        template_data = {
            'generated_at': data.get('generated_at'),
            'date': data.get('date'),
            'current_year': data.get('current_year'),
            'now': data.get('now'),
            'market_status': data.get('market_status', {}),
            'economic_events': data.get('economic_events', {}),
            'indices': data.get('indices', {}),
            'interest_rates': data.get('interest_rates', {}),
            'economic_indicators': data.get('economic_indicators', {}),
            'gdp_data': {
                'labels': data.get('gdp_data', {}).get('labels', []),
                'values': data.get('gdp_data', {}).get('values', [])
            },
            'inflation_data': {
                'labels': data.get('inflation_data', {}).get('labels', []),
                'values': data.get('inflation_data', {}).get('values', [])
            },
            'unemployment_data': {
                'labels': data.get('unemployment_data', {}).get('labels', []),
                'values': data.get('unemployment_data', {}).get('values', [])
            },
            'bond_data': {
                'labels': data.get('bond_data', {}).get('labels', []),
                'values': data.get('bond_data', {}).get('values', []),
                'values_2y': data.get('bond_data', {}).get('values_2y', [])
            }
        }
        
        # Generate charts if data is available
        if template_data['gdp_data']['values']:
            template_data['gdp_chart_path'] = generate_gdp_chart(template_data['gdp_data'], output_dir)
            
        if template_data['inflation_data']['values']:
            template_data['inflation_chart_path'] = generate_inflation_chart(template_data['inflation_data'], output_dir)
            
        if template_data['unemployment_data']['values']:
            template_data['unemployment_chart_path'] = generate_unemployment_chart(template_data['unemployment_data'], output_dir)
            
        if template_data['bond_data']['values']:
            template_data['bond_chart_path'] = generate_bond_chart(template_data['bond_data'], output_dir)
        
        # Load and render the template
        template = env.get_template('market/market_report.html')
        report_html = template.render(**template_data)
        
        # Save the report
        report_path = os.path.join(output_dir, "index.html")
        with open(report_path, 'w') as f:
            f.write(report_html)
        
        # Save raw data
        raw_data_path = os.path.join(output_dir, 'raw_data.json')
        with open(raw_data_path, 'w') as f:
            json.dump(data, f, indent=2, cls=CustomEncoder)
            
        logger.info(f"Report generated at: {report_path}")
        return report_path
        
    except Exception as e:
        logger.error(f"Error generating market report: {e}", exc_info=True)
        return None 