"""
Market chart generator for economic indicators and market data.
"""

import os
import json
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime
from typing import Dict, Optional
import logging
import re
import plotly.io as pio

# Configure logging
logger = logging.getLogger(__name__)

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
    """Generate inflation chart as a bar chart using Plotly."""
    try:
        labels = data['labels']
        values = data['values']
        # Color coding: green for target (2-2.5%), yellow for below target, red for above target
        colors = [
            'rgb(34, 197, 94)' if 2.0 <= v <= 2.5 else ('rgb(234, 179, 8)' if v < 2.0 else 'rgb(239, 68, 68)')
            for v in values
        ]
        fig = go.Figure(data=[
            go.Bar(
                x=labels,
                y=values,
                marker_color=colors,
                text=[f"{v:.1f}%" for v in values],
                textposition='outside',
                textfont={'size': 14, 'color': '#94a3b8'},
                hovertemplate="<b>%{x}</b><br>Inflation: %{y:.1f}%<extra></extra>"
            )
        ])
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
            font={'color': 'rgb(148, 163, 184)', 'size': 14, 'family': 'system-ui'},
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
                range=[min(values) - 0.5, max(values) + 0.5],
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
        # Add target range shadow
        fig.add_hrect(
            y0=2.0, y1=2.5,
            fillcolor="rgba(34, 197, 94, 0.08)",
            line_width=0
        )
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
    """Generate unemployment chart as a bar chart using Plotly."""
    try:
        labels = data['labels']
        values = data['values']
        # Color coding: green for <=4.0, yellow for <=4.4, red for >4.4
        colors = [
            'rgb(34, 197, 94)' if v <= 4.0 else ('rgb(234, 179, 8)' if v <= 4.4 else 'rgb(239, 68, 68)')
            for v in values
        ]
        fig = go.Figure(data=[
            go.Bar(
                x=labels,
                y=values,
                marker_color=colors,
                text=[f"{v:.1f}%" for v in values],
                textposition='outside',
                textfont={'size': 14, 'color': '#94a3b8'},
                hovertemplate="<b>%{x}</b><br>Unemployment: %{y:.1f}%<extra></extra>"
            )
        ])
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
            font={'color': 'rgb(148, 163, 184)', 'size': 14, 'family': 'system-ui'},
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
                range=[min(values) - 0.5, max(values) + 0.5],
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
        # Add optimal range shadow
        fig.add_hrect(
            y0=3.5, y1=4.0,
            fillcolor="rgba(34, 197, 94, 0.08)",
            line_width=0
        )
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
    """Generate bond yield chart as a line chart using Plotly, highlighting yield curve inversion, with debugging and robust length handling."""
    try:
        labels = data['labels']
        values_10y = data['values']
        values_2y = data.get('values_2y')
        # Ensure all lists are the same length
        n = len(labels)
        if values_2y:
            n = min(n, len(values_10y), len(values_2y))
            if not (len(labels) == len(values_10y) == len(values_2y)):
                print(f"[DEBUG] Mismatched lengths: labels={len(labels)}, 10Y={len(values_10y)}, 2Y={len(values_2y)}. Trimming to {n}.")
            labels = labels[:n]
            values_10y = values_10y[:n]
            values_2y = values_2y[:n]
        else:
            n = min(n, len(values_10y))
            if not (len(labels) == len(values_10y)):
                print(f"[DEBUG] Mismatched lengths: labels={len(labels)}, 10Y={len(values_10y)}. Trimming to {n}.")
            labels = labels[:n]
            values_10y = values_10y[:n]
        print(f"[DEBUG] Chart labels: {labels}")
        print(f"[DEBUG] 10Y values: {values_10y}")
        print(f"[DEBUG] 2Y values: {values_2y}")
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=labels,
            y=values_10y,
            mode='lines+markers',
            name='10Y Treasury',
            line=dict(color='rgb(59, 130, 246)', width=2),
            marker=dict(size=8, color='rgb(59, 130, 246)'),
            hovertemplate="<b>%{x}</b><br>10Y Yield: %{y:.2f}%<extra></extra>"
        ))
        if values_2y:
            fig.add_trace(go.Scatter(
                x=labels,
                y=values_2y,
                mode='lines+markers',
                name='2Y Treasury',
                line=dict(color='rgb(239, 68, 68)', width=2),
                marker=dict(size=8, color='rgb(239, 68, 68)'),
                hovertemplate="<b>%{x}</b><br>2Y Yield: %{y:.2f}%<extra></extra>"
            ))
            # Highlight contiguous inversion regions (2Y > 10Y)
            inversion_regions = []
            in_inversion = False
            start_idx = None
            for i in range(n):
                if values_2y[i] > values_10y[i]:
                    if not in_inversion:
                        in_inversion = True
                        start_idx = i
                else:
                    if in_inversion:
                        in_inversion = False
                        inversion_regions.append((start_idx, i-1))
            if in_inversion:
                inversion_regions.append((start_idx, n-1))
            for start, end in inversion_regions:
                fig.add_vrect(
                    x0=labels[start],
                    x1=labels[end],
                    fillcolor="rgba(239, 68, 68, 0.15)",
                    line_width=0,
                    layer="below"
                )
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
            font={'color': 'rgb(148, 163, 184)', 'size': 14, 'family': 'system-ui'},
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
                range=[
                    min(values_10y + (values_2y if values_2y else [])) - 0.5,
                    max(values_10y + (values_2y if values_2y else [])) + 0.5
                ],
                tickformat='.2f'
            ),
            height=400,
            width=None,
            autosize=True
        )
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

