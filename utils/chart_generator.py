import plotly.graph_objects as go
import os
import json

def generate_gdp_chart(data, output_dir):
    """Generate GDP chart using Plotly."""
    try:
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

def generate_inflation_chart(data, output_dir):
    """Generate inflation chart using Lightweight Charts."""
    try:
        # Limit to the most recent 8 data points
        labels = data['labels'][-8:]
        values = data['values'][-8:]
        chart_data = []
        for i, (label, value) in enumerate(zip(labels, values)):
            try:
                if label and value is not None:
                    time_str = f"{label}-01" if len(label.split('-')) == 2 else label
                    value = float(value)
                    # Color coding based on Fed target range
                    color = ('rgba(34, 197, 94, 0.7)' if 1.5 <= value <= 2.5 else  # Green for target range
                            'rgba(234, 179, 8, 0.7)' if 0 <= value < 1.5 else      # Yellow for low inflation
                            'rgba(239, 68, 68, 0.7)')                              # Red for high inflation
                    chart_data.append({
                        'time': time_str,
                        'value': value,
                        'color': color
                    })
            except Exception as e:
                print(f"Error processing inflation data point {i}: {e}")
        chart_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Inflation Rate</title>
            <script src=\"https://unpkg.com/lightweight-charts@4.1.1/dist/lightweight-charts.standalone.production.js\"></script>
            <style>
                body {{
                    margin: 0;
                    padding: 0;
                    width: 500px;
                    height: 500px;
                    background-color: rgb(13, 18, 30);
                }}
                #container {{
                    position: absolute;
                    width: 500px;
                    height: 500px;
                    background-color: rgb(13, 18, 30);
                }}
            </style>
        </head>
        <body>
            <div id=\"container\"></div>
            <script>
                const container = document.getElementById('container');
                const chart = LightweightCharts.createChart(container, {{
                    width: container.clientWidth,
                    height: container.clientHeight,
                    layout: {{
                        background: {{ type: 'solid', color: 'rgb(13, 18, 30)' }},
                        textColor: '#94a3b8',
                        fontFamily: 'system-ui',
                        fontSize: 12,
                    }},
                    grid: {{
                        vertLines: {{ color: 'rgba(148, 163, 184, 0.1)' }},
                        horzLines: {{ color: 'rgba(148, 163, 184, 0.1)' }},
                    }},
                    rightPriceScale: {{
                        borderColor: 'rgba(148, 163, 184, 0.2)',
                        borderVisible: true,
                        scaleMargins: {{
                            top: 0.2,
                            bottom: 0.2,
                        }},
                        autoScale: false,
                        minimum: -1.0,
                        maximum: 4.0,
                        ticksVisible: true,
                        entireTextOnly: false,
                    }},
                    timeScale: {{
                        borderColor: 'rgba(148, 163, 184, 0.2)',
                        borderVisible: true,
                        timeVisible: true,
                        fixLeftEdge: true,
                        fixRightEdge: true,
                        tickMarkFormatter: (time, tickIndex) => {{
                            // Show only every 4th label for clarity
                            const chartData = {json.dumps(chart_data)};
                            const idx = chartData.findIndex(d => d.time === time);
                            if (idx % 4 === 0) {{
                                const date = new Date(time);
                                return date.toLocaleDateString('en-US', {{ month: 'short', year: '2-digit' }});
                            }}
                            return '';
                        }},
                        tickLabelOrientation: 0, // horizontal
                        tickLength: 6,
                        borderColor: 'rgba(148, 163, 184, 0.2)',
                        borderVisible: true,
                        timeVisible: true,
                        secondsVisible: false,
                        fixLeftEdge: true,
                        fixRightEdge: true,
                        lockVisibleTimeRangeOnResize: true,
                        rightOffset: 12,
                        barSpacing: 6,
                        minBarSpacing: 6,
                    }},
                    crosshair: {{
                        vertLine: {{
                            color: '#94A3B8',
                            width: 0.5,
                            style: 1,
                            visible: true,
                            labelVisible: true,
                        }},
                        horzLine: {{
                            color: '#94A3B8',
                            width: 0.5,
                            style: 1,
                            visible: true,
                            labelVisible: true,
                        }},
                    }},
                }});

                // Add the main histogram series
                const mainSeries = chart.addHistogramSeries({{
                    color: '#2563eb',
                    priceFormat: {{
                        type: 'price',
                        precision: 1,
                        minMove: 0.1,
                    }},
                }});

                // Add data with custom colors
                mainSeries.setData(
                    {json.dumps(chart_data)}.map(d => ({{
                        time: d.time,
                        value: d.value,
                        color: d.color
                    }}))
                );

                // Add Fed target line (2%)
                const targetLine = chart.addBaselineSeries({{
                    baseValue: {{ type: 'price', price: 2.0 }},
                    topLineColor: 'rgba(34, 197, 94, 0.8)',
                    bottomLineColor: 'rgba(34, 197, 94, 0.8)',
                    lineWidth: 2,
                    lineStyle: 2,  // Dashed line
                }});

                // Add target range area (1.5-2.5%)
                const rangeArea = chart.addAreaSeries({{
                    topLineColor: 'rgba(34, 197, 94, 0.3)',
                    bottomLineColor: 'rgba(34, 197, 94, 0.3)',
                    lineWidth: 1,
                    lastValueVisible: false,
                    crosshairMarkerVisible: false,
                    priceLineVisible: false,
                }});

                // Set data for the target range area
                rangeArea.setData({json.dumps(chart_data)}.map(d => ({{
                    time: d.time,
                    high: 2.5,
                    low: 1.5
                }})));

                // Add trend line
                const trendSeries = chart.addLineSeries({{
                    color: 'rgba(255, 255, 255, 0.5)',
                    lineWidth: 2,
                    lineStyle: 2,  // Dashed line
                }});

                // Calculate and set trend line data
                const trendData = {json.dumps(chart_data)}.map(d => ({{
                    time: d.time,
                    value: d.value
                }}));
                trendSeries.setData(trendData);

                // Add legend
                const legend = document.createElement('div');
                legend.style.position = 'absolute';
                legend.style.right = '10px';
                legend.style.top = '10px';
                legend.style.display = 'flex';
                legend.style.flexDirection = 'column';
                legend.style.gap = '5px';
                legend.style.padding = '8px';
                legend.style.backgroundColor = 'rgba(13, 18, 30, 0.8)';
                legend.style.borderRadius = '4px';
                legend.style.color = '#94a3b8';
                legend.style.fontSize = '12px';
                legend.style.fontFamily = 'system-ui';
                legend.innerHTML = `
                    <div style="display: flex; align-items: center; gap: 5px;">
                        <span style="color: rgba(34, 197, 94, 0.8);">―</span>
                        <span>Fed Target (2.0%)</span>
                    </div>
                    <div style="display: flex; align-items: center; gap: 5px;">
                        <span style="color: rgba(34, 197, 94, 0.7);">■</span>
                        <span>Target Range (1.5-2.5%)</span>
                    </div>
                    <div style="display: flex; align-items: center; gap: 5px;">
                        <span style="color: rgba(234, 179, 8, 0.7);">■</span>
                        <span>Below Target (<1.5%)</span>
                    </div>
                    <div style="display: flex; align-items: center; gap: 5px;">
                        <span style="color: rgba(239, 68, 68, 0.7);">■</span>
                        <span>Above Target (>2.5%)</span>
                    </div>
                `;
                container.appendChild(legend);

                // Fit content and handle resize
                chart.timeScale().fitContent();

                window.addEventListener('resize', () => {{
                    chart.applyOptions({{
                        width: container.clientWidth,
                        height: container.clientHeight,
                    }});
                }});
            </script>
        </body>
        </html>
        """

        charts_dir = os.path.join(output_dir, 'charts')
        os.makedirs(charts_dir, exist_ok=True)
        chart_path = os.path.join(charts_dir, 'inflation_chart.html')
        
        with open(chart_path, 'w') as f:
            f.write(chart_html)
        
        return os.path.relpath(chart_path, output_dir)
        
    except Exception as e:
        print(f"ERROR - Failed to generate inflation chart: {e}")
        return None

def generate_unemployment_chart(data, output_dir):
    """Generate unemployment chart using Lightweight Charts."""
    try:
        # Limit to the most recent 8 data points
        labels = data['labels'][-8:]
        values = data['values'][-8:]
        chart_data = []
        for i, (label, value) in enumerate(zip(labels, values)):
            try:
                if label and value is not None:
                    time_str = f"{label}-01" if len(label.split('-')) == 2 else label
                    # Color coding: purple for unemployment
                    # Darker purple for higher unemployment
                    def get_unemployment_color(value):
                        if value <= 4.0:
                            return 'rgba(34, 197, 94, 0.7)'  # Green for low unemployment
                        elif value <= 4.4:
                            return 'rgba(234, 179, 8, 0.7)'  # Yellow for near target
                        else:
                            return 'rgba(239, 68, 68, 0.7)'  # Red for high unemployment
                    chart_data.append({
                        'time': time_str,
                        'value': float(value),
                        'color': get_unemployment_color(float(value))
                    })
            except Exception as e:
                print(f"Error processing unemployment data point {i}: {e}")
        print(f"DEBUG - Unemployment Chart data: {chart_data}")
        # Calculate min/max for a tighter y-axis
        min_val = min([d['value'] for d in chart_data])
        max_val = max([d['value'] for d in chart_data])
        y_min = max(0, min_val - 0.2)
        y_max = max_val + 0.2
        chart_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Unemployment Rate</title>
            <script src=\"https://unpkg.com/lightweight-charts@4.1.1/dist/lightweight-charts.standalone.production.js\"></script>
            <style>
                body {{
                    margin: 0;
                    padding: 0;
                    width: 100vw;
                    height: 100vh;
                    background-color: rgb(13, 18, 30);
                }}
                #container {{
                    position: absolute;
                    width: 100%;
                    height: 100%;
                }}
            </style>
        </head>
        <body>
            <div id=\"container\"></div>
            <script>
                const container = document.getElementById('container');
                const chart = LightweightCharts.createChart(container, {{
                    width: container.clientWidth,
                    height: container.clientHeight,
                    layout: {{
                        background: {{ type: 'solid', color: 'rgb(13, 18, 30)' }},
                        textColor: '#94a3b8',
                        fontFamily: 'system-ui',
                    }},
                    grid: {{
                        vertLines: {{ color: 'rgba(148, 163, 184, 0.1)' }},
                        horzLines: {{ color: 'rgba(148, 163, 184, 0.1)' }},
                    }},
                    rightPriceScale: {{
                        borderColor: 'rgba(148, 163, 184, 0.2)',
                        borderVisible: true,
                        scaleMargins: {{
                            top: 0.1,
                            bottom: 0.1,
                        }},
                        autoScale: false,
                        minimum: {y_min},
                        maximum: {y_max},
                        ticksVisible: true,
                        entireTextOnly: false,
                        tickMarkFormatter: (price) => price.toFixed(1) + '%',
                    }},
                    timeScale: {{
                        borderColor: 'rgba(148, 163, 184, 0.2)',
                        borderVisible: true,
                        timeVisible: true,
                    }},
                    handleScroll: {{
                        mouseWheel: true,
                        pressedMouseMove: true,
                    }},
                    handleScale: {{
                        mouseWheel: true,
                        pinch: true,
                    }},
                    crosshair: {{
                        mode: LightweightCharts.CrosshairMode.Normal,
                        vertLine: {{
                            color: '#94A3B8',
                            width: 0.5,
                            style: 1,
                            visible: true,
                            labelVisible: true,
                        }},
                        horzLine: {{
                            color: '#94A3B8',
                            width: 0.5,
                            style: 1,
                            visible: true,
                            labelVisible: true,
                        }},
                    }},
                }});

                const series = chart.addHistogramSeries({{
                    priceFormat: {{
                        type: 'price',
                        precision: 2,
                        minMove: 0.01,
                    }},
                }});

                const chartData = {json.dumps(chart_data)};
                series.setData(chartData);

                const baseline = chart.addBaselineSeries({{
                    baseValue: {{ type: 'price', price: 4.4 }},
                    topLineColor: 'rgba(148, 163, 184, 0.2)',
                    bottomLineColor: 'rgba(148, 163, 184, 0.2)',
                }});

                // Add value labels above bars with delay to ensure rendering
                setTimeout(() => {{
                    chartData.forEach(dataPoint => {{
                        chart.addCustomPriceLabel({{
                            price: dataPoint.value + 0.05,
                            time: dataPoint.time,
                            color: '#94a3b8',
                            text: `${{dataPoint.value.toFixed(2)}}%`,
                            fontSize: 11,
                            borderColor: 'transparent',
                        }});
                    }});
                }}, 100);

                chart.timeScale().fitContent();

                window.addEventListener('resize', () => {{
                    chart.applyOptions({{
                        width: container.clientWidth,
                        height: container.clientHeight,
                    }});
                }});
            </script>
        </body>
        </html>
        """

        charts_dir = os.path.join(output_dir, 'charts')
        os.makedirs(charts_dir, exist_ok=True)
        chart_path = os.path.join(charts_dir, 'unemployment_chart.html')
        
        with open(chart_path, 'w') as f:
            f.write(chart_html)
        
        return os.path.relpath(chart_path, output_dir)
        
    except Exception as e:
        print(f"ERROR - Failed to generate unemployment chart: {e}")
        return None

