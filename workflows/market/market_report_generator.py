import os
from datetime import datetime
import logging
import json
from jinja2 import Environment, FileSystemLoader
from ..metadata_generator import generate_metadata, save_metadata
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
        templates_dir = os.path.dirname(__file__)
        parent_dir = os.path.dirname(templates_dir)
        env = Environment(loader=FileSystemLoader([templates_dir, parent_dir]))
        
        # Add custom filter for JSON serialization
        env.filters['safe_tojson'] = lambda obj: json.dumps(obj, cls=CustomEncoder)
        
        # Process inflation data for better visualization
        if 'inflation_history' in data and data['inflation_history'].get('values'):
            inflation_data = data['inflation_history']
            processed_inflation = []
            for i, (label, value) in enumerate(zip(inflation_data['labels'], inflation_data['values'])):
                try:
                    date = datetime.strptime(label, '%Y-%m-%d')
                    processed_inflation.append({
                        'date': date.strftime('%Y-%m'),
                        'value': round(float(value), 1),
                        'label': date.strftime('%b %Y')
                    })
                except Exception as e:
                    logger.error(f"Error processing inflation data point {i}: {e}")
            data['inflation_history'] = {
                'labels': [item['label'] for item in processed_inflation],
                'values': [item['value'] for item in processed_inflation],
                'dates': [item['date'] for item in processed_inflation]
            }
        
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
            'bond_history': data.get('bond_history', {})
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
        
        # Load and render the template
        template = env.get_template('market_check.html')
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

def generate_gdp_chart(data: Dict, output_dir: str) -> str:
    """Generate GDP growth rate chart"""
    try:
        values = data['values']
        
        # Log the raw values for debugging
        logger.info(f"GDP Chart Values: {values}")
        logger.info(f"GDP Chart Labels: {data['labels']}")
        
        # Validate and clean values
        cleaned_values = []
        cleaned_labels = []
        for i, (value, label) in enumerate(zip(values, data['labels'])):
            try:
                v = float(value)
                if abs(v) > 50:  # GDP growth rarely exceeds ±50%
                    logger.warning(f"Unusually high GDP growth value: {v}% at index {i}")
                    continue
                cleaned_values.append(v)
                cleaned_labels.append(label)
            except (ValueError, TypeError) as e:
                logger.error(f"Error processing GDP value at index {i}: {e}")
                continue
        
        if not cleaned_values:
            logger.error("No valid GDP values after cleaning")
            return None
        
        fig = go.Figure()
        
        # Add GDP growth rate bars with color based on value
        colors = ['rgba(74, 222, 128, 0.6)' if v > 3 else           # Strong growth (>3%): Green
                 'rgba(59, 130, 246, 0.6)' if 2 <= v <= 3 else      # Healthy growth (2-3%): Blue
                 'rgba(250, 204, 21, 0.6)' if 0 <= v < 2 else       # Low growth (0-2%): Yellow
                 'rgba(248, 113, 113, 0.6)' for v in cleaned_values] # Negative growth: Red
        
        fig.add_trace(go.Bar(
            x=cleaned_labels,
            y=cleaned_values,
            name='GDP Growth Rate',
            marker_color=colors,
            hovertemplate='%{x}<br>Growth Rate: %{y:.1f}%<extra></extra>'
        ))
        
        # Add trend line
        fig.add_trace(go.Scatter(
            x=cleaned_labels,
            y=cleaned_values,
            name='Trend',
            line=dict(color='rgba(255, 255, 255, 0.5)', dash='dot'),
            hovertemplate='%{x}<br>Growth Rate: %{y:.1f}%<extra></extra>'
        ))
        
        # Add healthy growth range (2-3%)
        fig.add_hrect(
            y0=2, y1=3,
            fillcolor="rgba(59, 130, 246, 0.1)",  # Light blue for the target range
            line_width=0
        )
        
        # Calculate reasonable y-axis range based on data
        min_val = min(cleaned_values)
        max_val = max(cleaned_values)
        padding = (max_val - min_val) * 0.1  # Add 10% padding
        y_range = [
            max(min_val - padding, -10),  # Don't go below -10%
            min(max_val + padding, 10)    # Don't go above 10%
        ]
        
        logger.info(f"GDP Chart Y-axis range: {y_range}")
        
        fig.update_layout(
            title='Real GDP Growth Rate (Quarterly, SAAR)',
            xaxis_title='Quarter',
            yaxis_title='Growth Rate (%)',
            template='plotly_dark',
            hovermode='x unified',
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ),
            yaxis=dict(
                range=y_range,
                dtick=1  # Show tick marks every 1%
            ),
            plot_bgcolor='rgb(13, 18, 30)',
            paper_bgcolor='rgb(13, 18, 30)'
        )
        
        chart_path = os.path.join(output_dir, 'gdp_chart.html')
        fig.write_html(chart_path)
        return os.path.basename(chart_path)
        
    except Exception as e:
        logger.error(f"Error generating GDP chart: {e}")
        return None

