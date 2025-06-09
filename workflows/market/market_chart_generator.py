"""
Market chart generator for economic indicators and market data.
"""

import os
import json
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime
from typing import Dict, Optional

# Remove the debug print
# print("[DEBUG] market_chart_generator.py loaded, go is:", 'go' in globals())

def generate_gdp_chart(data: Dict, output_dir: str) -> Optional[str]:
    """Generate GDP chart using Plotly."""
    try:
        # Check if data is empty
        if not data.get('labels') or not data.get('values'):
            print("ERROR - GDP data is empty or missing labels/values")
            return None
        # Convert data for plotly
        chart_data = []
        labels = []
        values = []
        colors = []
        
        for i, (label, value) in enumerate(zip(data['labels'], data['values'])):
            try:
                if label and value is not None:
                    quarter = int(label[1])
                    year = int(label.split()[1])
                    labels.append(f"Q{quarter} {year}")
                    values.append(float(value))
                    colors.append('rgb(34, 197, 94)' if float(value) >= 0 else 'rgb(239, 68, 68)')
            except Exception as e:
                print(f"Error processing GDP data point {i}: {e}")

        # Create the bar chart
        fig = go.Figure(data=[
            go.Bar(
                x=labels,
                y=values,
                marker_color=colors,
                text=[f"{v:+.1f}%" for v in values],  # Show values with + or - sign
                textposition='outside',  # Place text above bars
                textfont={'size': 14, 'color': '#94a3b8'},  # Larger, visible text
                hovertemplate="<b>%{x}</b><br>" +
                            "GDP Growth: %{text}<br>" +
                            "<extra></extra>"  # Remove secondary box
            )
        ])

        # Update layout
        fig.update_layout(
            title={
                'text': 'Real GDP Growth',  # Simplified title
                'y': 0.95,
                'x': 0.5,
                'xanchor': 'center',
                'yanchor': 'top',
                'font': {'color': 'rgb(148, 163, 184)', 'size': 28}  # Brighter, larger title
            },
            plot_bgcolor='rgb(13, 18, 30)',
            paper_bgcolor='rgb(13, 18, 30)',
            font={'color': 'rgb(148, 163, 184)', 'size': 14},  # Brighter text
            showlegend=False,
            margin=dict(t=60, l=50, r=30, b=80),  # Increased bottom margin for dates
            xaxis=dict(
                showgrid=True,
                gridcolor='rgba(148, 163, 184, 0.1)',
                tickfont={'size': 12, 'color': 'rgb(148, 163, 184)'},  # Adjusted text size
                title=None,
                tickangle=45,  # Angled labels for better readability
                tickmode='array',
                ticktext=labels,
                tickvals=list(range(len(labels))),
            ),
            yaxis=dict(
                showgrid=True,
                gridcolor='rgba(148, 163, 184, 0.1)',
                zeroline=True,
                zerolinecolor='rgba(148, 163, 184, 0.5)',
                zerolinewidth=1,
                ticksuffix='%',
                tickfont={'size': 12, 'color': 'rgb(148, 163, 184)'},
                title={'text': 'Growth Rate', 'font': {'size': 14, 'color': 'rgb(148, 163, 184)'}},
                range=[min(values) - 1, max(values) + 1],
                tickformat='.1f'
            ),
            height=400,  # Reduced height for better embedding
            width=None,  # Remove fixed width to allow responsive scaling
            autosize=True,  # Enable autosize
        )

        # Add a horizontal line at y=0
        fig.add_hline(
            y=0,
            line_color='rgba(148, 163, 184, 0.5)',
            line_width=1
        )

        # Add healthy growth range (2-3%)
        fig.add_hrect(
            y0=2, y1=3,
            fillcolor="rgba(59, 130, 246, 0.1)",  # Light blue for the target range
            line_width=0
        )

        # Add optimal range (3.5-4.5%)
        fig.add_hrect(
            y0=3.5, y1=4.5,
            fillcolor="rgba(74, 222, 128, 0.1)",
            line_width=0
        )

        # Save the chart
        charts_dir = os.path.join(output_dir, 'charts')
        os.makedirs(charts_dir, exist_ok=True)
        chart_path = os.path.join(charts_dir, 'gdp_chart.html')
        
        fig.write_html(
            chart_path,
            include_plotlyjs=True,
            full_html=True,
            config={
                'displayModeBar': False,
                'responsive': True,
                'autosizable': True,
                'fillFrame': True
            }
        )
        
        return os.path.relpath(chart_path, output_dir)
        
    except Exception as e:
        print(f"ERROR - Failed to generate GDP chart: {e}")
        return None