def generate_bond_chart(data, output_dir):
    """Generate bond chart using Lightweight Charts."""
    try:
        # Convert data for lightweight-charts
        chart_data = []
        for i, (label, value) in enumerate(zip(data['labels'], data['values'])):
            try:
                if label and value is not None:
                    time_str = label if len(label.split('-')) == 3 else f"{label}-01"
                    
                    chart_data.append({
                        'time': time_str,
                        'value': float(value)
                    })
            except Exception as e:
                print(f"Error processing bond data point {i}: {e}")

        print(f"DEBUG - Bond Chart data: {chart_data}")

        chart_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>US 10Y Bond Yield</title>
            <script src="https://unpkg.com/lightweight-charts@4.1.1/dist/lightweight-charts.standalone.production.js"></script>
            <style>
                body {{
                    margin: 0;
                    padding: 0;
                    width: 100vw;
                    height: 100vh;
                    background-color: rgb(13, 18, 30);
                }}
                #container {{
                    position: absolute;
                    width: 100%;
                    height: 100%;
                }}
            </style>
        </head>
        <body>
            <div id="container"></div>
            <script>
                const container = document.getElementById('container');
                const chart = LightweightCharts.createChart(container, {{
                    width: container.clientWidth,
                    height: container.clientHeight,
                    layout: {{
                        background: {{ type: 'solid', color: 'rgb(13, 18, 30)' }},
                        textColor: '#94a3b8',
                        fontFamily: 'system-ui',
                    }},
                    grid: {{
                        vertLines: {{ color: 'rgba(148, 163, 184, 0.1)' }},
                        horzLines: {{ color: 'rgba(148, 163, 184, 0.1)' }},
                    }},
                    rightPriceScale: {{
                        borderColor: 'rgba(148, 163, 184, 0.2)',
                        borderVisible: true,
                        scaleMargins: {{
                            top: 0.2,
                            bottom: 0.2,
                        }},
                    }},
                    timeScale: {{
                        borderColor: 'rgba(148, 163, 184, 0.2)',
                        borderVisible: true,
                        timeVisible: true,
                    }},
                }});

                const series = chart.addLineSeries({{
                    color: 'rgba(41, 98, 255, 0.9)',
                    lineWidth: 2,
                    priceFormat: {{
                        type: 'price',
                        precision: 2,
                        minMove: 0.01,
                    }},
                }});

                const chartData = {json.dumps(chart_data)};
                series.setData(chartData);

                // Add area under the line
                const areaSeries = chart.addAreaSeries({{
                    lineWidth: 0,
                    topColor: 'rgba(41, 98, 255, 0.1)',
                    bottomColor: 'rgba(41, 98, 255, 0.01)',
                    priceFormat: {{
                        type: 'price',
                        precision: 2,
                        minMove: 0.01,
                    }},
                }});
                areaSeries.setData(chartData);

                // Add value labels with delay to ensure rendering
                setTimeout(() => {{
                    chartData.forEach(dataPoint => {{
                        chart.addCustomPriceLabel({{
                            price: dataPoint.value + 0.1,
                            time: dataPoint.time,
                            color: '#94a3b8',
                            text: `${{dataPoint.value.toFixed(2)}}%`,
                            fontSize: 11,
                            borderColor: 'transparent',
                        }});
                    }});
                }}, 100);

                chart.timeScale().fitContent();

                window.addEventListener('resize', () => {{
                    chart.applyOptions({{
                        width: container.clientWidth,
                        height: container.clientHeight,
                    }});
                }});
            </script>
        </body>
        </html>
        """

        charts_dir = os.path.join(output_dir, 'charts')
        os.makedirs(charts_dir, exist_ok=True)
        chart_path = os.path.join(charts_dir, 'bond_chart.html')
        
        with open(chart_path, 'w') as f:
            f.write(chart_html)
        
        return os.path.relpath(chart_path, output_dir)
        
    except Exception as e:
        print(f"ERROR - Failed to generate bond chart: {e}")
        return None 