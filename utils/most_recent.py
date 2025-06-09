import functools
from datetime import datetime, timedelta
import logging
from typing import Any, Callable, Optional, Tuple, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar('T')

def with_most_recent_data(max_days: int = 7) -> Callable[[Callable[..., T]], Callable[..., Tuple[Optional[T], Optional[str]]]]:
    """
    Decorator to try fetching data for today, then previous days up to max_days.
    The wrapped function must accept a 'date' kwarg (YYYY-MM-DD).
    
    Args:
        max_days: Maximum number of days to look back for data
        
    Returns:
        Tuple of (result, date) if found, else (None, None)
        
    Example:
        @with_most_recent_data(max_days=7)
        def get_data(date: str) -> Optional[Dict]:
            # Function implementation
            pass
    """
    def decorator(func: Callable[..., T]) -> Callable[..., Tuple[Optional[T], Optional[str]]]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Tuple[Optional[T], Optional[str]]:
            for offset in range(max_days):
                try:
                    date = (datetime.now() - timedelta(days=offset)).strftime('%Y-%m-%d')
                    kwargs['date'] = date
                    result = func(*args, **kwargs)
                    if result:
                        logger.debug(f"Found data for {func.__name__} on {date}")
                        return result, date
                    logger.debug(f"No data for {func.__name__} on {date}, trying previous day.")
                except Exception as e:
                    logger.error(f"Error fetching data for {func.__name__} on {date}: {str(e)}")
                    continue
            logger.warning(f"No data found for {func.__name__} in the last {max_days} days.")
            return None, None
        return wrapper
    return decorator 