def generate_inflation_chart(data: Dict, output_dir: str) -> Optional[str]:
    """Generate inflation chart using Plotly."""
    try:
        # Create the line chart
        fig = go.Figure(data=[
            go.Scatter(
                x=data['labels'],
                y=data['values'],
                mode='lines+markers',
                line=dict(color='rgb(59, 130, 246)', width=2),
                marker=dict(size=8, color='rgb(59, 130, 246)'),
                hovertemplate="<b>%{x}</b><br>" +
                            "Inflation: %{y:.1f}%<br>" +
                            "<extra></extra>"
            )
        ])

        # Update layout
        fig.update_layout(
            title={
                'text': 'Inflation Rate',
                'y': 0.95,
                'x': 0.5,
                'xanchor': 'center',
                'yanchor': 'top',
                'font': {'color': 'rgb(148, 163, 184)', 'size': 28}
            },
            plot_bgcolor='rgb(13, 18, 30)',
            paper_bgcolor='rgb(13, 18, 30)',
            font={'color': 'rgb(148, 163, 184)', 'size': 14},
            showlegend=False,
            margin=dict(t=60, l=50, r=30, b=80),
            xaxis=dict(
                showgrid=True,
                gridcolor='rgba(148, 163, 184, 0.1)',
                tickfont={'size': 12, 'color': 'rgb(148, 163, 184)'},
                title=None,
                tickangle=45
            ),
            yaxis=dict(
                showgrid=True,
                gridcolor='rgba(148, 163, 184, 0.1)',
                zeroline=True,
                zerolinecolor='rgba(148, 163, 184, 0.5)',
                zerolinewidth=1,
                ticksuffix='%',
                tickfont={'size': 12, 'color': 'rgb(148, 163, 184)'},
                title={'text': 'Inflation Rate', 'font': {'size': 14, 'color': 'rgb(148, 163, 184)'}},
                range=[min(data['values']) - 0.5, max(data['values']) + 0.5],
                tickformat='.1f'
            ),
            height=400,
            width=None,
            autosize=True
        )

        # Add target inflation line
        fig.add_hline(
            y=2,
            line_color='rgba(148, 163, 184, 0.5)',
            line_width=1,
            line_dash='dash'
        )

        # Save the chart
        charts_dir = os.path.join(output_dir, 'charts')
        os.makedirs(charts_dir, exist_ok=True)
        chart_path = os.path.join(charts_dir, 'inflation_chart.html')
        
        fig.write_html(
            chart_path,
            include_plotlyjs=True,
            full_html=True,
            config={
                'displayModeBar': False,
                'responsive': True,
                'autosizable': True,
                'fillFrame': True
            }
        )
        
        return os.path.relpath(chart_path, output_dir)
        
    except Exception as e:
        print(f"ERROR - Failed to generate inflation chart: {e}")
        return None

def generate_unemployment_chart(data: Dict, output_dir: str) -> Optional[str]:
    """Generate unemployment chart using Plotly."""
    try:
        # Create the line chart
        fig = go.Figure(data=[
            go.Scatter(
                x=data['labels'],
                y=data['values'],
                mode='lines+markers',
                line=dict(color='rgb(239, 68, 68)', width=2),
                marker=dict(size=8, color='rgb(239, 68, 68)'),
                hovertemplate="<b>%{x}</b><br>" +
                            "Unemployment: %{y:.1f}%<br>" +
                            "<extra></extra>"
            )
        ])

        # Update layout
        fig.update_layout(
            title={
                'text': 'Unemployment Rate',
                'y': 0.95,
                'x': 0.5,
                'xanchor': 'center',
                'yanchor': 'top',
                'font': {'color': 'rgb(148, 163, 184)', 'size': 28}
            },
            plot_bgcolor='rgb(13, 18, 30)',
            paper_bgcolor='rgb(13, 18, 30)',
            font={'color': 'rgb(148, 163, 184)', 'size': 14},
            showlegend=False,
            margin=dict(t=60, l=50, r=30, b=80),
            xaxis=dict(
                showgrid=True,
                gridcolor='rgba(148, 163, 184, 0.1)',
                tickfont={'size': 12, 'color': 'rgb(148, 163, 184)'},
                title=None,
                tickangle=45
            ),
            yaxis=dict(
                showgrid=True,
                gridcolor='rgba(148, 163, 184, 0.1)',
                zeroline=True,
                zerolinecolor='rgba(148, 163, 184, 0.5)',
                zerolinewidth=1,
                ticksuffix='%',
                tickfont={'size': 12, 'color': 'rgb(148, 163, 184)'},
                title={'text': 'Unemployment Rate', 'font': {'size': 14, 'color': 'rgb(148, 163, 184)'}},
                range=[min(data['values']) - 0.5, max(data['values']) + 0.5],
                tickformat='.1f'
            ),
            height=400,
            width=None,
            autosize=True
        )

        # Add full employment line
        fig.add_hline(
            y=4,
            line_color='rgba(148, 163, 184, 0.5)',
            line_width=1,
            line_dash='dash'
        )

        # Save the chart
        charts_dir = os.path.join(output_dir, 'charts')
        os.makedirs(charts_dir, exist_ok=True)
        chart_path = os.path.join(charts_dir, 'unemployment_chart.html')
        
        fig.write_html(
            chart_path,
            include_plotlyjs=True,
            full_html=True,
            config={
                'displayModeBar': False,
                'responsive': True,
                'autosizable': True,
                'fillFrame': True
            }
        )
        
        return os.path.relpath(chart_path, output_dir)
        
    except Exception as e:
        print(f"ERROR - Failed to generate unemployment chart: {e}")
        return None