def generate_inflation_chart(data: Dict, output_dir: str) -> str:
    """Generate YoY inflation rate chart (expects already-calculated YoY values)."""
    try:
        values = data['values']
        dates = data['labels']
        # Only use the last 8 data points
        values = values[-8:]
        dates = dates[-8:]
        if not values or not dates or len(values) != len(dates):
            logger.error("No valid inflation YoY values or mismatched labels/values")
            return None
        fig = go.Figure()
        # Add YoY inflation bars with improved colors and opacity
        colors = []
        for v in values:
            if 1.8 <= v <= 2.2:  # Very close to target (2% ± 0.2%)
                colors.append('rgba(74, 222, 128, 1.0)')  # Bright green
            elif 1.5 <= v <= 2.5:  # Target range
                colors.append('rgba(74, 222, 128, 0.8)')  # Green
            elif 0 <= v < 1.5:  # Below target
                colors.append('rgba(250, 204, 21, 0.8)')  # Yellow
            elif 2.5 < v <= 3.5:  # Above target
                colors.append('rgba(251, 146, 60, 0.8)')  # Orange
            else:  # Far from target
                colors.append('rgba(248, 113, 113, 0.8)')  # Red
        fig.add_trace(go.Bar(
            x=dates,
            y=values,
            name='Inflation Rate YoY',
            marker_color=colors,
            marker_line_width=1,
            marker_line_color='rgba(255, 255, 255, 0.5)',
            hovertemplate='<b>%{x}</b><br>' +
                         'Inflation: %{y:.1f}%<br>' +
                         '<extra></extra>'
        ))
        # Add 2% Fed target line
        fig.add_hline(
            y=2,
            line_dash="dash",
            line_color="rgba(74, 222, 128, 1)",  # Bright green
            line_width=2
        )
        # Add target range with improved visibility
        fig.add_hrect(
            y0=1.5, y1=2.5,
            fillcolor="rgba(74, 222, 128, 0.1)",  # Very light green
            line_width=0
        )
        # Add trend line with improved visibility
        fig.add_trace(go.Scatter(
            x=dates,
            y=values,
            name='Trend',
            line=dict(
                color='rgba(255, 255, 255, 0.9)',  # Almost white
                width=2,
                dash='dot'
            ),
            hovertemplate='<b>%{x}</b><br>' +
                         'Trend: %{y:.1f}%<br>' +
                         '<extra></extra>'
        ))
        # Calculate reasonable y-axis range based on data
        min_val = min(values)
        max_val = max(values)
        padding = (max_val - min_val) * 0.2  # Increase padding to 20%
        y_range = [
            max(min_val - padding, -2),   # Don't go below -2%
            min(max_val + padding, 8)     # Don't go above 8%
        ]
        # Show only every 4th label on the x-axis
        step = 4
        tickvals = [dates[i] for i in range(0, len(dates), step)]
        ticktext = [dates[i] for i in range(0, len(dates), step)]
        # Update layout with improved readability
        fig.update_layout(
            title=dict(
                text='Inflation Rate (YoY) Over Time',
                font=dict(size=24, color='white'),
                y=0.95
            ),
            xaxis=dict(
                title='Date',
                title_font=dict(size=14),
                tickfont=dict(size=12),
                gridcolor='rgba(128, 128, 128, 0.2)',
                tickangle=0,  # horizontal
                tickvals=tickvals,
                ticktext=ticktext,
                showgrid=True,
                zeroline=True,
                zerolinecolor='rgba(255, 255, 255, 0.2)',
                zerolinewidth=1
            ),
            yaxis=dict(
                title='Inflation Rate (%)',
                title_font=dict(size=14),
                tickfont=dict(size=12),
                gridcolor='rgba(128, 128, 128, 0.2)',
                range=y_range,
                dtick=0.5,  # Show tick marks every 0.5%
                tickformat='.1f',
                showgrid=True,
                zeroline=True,
                zerolinecolor='rgba(255, 255, 255, 0.2)',
                zerolinewidth=1
            ),
            template='plotly_dark',
            hovermode='x unified',
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1,
                font=dict(size=12),
                bgcolor='rgba(0,0,0,0.5)'
            ),
            plot_bgcolor='rgb(13, 18, 30)',
            paper_bgcolor='rgb(13, 18, 30)',
            margin=dict(t=80, r=60, b=80, l=60),  # Increased bottom margin for annotations
            height=500  # Make chart taller
        )
        chart_path = os.path.join(output_dir, 'inflation_chart.html')
        fig.write_html(chart_path, config={'displayModeBar': True, 'displaylogo': False})
        return os.path.basename(chart_path)
    except Exception as e:
        logger.error(f"Error generating inflation chart: {e}")
        return None

