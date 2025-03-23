"""
Utility module for generating standardized metadata for backtest reports.
"""

import os
from datetime import datetime

def generate_metadata(
    symbol,
    timeframe,
    start_date,
    end_date,
    initial_capital,
    commission,
    report_type,
    strategy_name=None,
    strategies_compared=None,
    directory_name=None,
    chart_path=None,
    additional_data=None
):
    """
    Generate standardized metadata for backtest reports.
    
    Parameters:
    -----------
    symbol : str
        The stock symbol (ticker)
    timeframe : str
        The timeframe of the data (e.g., '1d', '1h')
    start_date : str
        The start date of the backtest
    end_date : str
        The end date of the backtest
    initial_capital : float
        The initial capital used in the backtest
    commission : float
        The commission rate used in the backtest
    report_type : str
        The type of report ('backtest', 'comparison')
    strategy_name : str, optional
        The name of the strategy (for backtest reports)
    strategies_compared : list, optional
        List of strategies compared (for comparison reports)
    directory_name : str, optional
        The directory name where the report is stored
    chart_path : str, optional
        Path to the chart file (for backtest reports)
    additional_data : dict, optional
        Any additional data to include in the metadata
        
    Returns:
    --------
    dict
        Standardized metadata dictionary
    """
    # Create base metadata
    metadata = {
        "symbol": symbol,
        "timeframe": timeframe,
        "start_date": start_date,
        "end_date": end_date,
        "initial_capital": initial_capital,
        "commission": commission,
        "type": report_type,
        "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    # Add report type specific fields
    if report_type == "backtest":
        metadata["strategy"] = strategy_name
        if chart_path:
            metadata["chart_path"] = chart_path
    elif report_type == "comparison":
        metadata["strategy"] = "Comparison"
        if strategies_compared:
            metadata["strategies_compared"] = strategies_compared
    
    # Add path to the report
    if directory_name:
        metadata["path"] = f"{directory_name}/index.html"
    
    # Add any additional data
    if additional_data and isinstance(additional_data, dict):
        metadata.update(additional_data)
    
    return metadata

def save_metadata(metadata, directory):
    """
    Save metadata to a JSON file in the specified directory.
    
    Parameters:
    -----------
    metadata : dict
        The metadata to save
    directory : str
        The directory where to save the metadata.json file
    
    Returns:
    --------
    str
        Path to the saved metadata file
    """
    import json
    
    # Ensure directory exists
    os.makedirs(directory, exist_ok=True)
    
    # Save metadata to file
    metadata_path = os.path.join(directory, "metadata.json")
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=4)
    
    return metadata_path 