import logging
import logging.handlers
import os
from datetime import datetime

# Create logs directory if it doesn't exist
LOGS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
os.makedirs(LOGS_DIR, exist_ok=True)

# Log rotation settings
MAX_LOG_SIZE_MB = 10  # Maximum size per log file in MB
MAX_LOG_BACKUPS = 5   # Number of backup files to keep
MAX_TOTAL_LOG_SIZE_MB = 100  # Maximum total size of all logs in MB

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
        
        # Create rotating file handler
        log_file = os.path.join(LOGS_DIR, f"{widget_name}.log")
        max_bytes = MAX_LOG_SIZE_MB * 1024 * 1024  # Convert MB to bytes
        file_handler = logging.handlers.RotatingFileHandler(
            log_file, 
            maxBytes=max_bytes, 
            backupCount=MAX_LOG_BACKUPS,
            encoding='utf-8'
        )
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
        
        # Create rotating file handler
        log_file = os.path.join(LOGS_DIR, f"{api_name}.log")
        max_bytes = MAX_LOG_SIZE_MB * 1024 * 1024  # Convert MB to bytes
        file_handler = logging.handlers.RotatingFileHandler(
            log_file, 
            maxBytes=max_bytes, 
            backupCount=MAX_LOG_BACKUPS,
            encoding='utf-8'
        )
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
    deleted_count = 0
    
    for log_file in Path(LOGS_DIR).glob("*.log*"):  # Include rotated files
        if log_file.stat().st_mtime < cutoff_time:
            try:
                log_file.unlink()
                deleted_count += 1
                print(f"Deleted old log file: {log_file}")
            except Exception as e:
                print(f"Error deleting {log_file}: {e}")
    
    return deleted_count

def cleanup_large_logs(max_total_size_mb: int = None):
    """
    Clean up log files when total size exceeds limit.
    
    Args:
        max_total_size_mb: Maximum total size in MB (uses default if None)
    """
    if max_total_size_mb is None:
        max_total_size_mb = MAX_TOTAL_LOG_SIZE_MB
    
    log_files = list_log_files()
    total_size_mb = sum(log['size_mb'] for log in log_files)
    
    if total_size_mb <= max_total_size_mb:
        return 0, total_size_mb
    
    # Sort by modification time (oldest first)
    log_files.sort(key=lambda x: x['modified'])
    
    deleted_count = 0
    for log_file in log_files:
        if total_size_mb <= max_total_size_mb:
            break
        
        try:
            file_path = os.path.join(LOGS_DIR, log_file['name'])
            os.remove(file_path)
            total_size_mb -= log_file['size_mb']
            deleted_count += 1
            print(f"Deleted large log file: {log_file['name']} ({log_file['size_mb']}MB)")
        except Exception as e:
            print(f"Error deleting {log_file['name']}: {e}")
    
    return deleted_count, total_size_mb

def get_log_stats():
    """
    Get statistics about log files.
    
    Returns:
        Dictionary with log statistics
    """
    log_files = list_log_files()
    total_size_mb = sum(log['size_mb'] for log in log_files)
    
    return {
        'total_files': len(log_files),
        'total_size_mb': round(total_size_mb, 2),
        'largest_file': max(log_files, key=lambda x: x['size_mb']) if log_files else None,
        'oldest_file': min(log_files, key=lambda x: x['modified']) if log_files else None,
        'newest_file': max(log_files, key=lambda x: x['modified']) if log_files else None,
        'files_by_size': sorted(log_files, key=lambda x: x['size_mb'], reverse=True)
    }

def auto_cleanup_logs():
    """
    Automatically clean up logs based on size and age limits.
    """
    print("🧹 Running automatic log cleanup...")
    
    # Clean by age (7 days)
    age_deleted = cleanup_old_logs(7)
    
    # Clean by total size
    size_deleted, total_size = cleanup_large_logs()
    
    print(f"✅ Cleanup complete: {age_deleted} files deleted by age, {size_deleted} files deleted by size")
    print(f"📊 Total log size: {total_size:.2f}MB")
    
    return age_deleted + size_deleted

def list_log_files():
    """List all log files in the logs directory."""
    if not os.path.exists(LOGS_DIR):
        return []
    
    log_files = []
    for file in os.listdir(LOGS_DIR):
        # Include .log files and rotated .log.1, .log.2, etc.
        if file.endswith('.log') or ('.log.' in file and file.split('.')[-1].isdigit()):
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