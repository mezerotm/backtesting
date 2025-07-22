import logging
import os
from datetime import datetime

# Create logs directory if it doesn't exist
LOGS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
os.makedirs(LOGS_DIR, exist_ok=True)

def get_widget_logger(widget_name: str, level: int = logging.DEBUG) -> logging.Logger:
    """
    Get a logger for a specific widget with its own log file.
    
    Args:
        widget_name: Name of the widget (e.g., 'portfolio', 'profit_loss', 'orders')
        level: Logging level (default: DEBUG for detailed logging)
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(f"widget.{widget_name}")
    
    # Only configure if not already configured
    if not logger.handlers:
        logger.setLevel(level)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Create file handler
        log_file = os.path.join(LOGS_DIR, f"{widget_name}.log")
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        
        # Add handler to logger
        logger.addHandler(file_handler)
        
        # Prevent propagation to root logger to avoid duplicate logs
        logger.propagate = False
        
        logger.info(f"Logger initialized for {widget_name} widget")
    
    return logger

def get_api_logger(api_name: str, level: int = logging.DEBUG) -> logging.Logger:
    """
    Get a logger for a specific API with its own log file.
    
    Args:
        api_name: Name of the API (e.g., 'polygon', 'robinhood')
        level: Logging level (default: DEBUG for detailed logging)
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(f"api.{api_name}")
    
    # Only configure if not already configured
    if not logger.handlers:
        logger.setLevel(level)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Create file handler
        log_file = os.path.join(LOGS_DIR, f"{api_name}.log")
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        
        # Add handler to logger
        logger.addHandler(file_handler)
        
        # Prevent propagation to root logger to avoid duplicate logs
        logger.propagate = False
        
        logger.info(f"Logger initialized for {api_name} API")
    
    return logger

def cleanup_old_logs(days_to_keep: int = 7):
    """
    Clean up log files older than specified days.
    
    Args:
        days_to_keep: Number of days to keep log files (default: 7)
    """
    import time
    from pathlib import Path
    
    cutoff_time = time.time() - (days_to_keep * 24 * 60 * 60)
    
    for log_file in Path(LOGS_DIR).glob("*.log"):
        if log_file.stat().st_mtime < cutoff_time:
            try:
                log_file.unlink()
                print(f"Deleted old log file: {log_file}")
            except Exception as e:
                print(f"Error deleting {log_file}: {e}")

def list_log_files():
    """List all log files in the logs directory."""
    if not os.path.exists(LOGS_DIR):
        return []
    
    log_files = []
    for file in os.listdir(LOGS_DIR):
        if file.endswith('.log'):
            file_path = os.path.join(LOGS_DIR, file)
            size = os.path.getsize(file_path)
            modified = datetime.fromtimestamp(os.path.getmtime(file_path))
            log_files.append({
                'name': file,
                'size': size,
                'modified': modified,
                'size_mb': round(size / (1024 * 1024), 2)
            })
    
    return sorted(log_files, key=lambda x: x['modified'], reverse=True) 