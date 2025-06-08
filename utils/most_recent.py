import functools
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

def with_most_recent_data(max_days=7):
    """
    Decorator to try fetching data for today, then previous days up to max_days.
    The wrapped function must accept a 'date' kwarg (YYYY-MM-DD).
    Returns (result, date) if found, else (None, None).
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for offset in range(max_days):
                date = (datetime.now() - timedelta(days=offset)).strftime('%Y-%m-%d')
                kwargs['date'] = date
                result = func(*args, **kwargs)
                if result:
                    logger.debug(f"Found data for {func.__name__} on {date}")
                    return result, date
                logger.debug(f"No data for {func.__name__} on {date}, trying previous day.")
            logger.warning(f"No data found for {func.__name__} in the last {max_days} days.")
            return None, None
        return wrapper
    return decorator 