def generate_market_index_chart(data: Dict, output_dir: str, index_name: str) -> Optional[str]:
    """Generate a chart HTML file for a market index ETF. Use Plotly for Dollar Index, TradingView for others."""
    # Special case for Dollar Index
    if index_name == 'Dollar Index' and data and data.get('labels') and data.get('values'):
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=data['labels'],
            y=data['values'],
            mode='lines+markers',
            name='Dollar Index',
            line=dict(color='rgb(59, 130, 246)', width=2),
            marker=dict(size=8, color='rgb(59, 130, 246)'),
            hovertemplate="<b>%{x}</b><br>Dollar Index: %{y:.2f}<extra></extra>"
        ))
        fig.update_layout(
            title={'text': 'Dollar Index (DXY)', 'y': 0.95, 'x': 0.5, 'xanchor': 'center', 'yanchor': 'top', 'font': {'color': 'rgb(148, 163, 184)', 'size': 28}},
            plot_bgcolor='rgba(15,23,42,1)',
            paper_bgcolor='rgba(15,23,42,1)',
            font=dict(color='rgb(226,232,240)', size=16),
            margin=dict(l=30, r=30, t=60, b=30),
            xaxis=dict(title='', showgrid=False, zeroline=False),
            yaxis=dict(title='', showgrid=True, gridcolor='rgba(51,65,85,0.4)', zeroline=False),
            hovermode='x unified',
        )
        charts_dir = os.path.join(output_dir, 'charts')
        os.makedirs(charts_dir, exist_ok=True)
        chart_path = os.path.join(charts_dir, 'dollar_index_chart.html')
        pio.write_html(fig, file=chart_path, auto_open=False, include_plotlyjs='cdn')
        return os.path.relpath(chart_path, output_dir)
    # Otherwise, use TradingView as before
    logger.debug(f"Generating TradingView chart for {index_name}")
    # Map index names and tickers to correct TradingView symbols
    tradingview_symbol_map = {
        'S&P 500': 'AMEX:SPY',
        'SPY': 'AMEX:SPY',
        'Dow Jones': 'AMEX:DIA',
        'DIA': 'AMEX:DIA',
        'Nasdaq-100': 'NASDAQ:QQQ',
        'QQQ': 'NASDAQ:QQQ',
        'S&P 400 MidCap': 'AMEX:MDY',
        'MDY': 'AMEX:MDY',
        'Russell 2000': 'AMEX:IWM',
        'IWM': 'AMEX:IWM',
        'S&P 500 Growth': 'AMEX:IVW',
        'IVW': 'AMEX:IVW',
        'S&P 500 Value': 'AMEX:IVE',
        'IVE': 'AMEX:IVE',
        'UUP': 'AMEX:UUP',
        'Oil (WTI)': 'TVC:USOIL',
        'USO': 'AMEX:USO',
        'VIX': 'AMEX:VIXY',
        'VIXY': 'AMEX:VIXY',
    }
    # Try to match by name or ticker
    tv_symbol = None
    for k, v in tradingview_symbol_map.items():
        if k.lower() in index_name.lower() or k.lower() == index_name.lower():
            tv_symbol = v
            break
    if not tv_symbol:
        # Fallback: try to extract ticker from data or index_name and use AMEX as default
        ticker = re.sub(r'[^A-Z]', '', index_name.upper())
        tv_symbol = f'AMEX:{ticker}'
        logger.debug(f"Fallback TradingView symbol: {tv_symbol} for index {index_name}")
    logger.debug(f"Final TradingView symbol for {index_name}: {tv_symbol}")
    safe_name = index_name.lower().replace(' ', '_').replace('&', 'and')
    charts_dir = os.path.join(output_dir, 'charts')
    os.makedirs(charts_dir, exist_ok=True)
    chart_path = os.path.join(charts_dir, f'{safe_name}_chart.html')
    widget_html = f'''
<!-- TradingView Widget BEGIN -->
<div class="tradingview-widget-container">
  <div id="tradingview_{safe_name}"></div>
  <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
  <script type="text/javascript">
  new TradingView.widget({{
    "width": "100%",
    "height": 480,
    "symbol": "{tv_symbol}",
    "interval": "D",
    "timezone": "Etc/UTC",
    "theme": "dark",
    "style": "1",
    "locale": "en",
    "toolbar_bg": "#131722",
    "enable_publishing": false,
    "hide_top_toolbar": false,
    "save_image": false,
    "container_id": "tradingview_{safe_name}"
  }});
  </script>
</div>
<!-- TradingView Widget END -->
'''
    try:
        with open(chart_path, 'w', encoding='utf-8') as f:
            f.write(widget_html)
        logger.info(f"TradingView chart for {index_name} saved to {chart_path}")
        return os.path.relpath(chart_path, output_dir)
    except Exception as e:
        logger.error(f"Failed to generate TradingView chart for {index_name}: {e}")
        return None