def generate_bond_chart(data: Dict, output_dir: str) -> Optional[str]:
    """Generate bond yield chart using Plotly."""
    try:
        # Create the line chart with both 10Y and 2Y yields
        fig = go.Figure()

        # Add 10Y yield line
        fig.add_trace(go.Scatter(
            x=data['labels'],
            y=data['values'],
            mode='lines+markers',
            name='10Y Treasury',
            line=dict(color='rgb(59, 130, 246)', width=2),
            marker=dict(size=8, color='rgb(59, 130, 246)'),
            hovertemplate="<b>%{x}</b><br>" +
                        "10Y Yield: %{y:.2f}%<br>" +
                        "<extra></extra>"
        ))

        # Add 2Y yield line if available
        if 'values_2y' in data:
            fig.add_trace(go.Scatter(
                x=data['labels'],
                y=data['values_2y'],
                mode='lines+markers',
                name='2Y Treasury',
                line=dict(color='rgb(239, 68, 68)', width=2),
                marker=dict(size=8, color='rgb(239, 68, 68)'),
                hovertemplate="<b>%{x}</b><br>" +
                            "2Y Yield: %{y:.2f}%<br>" +
                            "<extra></extra>"
            ))

        # Update layout
        fig.update_layout(
            title={
                'text': 'Treasury Yields',
                'y': 0.95,
                'x': 0.5,
                'xanchor': 'center',
                'yanchor': 'top',
                'font': {'color': 'rgb(148, 163, 184)', 'size': 28}
            },
            plot_bgcolor='rgb(13, 18, 30)',
            paper_bgcolor='rgb(13, 18, 30)',
            font={'color': 'rgb(148, 163, 184)', 'size': 14},
            showlegend=True,
            legend=dict(
                yanchor="top",
                y=0.99,
                xanchor="left",
                x=0.01,
                bgcolor='rgba(0,0,0,0)',
                bordercolor='rgba(0,0,0,0)',
                borderwidth=0,
                font={'color': 'rgb(148, 163, 184)', 'size': 12}
            ),
            margin=dict(t=60, l=50, r=30, b=80),
            xaxis=dict(
                showgrid=True,
                gridcolor='rgba(148, 163, 184, 0.1)',
                tickfont={'size': 12, 'color': 'rgb(148, 163, 184)'},
                title=None,
                tickangle=45
            ),
            yaxis=dict(
                showgrid=True,
                gridcolor='rgba(148, 163, 184, 0.1)',
                zeroline=True,
                zerolinecolor='rgba(148, 163, 184, 0.5)',
                zerolinewidth=1,
                ticksuffix='%',
                tickfont={'size': 12, 'color': 'rgb(148, 163, 184)'},
                title={'text': 'Yield', 'font': {'size': 14, 'color': 'rgb(148, 163, 184)'}},
                range=[min(data['values']) - 0.5, max(data['values']) + 0.5],
                tickformat='.2f'
            ),
            height=400,
            width=None,
            autosize=True
        )

        # Save the chart
        charts_dir = os.path.join(output_dir, 'charts')
        os.makedirs(charts_dir, exist_ok=True)
        chart_path = os.path.join(charts_dir, 'bond_chart.html')
        
        fig.write_html(
            chart_path,
            include_plotlyjs=True,
            full_html=True,
            config={
                'displayModeBar': False,
                'responsive': True,
                'autosizable': True,
                'fillFrame': True
            }
        )
        
        return os.path.relpath(chart_path, output_dir)
        
    except Exception as e:
        print(f"ERROR - Failed to generate bond chart: {e}")
        return None 