def generate_unemployment_chart(data: Dict, output_dir: str) -> str:
    """Generate unemployment chart"""
    try:
        values = data['values']
        labels = data['labels']
        # Only use the last 8 data points
        values = values[-8:]
        labels = labels[-8:]
        fig = go.Figure()
        
        # Add unemployment rate bars with color based on value
        colors = ['rgba(74, 222, 128, 0.6)' if 3.5 <= v <= 4.5 else     # Optimal range (3.5-4.5%): Green
                 'rgba(250, 204, 21, 0.6)' if (3 <= v < 3.5) or (4.5 < v <= 5.5) else  # Near optimal: Yellow
                 'rgba(248, 113, 113, 0.6)' for v in values]             # High unemployment (>5.5%) or too low (<3%): Red
        
        fig.add_trace(go.Bar(
            x=labels,
            y=values,
            name='Unemployment Rate',
            marker_color=colors,
            hovertemplate='%{x}<br>Rate: %{y:.1f}%<extra></extra>'
        ))
        
        # Add trend line
        fig.add_trace(go.Scatter(
            x=labels,
            y=values,
            name='Trend',
            line=dict(color='rgba(255, 255, 255, 0.5)', dash='dot'),
            hovertemplate='%{x}<br>Rate: %{y:.1f}%<extra></extra>'
        ))
        
        # Add optimal range (3.5-4.5%)
        fig.add_hrect(
            y0=3.5, y1=4.5,
            fillcolor="rgba(74, 222, 128, 0.1)",
            line_width=0
        )
        
        fig.update_layout(
            title='Unemployment Rate Over Time',
            xaxis_title='Date',
            yaxis_title='Rate (%)',
            template='plotly_dark',
            hovermode='x unified',
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ),
            plot_bgcolor='rgb(13, 18, 30)',
            paper_bgcolor='rgb(13, 18, 30)'
        )
        
        chart_path = os.path.join(output_dir, 'unemployment_chart.html')
        fig.write_html(chart_path)
        return os.path.basename(chart_path)
        
    except Exception as e:
        logger.error(f"Error generating unemployment chart: {e}")
        return None

def generate_bond_chart(data: Dict, output_dir: str) -> str:
    """Generate bond yield chart with yield curve inversion indicator"""
    try:
        # We expect data to contain both 10Y and 2Y yields
        ten_year_values = data['values']
        two_year_values = data.get('values_2y', [])
        dates = data['labels']
        
        fig = go.Figure()
        
        # Add 10Y yield line
        fig.add_trace(go.Scatter(
            x=dates,
            y=ten_year_values,
            name='10Y Treasury Yield',
            line=dict(color='rgb(59, 130, 246)', width=2),  # Blue line
            hovertemplate='%{x}<br>10Y: %{y:.2f}%<extra></extra>'
        ))
        
        # Add 2Y yield line if available
        if two_year_values:
            fig.add_trace(go.Scatter(
                x=dates,
                y=two_year_values,
                name='2Y Treasury Yield',
                line=dict(color='rgb(147, 51, 234)', width=2),  # Purple line
                hovertemplate='%{x}<br>2Y: %{y:.2f}%<extra></extra>'
            ))
            
            # Calculate and add yield spread (10Y - 2Y)
            spreads = [ten_year_values[i] - two_year_values[i] for i in range(len(dates))]
            
            # Add spread as a line plot
            fig.add_trace(go.Scatter(
                x=dates,
                y=spreads,
                name='10Y-2Y Spread',
                line=dict(color='rgba(147, 51, 234, 0.5)', width=1, dash='dot'),
                hovertemplate='%{x}<br>Spread: %{y:.2f}%<extra></extra>'
            ))
            
            # Add inversion highlighting
            inversion_periods = []
            current_period = None
            
            # Find continuous inversion periods
            for i in range(len(dates)):
                if spreads[i] < 0:
                    if current_period is None:
                        current_period = {'start': dates[i]}
                elif current_period is not None:
                    current_period['end'] = dates[i]
                    inversion_periods.append(current_period)
                    current_period = None
            
            # Add the last period if it's still inverted
            if current_period is not None:
                current_period['end'] = dates[-1]
                inversion_periods.append(current_period)
            
            # Add shading for inversion periods
            for period in inversion_periods:
                fig.add_vrect(
                    x0=period['start'],
                    x1=period['end'],
                    fillcolor="rgba(248, 113, 113, 0.15)",  # Lighter red
                    line_width=0,
                    layer="below"
                )
            
            # Add zero line for spread reference
            fig.add_hline(
                y=0,
                line_dash="dash",
                line_color="rgba(255, 255, 255, 0.3)",
                line_width=1
            )
        
        fig.update_layout(
            title={
                'text': 'Treasury Yields and Spread Analysis (Weekly)',
                'y':0.95,
                'x':0.5,
                'xanchor': 'center',
                'yanchor': 'top'
            },
            xaxis_title='Date',
            yaxis_title='Yield (%)',
            template='plotly_dark',
            hovermode='x unified',
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ),
            plot_bgcolor='rgb(13, 18, 30)',
            paper_bgcolor='rgb(13, 18, 30)'
        )
        
        chart_path = os.path.join(output_dir, 'bond_chart.html')
        fig.write_html(chart_path)
        return os.path.basename(chart_path)
        
    except Exception as e:
        logger.error(f"Error generating bond chart: {e}")
        return None 