def generate_single_bond_chart(data: Dict, output_dir: str, filename: str, title: str) -> Optional[str]:
    try:
        labels = data['labels']
        values = data['values']
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=labels,
            y=values,
            mode='lines+markers',
            name=title,
            line=dict(color='rgb(59, 130, 246)', width=2),
            marker=dict(size=8, color='rgb(59, 130, 246)'),
            hovertemplate=f"<b>%{{x}}</b><br>{title}: %{{y:.2f}}%<extra></extra>"
        ))
        fig.update_layout(
            title={'text': title, 'y': 0.95, 'x': 0.5, 'xanchor': 'center', 'yanchor': 'top', 'font': {'color': 'rgb(148, 163, 184)', 'size': 28}},
            plot_bgcolor='rgb(13, 18, 30)',
            paper_bgcolor='rgb(13, 18, 30)',
            font={'color': 'rgb(148, 163, 184)', 'size': 14, 'family': 'system-ui'},
            showlegend=False,
            margin=dict(t=60, l=50, r=30, b=80),
            xaxis=dict(showgrid=True, gridcolor='rgba(148, 163, 184, 0.1)', tickfont={'size': 12, 'color': 'rgb(148, 163, 184)'}, title=None, tickangle=45),
            yaxis=dict(showgrid=True, gridcolor='rgba(148, 163, 184, 0.1)', zeroline=True, zerolinecolor='rgba(148, 163, 184, 0.5)', zerolinewidth=1, ticksuffix='%', tickfont={'size': 12, 'color': 'rgb(148, 163, 184)'}, title={'text': 'Yield', 'font': {'size': 14, 'color': 'rgb(148, 163, 184)'}}, range=[min(values) - 0.5, max(values) + 0.5], tickformat='.2f'),
            height=400,
            width=None,
            autosize=True
        )
        charts_dir = os.path.join(output_dir, 'charts')
        os.makedirs(charts_dir, exist_ok=True)
        chart_path = os.path.join(charts_dir, filename)
        fig.write_html(
            chart_path,
            include_plotlyjs=True,
            full_html=True,
            config={'displayModeBar': False, 'responsive': True, 'autosizable': True, 'fillFrame': True}
        )
        return os.path.relpath(chart_path, output_dir)
    except Exception as e:
        print(f"ERROR - Failed to generate {title} chart: {e}")
        return None 