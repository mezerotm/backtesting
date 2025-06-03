import os
from datetime import datetime
import logging
import json
from jinja2 import Environment, FileSystemLoader
from utils.metadata_generator import generate_metadata, save_metadata

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_market_report(data: dict, report_dir: str) -> str:
    """Generate market analysis report
    
    Args:
        data (dict): Market data dictionary containing indices, rates, etc.
        report_dir (str): Directory to save the report
        
    Returns:
        str: Path to generated report
    """
    try:
        logger.info("Starting market report generation")
        logger.info(f"Received data keys: {data.keys()}")
        
        # Create output directory if it doesn't exist
        os.makedirs(report_dir, exist_ok=True)
        
        # Get the templates directory relative to this file
        templates_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates')
        env = Environment(loader=FileSystemLoader(templates_dir))
        
        # Add custom filter for JSON serialization
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
        
        # Load and render the template
        template = env.get_template('market_check.html')
        report_html = template.render(**data)
        
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