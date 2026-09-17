import logging
import logging.handlers
import os
from datetime import datetime
from pathlib import Path

# Create logs directory if it doesn't exist
# Use absolute path at project root to ensure logs go to the correct location
LOGS_DIR = os.path.join(
    os.path.dirname(
        os.path.dirname(
            os.path.dirname(__file__))),
    "logs")
os.makedirs(LOGS_DIR, exist_ok=True)

# Log file paths
APP_LOG_FILE = os.path.join(LOGS_DIR, "app.log")
SERVER_LOG_FILE = os.path.join(LOGS_DIR, "server.log")
WIDGET_LOG_DIR = os.path.join(LOGS_DIR, "widgets")
API_LOG_DIR = os.path.join(LOGS_DIR, "api")

# Create subdirectories
os.makedirs(WIDGET_LOG_DIR, exist_ok=True)
os.makedirs(API_LOG_DIR, exist_ok=True)


def _create_file_handler(
        log_file: str,
        level: int = logging.INFO,
        max_bytes: int = 5 *
        1024 *
        1024) -> logging.Handler:
    """Create a rotating file handler for a specific log file."""
    handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=max_bytes, backupCount=3, encoding='utf-8')
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'))
    return handler


def _create_console_handler(level: int = logging.ERROR) -> logging.Handler:
    """Create a console handler with specified level."""
    handler = logging.StreamHandler()
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter(
        '%(levelname)s: %(name)s: %(message)s'))
    return handler


def get_app_logger(
        name: str = None,
        level: int = logging.INFO) -> logging.Logger:
    """Get a logger for general application logs (writes to app.log)."""
    if name is None:
        import inspect
        frame = inspect.currentframe().f_back
        name = frame.f_globals.get('__name__', 'unknown')

    logger = logging.getLogger(f"app.{name}")

    if not logger.handlers:
        logger.setLevel(level)
        logger.addHandler(_create_file_handler(APP_LOG_FILE, level))
        logger.addHandler(_create_console_handler())
        logger.propagate = False

    return logger


def get_server_logger(
        name: str = None,
        level: int = logging.DEBUG) -> logging.Logger:
    """Get a logger for server-specific logs (writes to server.log)."""
    if name is None:
        import inspect
        frame = inspect.currentframe().f_back
        name = frame.f_globals.get('__name__', 'unknown')

    logger = logging.getLogger(f"server.{name}")

    if not logger.handlers:
        logger.setLevel(level)
        logger.addHandler(_create_file_handler(SERVER_LOG_FILE, level))
        logger.addHandler(_create_console_handler())
        logger.propagate = False

    return logger


def get_widget_logger(
        widget_name: str,
        level: int = logging.INFO) -> logging.Logger:
    """Get a logger for a specific widget (writes to widgets/{widget_name}.log)."""
    log_file = os.path.join(WIDGET_LOG_DIR, f"{widget_name}.log")
    logger = logging.getLogger(f"widget.{widget_name}")

    if not logger.handlers:
        logger.setLevel(level)
        logger.addHandler(
            _create_file_handler(
                log_file,
                level,
                max_bytes=10 *
                1024 *
                1024))
        logger.addHandler(_create_console_handler())
        logger.propagate = False

    return logger


def get_api_logger(api_name: str, level: int = logging.INFO) -> logging.Logger:
    """Get a logger for a specific API (writes to api/{api_name}.log)."""
    log_file = os.path.join(API_LOG_DIR, f"{api_name}.log")
    logger = logging.getLogger(f"api.{api_name}")

    if not logger.handlers:
        logger.setLevel(level)
        logger.addHandler(
            _create_file_handler(
                log_file,
                level,
                max_bytes=10 *
                1024 *
                1024))
        logger.addHandler(_create_console_handler())
        logger.propagate = False

    return logger


def get_data_validation_logger(
        api_name: str = "general",
        level: int = logging.INFO) -> logging.Logger:
    """Get a logger specifically for data validation and malformed data handling."""
    log_file = os.path.join(API_LOG_DIR, f"{api_name}_validation.log")
    logger = logging.getLogger(f"validation.{api_name}")

    if not logger.handlers:
        logger.setLevel(level)
        logger.addHandler(
            _create_file_handler(
                log_file,
                level,
                max_bytes=10 *
                1024 *
                1024))
        # Only show warnings+ in console
        logger.addHandler(_create_console_handler(logging.WARNING))
        logger.propagate = False

    return logger


def cleanup_old_logs(days_to_keep: int = 7):
    """Clean up old log files."""
    from pathlib import Path
    deleted_count = 0

    for log_file in Path(LOGS_DIR).glob("*.log*"):
        try:
            log_file.unlink()
            deleted_count += 1
            print(f"Deleted old log file: {log_file}")
        except Exception as e:
            print(f"Error deleting {log_file}: {e}")

    return deleted_count


def cleanup_large_logs(max_total_size_mb: int = 50):
    """Clean up log files when total size exceeds limit."""
    total_size = 0
    log_files = []

    for log_file in Path(LOGS_DIR).rglob("*.log*"):
        try:
            size = log_file.stat().st_size
            total_size += size
            log_files.append((log_file, size))
        except Exception:
            continue

    total_size_mb = total_size / (1024 * 1024)
    deleted_count = 0

    if total_size_mb > max_total_size_mb:
        # Sort by modification time (oldest first)
        log_files.sort(key=lambda x: x[0].stat().st_mtime)

        for log_file, size in log_files:
            try:
                log_file.unlink()
                deleted_count += 1
                total_size_mb -= size / (1024 * 1024)
                if total_size_mb <= max_total_size_mb:
                    break
            except Exception as e:
                print(f"Error deleting {log_file}: {e}")

    return deleted_count, total_size_mb


def get_log_stats():
    """Get statistics about log files."""
    stats = {
        'total_files': 0,
        'total_size_mb': 0,
        'files': {}
    }

    try:
        for log_file in Path(LOGS_DIR).rglob("*.log*"):
            size = log_file.stat().st_size
            size_mb = round(size / (1024 * 1024), 2)
            stats['total_files'] += 1
            stats['total_size_mb'] += size_mb
            stats['files'][str(log_file.relative_to(LOGS_DIR))] = size_mb
    except Exception:
        pass

    return stats


def auto_cleanup_logs():
    """Automatically clean up logs."""
    print("🧹 Running automatic log cleanup...")

    deleted = cleanup_old_logs()
    stats = get_log_stats()

    print(f"✅ Cleanup complete: {deleted} files deleted")
    print(
        f"📊 Total logs: {stats['total_files']} files, {stats['total_size_mb']:.2f}MB")

    return deleted


def list_log_files():
    """List all log files with their sizes."""
    if not os.path.exists(LOGS_DIR):
        return []

    log_files = []
    try:
        for log_file in Path(LOGS_DIR).rglob("*.log*"):
            size = log_file.stat().st_size
            modified = datetime.fromtimestamp(log_file.stat().st_mtime)
            log_files.append({
                'name': str(log_file.relative_to(LOGS_DIR)),
                'size': size,
                'modified': modified,
                'size_mb': round(size / (1024 * 1024), 2)
            })
    except Exception:
        pass

    return log_files
