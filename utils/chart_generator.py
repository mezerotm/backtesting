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
                    quarter = int(label[1])
                    year = int(label.split()[1])
                    month = (quarter - 1) * 3 + 2
                    time_str = f"{year}-{month:02d}-15"
                    
                    chart_data.append({
                        'time': time_str,
                        'value': float(value),
                        'color': 'rgba(34, 197, 94, 0.7)' if float(value) >= 0 else 'rgba(239, 68, 68, 0.7)'
                    })
            except Exception as e:
                print(f"Error processing GDP data point {i}: {e}")

        print(f"DEBUG - GDP Chart data: {chart_data}")

        # Update the JavaScript to properly show labels
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
                            top: 0.1,
                            bottom: 0.1,
                        }},
                        autoScale: false,
                        minimum: -2,
                        maximum: 4.5,
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
                        precision: 1,
                        minMove: 0.1,
                    }},
                }});

                const chartData = {json.dumps(chart_data)};
                series.setData(chartData);

                const baseline = chart.addBaselineSeries({{
                    baseValue: {{ type: 'price', price: 0 }},
                    topLineColor: 'rgba(148, 163, 184, 0.2)',
                    bottomLineColor: 'rgba(148, 163, 184, 0.2)',
                }});

                // Add value labels above bars with delay to ensure rendering
                setTimeout(() => {{
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

        # Save the chart
        charts_dir = os.path.join(output_dir, 'charts')
        os.makedirs(charts_dir, exist_ok=True)
        chart_path = os.path.join(charts_dir, 'gdp_chart.html')
        
        with open(chart_path, 'w') as f:
            f.write(chart_html)
        
        return os.path.relpath(chart_path, output_dir)
        
    except Exception as e:
        print(f"ERROR - Failed to generate GDP chart: {e}")
        return None

def generate_inflation_chart(data, output_dir):
    """Generate inflation chart using Lightweight Charts."""
    try:
        # Convert data for lightweight-charts
        chart_data = []
        for i, (label, value) in enumerate(zip(data['labels'], data['values'])):
            try:
                if label and value is not None:
                    time_str = f"{label}-01" if len(label.split('-')) == 2 else label
                    
                    chart_data.append({
                        'time': time_str,
                        'value': float(value),
                        'color': ('rgba(34, 197, 94, 0.7)' if 2.0 <= float(value) <= 2.5  # Green when in target range
                                 else 'rgba(239, 68, 68, 0.7)')  # Red when outside target range
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
                            top: 0.1,
                            bottom: 0.1,
                        }},
                        autoScale: false,
                        minimum: 1.8,
                        maximum: 3.5,
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
                    baseValue: {{ type: 'price', price: 2.5 }},
                    topLineColor: 'rgba(148, 163, 184, 0.2)',
                    bottomLineColor: 'rgba(148, 163, 184, 0.2)',
                }});

                // Add value labels above bars with delay to ensure rendering
                setTimeout(() => {{
                    chartData.forEach(dataPoint => {{
                        chart.addCustomPriceLabel({{
                            price: dataPoint.value + 0.5,
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
                            top: 0.1,
                            bottom: 0.1,
                        }},
                        autoScale: false,
                        minimum: 3.2,
                        maximum: 4.4,
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
                        precision: 1,
                        minMove: 0.1,
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
                            price: dataPoint.value + 0.5,
                            time: dataPoint.time,
                            color: '#94a3b8',
                            text: `${{dataPoint.value.toFixed(1)}}%`,
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