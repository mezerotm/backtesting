import os
from datetime import datetime
import logging
import json
from jinja2 import Environment, FileSystemLoader
from utils.metadata_generator import generate_metadata, save_metadata
import plotly.graph_objects as go
from typing import Dict

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
        templates_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates')
        env = Environment(loader=FileSystemLoader(templates_dir))
        
        # Add custom filter for JSON serialization
        env.filters['safe_tojson'] = lambda obj: json.dumps(obj, cls=CustomEncoder)
        
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

def generate_gdp_chart(data: Dict, output_dir: str) -> str:
    """Generate GDP chart"""
    try:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=data['labels'],
            y=data['values'],
            mode='lines+markers',
            name='GDP Growth Rate'
        ))
        
        fig.update_layout(
            title='GDP Growth Rate Over Time',
            xaxis_title='Date',
            yaxis_title='Growth Rate (%)',
            template='plotly_dark'
        )
        
        chart_path = os.path.join(output_dir, 'gdp_chart.html')
        fig.write_html(chart_path)
        return os.path.basename(chart_path)
        
    except Exception as e:
        logger.error(f"Error generating GDP chart: {e}")
        return None

def generate_inflation_chart(data: Dict, output_dir: str) -> str:
    """Generate inflation chart"""
    try:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=data['labels'],
            y=data['values'],
            mode='lines+markers',
            name='Inflation Rate'
        ))
        
        fig.update_layout(
            title='Inflation Rate Over Time',
            xaxis_title='Date',
            yaxis_title='Rate (%)',
            template='plotly_dark'
        )
        
        chart_path = os.path.join(output_dir, 'inflation_chart.html')
        fig.write_html(chart_path)
        return os.path.basename(chart_path)
        
    except Exception as e:
        logger.error(f"Error generating inflation chart: {e}")
        return None

def generate_unemployment_chart(data: Dict, output_dir: str) -> str:
    """Generate unemployment chart"""
    try:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=data['labels'],
            y=data['values'],
            mode='lines+markers',
            name='Unemployment Rate'
        ))
        
        fig.update_layout(
            title='Unemployment Rate Over Time',
            xaxis_title='Date',
            yaxis_title='Rate (%)',
            template='plotly_dark'
        )
        
        chart_path = os.path.join(output_dir, 'unemployment_chart.html')
        fig.write_html(chart_path)
        return os.path.basename(chart_path)
        
    except Exception as e:
        logger.error(f"Error generating unemployment chart: {e}")
        return None

def generate_bond_chart(data: Dict, output_dir: str) -> str:
    """Generate bond yield chart"""
    try:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=data['labels'],
            y=data['values'],
            mode='lines+markers',
            name='10-Year Treasury Yield'
        ))
        
        fig.update_layout(
            title='10-Year Treasury Yield Over Time',
            xaxis_title='Date',
            yaxis_title='Yield (%)',
            template='plotly_dark'
        )
        
        chart_path = os.path.join(output_dir, 'bond_chart.html')
        fig.write_html(chart_path)
        return os.path.basename(chart_path)
        
    except Exception as e:
        logger.error(f"Error generating bond chart: {e}")
        return None 