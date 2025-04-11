import plotly.graph_objects as go
import os
import json

def generate_gdp_chart(data, output_dir):
    """Generate GDP chart using Lightweight Charts."""
    try:
        # Convert data for lightweight-charts
        chart_data = []
        for i, (label, value) in enumerate(zip(data['labels'], data['values'])):
            try:
                if label and value is not None:
                    # Convert quarter format (e.g. "Q1 2025") to timestamp
                    quarter = int(label[1])
                    year = int(label.split()[1])
                    # Map quarter to middle month of quarter
                    month = (quarter - 1) * 3 + 2  # Q1->Feb, Q2->May, Q3->Aug, Q4->Nov
                    time_str = f"{year}-{month:02d}-15"
                    
                    chart_data.append({
                        'time': time_str,
                        'value': float(value),
                        'color': 'rgba(100, 150, 220, 0.7)' if float(value) >= 0 else 'rgba(255, 220, 100, 0.7)'
                    })
            except Exception as e:
                print(f"Error processing GDP data point {i}: {e}")

        print(f"DEBUG - GDP Chart data: {chart_data}")  # Debug print

        chart_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Real GDP Growth Rate</title>
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
                            top: 0.3,  // Increased to make room for labels
                            bottom: 0.2,
                        }},
                    }},
                    timeScale: {{
                        borderColor: 'rgba(148, 163, 184, 0.2)',
                        borderVisible: true,
                        timeVisible: true,
                    }},
                }});

                const series = chart.addHistogramSeries({{
                    priceFormat: {{
                        type: 'price',
                        precision: 1,
                        minMove: 0.1,
                    }},
                }});

                const chartData = {json.dumps(chart_data)};
                series.setData(chartData);

                // Add value labels above bars
                chartData.forEach(bar => {{
                    const sign = bar.value >= 0 ? '+' : '';
                    chart.addCustomPriceLabel({{
                        price: bar.value + (bar.value >= 0 ? 0.5 : -0.5),
                        time: bar.time,
                        color: '#94a3b8',
                        text: `${{sign}}${{bar.value.toFixed(1)}}%`,
                        fontSize: 11,
                        borderColor: 'transparent',
                    }});
                }});

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

        # Save the chart
        charts_dir = os.path.join(output_dir, 'charts')
        os.makedirs(charts_dir, exist_ok=True)
        chart_path = os.path.join(charts_dir, 'gdp_chart.html')
        
        with open(chart_path, 'w') as f:
            f.write(chart_html)
        
        return os.path.relpath(chart_path, output_dir)
        
    except Exception as e:
        print(f"ERROR - Failed to generate GDP chart: {e}")
        print(f"Data sample: {data['labels'][:3]}, {data['values'][:3]}")
        return None

def generate_inflation_chart(data, output_dir):
    """Generate inflation chart using Lightweight Charts."""
    try:
        # Convert data for lightweight-charts
        chart_data = []
        for i, (label, value) in enumerate(zip(data['labels'], data['values'])):
            try:
                if label and value is not None:
                    # Format date as YYYY-MM-DD
                    time_str = f"{label}-01" if len(label.split('-')) == 2 else label
                    
                    chart_data.append({
                        'time': time_str,
                        'value': float(value),
                        'color': 'rgba(74, 222, 128, 0.7)' if float(value) <= 2.5 else 'rgba(248, 113, 113, 0.7)'
                    })
            except Exception as e:
                print(f"Error processing inflation data point {i}: {e}")

        print(f"DEBUG - Inflation Chart data: {chart_data}")

        chart_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Inflation Rate</title>
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

                const series = chart.addHistogramSeries({{
                    priceFormat: {{
                        type: 'price',
                        precision: 1,
                        minMove: 0.1,
                    }},
                }});

                series.setData({json.dumps(chart_data)});
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
        # Convert data for lightweight-charts
        chart_data = []
        for i, (label, value) in enumerate(zip(data['labels'], data['values'])):
            try:
                if label and value is not None:
                    # Format date as YYYY-MM-DD
                    time_str = f"{label}-01" if len(label.split('-')) == 2 else label
                    
                    chart_data.append({
                        'time': time_str,
                        'value': float(value),
                        'color': 'rgba(168, 85, 247, 0.7)'  # Purple
                    })
            except Exception as e:
                print(f"Error processing unemployment data point {i}: {e}")

        print(f"DEBUG - Unemployment Chart data: {chart_data}")

        chart_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Unemployment Rate</title>
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

                const series = chart.addHistogramSeries({{
                    priceFormat: {{
                        type: 'price',
                        precision: 1,
                        minMove: 0.1,
                    }},
                }});

                series.setData({json.dumps(chart_data)});
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
    """Generate bond chart using Plotly."""
    try:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=data['labels'],
            y=data['values'],
            name='10Y Bond Yield',
            line=dict(
                color='rgba(41, 98, 255, 0.9)',
                width=2
            ),
            fill='tozeroy',
            fillcolor='rgba(41, 98, 255, 0.1)'
        ))

        fig.update_layout(
            title=None,
            paper_bgcolor='rgb(13, 18, 30)',
            plot_bgcolor='rgb(13, 18, 30)',
            showlegend=False,
            margin=dict(l=40, r=40, t=40, b=40),
            height=350,
            yaxis=dict(
                title=dict(
                    text='Yield (%)',
                    font=dict(color='#94a3b8')
                ),
                gridcolor='rgba(148, 163, 184, 0.1)',
                zerolinecolor='rgba(148, 163, 184, 0.2)',
                tickfont=dict(color='#94a3b8')
            ),
            xaxis=dict(
                gridcolor='rgba(148, 163, 184, 0.1)',
                tickfont=dict(color='#94a3b8')
            )
        )

        charts_dir = os.path.join(output_dir, 'charts')
        os.makedirs(charts_dir, exist_ok=True)
        chart_path = os.path.join(charts_dir, 'bond_chart.html')
        fig.write_html(chart_path)
        
        return os.path.relpath(chart_path, output_dir)
        
    except Exception as e:
        print(f"ERROR - Failed to generate bond chart: {e}")
        return None 