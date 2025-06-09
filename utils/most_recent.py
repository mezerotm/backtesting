import functools
from datetime import datetime, timedelta
from typing import Any, Callable, Optional, Tuple, TypeVar

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
                        return result, date
                except Exception as e:
                    continue
            return None, None
        return wrapper
    return decorator 